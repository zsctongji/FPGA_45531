"""Read-only verification of a completed offline run and historical board evidence."""
from pathlib import Path
import argparse,datetime,hashlib,json,sys
from c9_probe_image import select,select_current
from compare_c1_reference import compare
from check_c9_uart import check as dma_check
from check_c9_linebuffer_quality import check as geometry_check
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('run',type=Path);a=ap.parse_args()
 out=a.run.resolve();assert out.is_relative_to((R/'logs').resolve())
 result=load(out/'result.json');assert result['status']=='PASS_OFFLINE_REGRESSION_HARDWARE_PENDING',result
 evidence={out/'result.json'}
 for step in result['steps']:
  p=R/step['log'];assert step['returncode']==0 and sha(p)==step['log_sha256'];evidence.add(p)
  execution=out/step['name']/'execution.json';e=load(execution)
  assert e['returncode']==0 and sha(R/'tools'/(step['name']+'.py'))==e['script_sha256']
  evidence.add(execution)
  for rel in e['reports']:evidence.add(R/rel)
 assert len(result['steps'])==25
 assert result['frozen_files_unchanged'] and result['camera_failure_preserved']
 assert result['identities_before']==result['identities_after']
 counts={}
 for name,filename,count in [
  ('test_c9_linebuffer','c9_linebuffer_tests_20261103.json',20),
  ('test_c9_linebuffer_csr','c9_linebuffer_csr_tests_20261103.json',16),
  ('test_c9_receiver_quality','c9_receiver_quality_tests_20261103.json',14),
  ('test_c9_stage_chain','c9_stage_chain_tests_20261103.json',7)]:
  p=out/name/filename;m=load(p);assert m['status']=='PASS' and len(m['cases'])==count
  counts[name]=count
 c2=load(out/'test_c9_display_c2/c9_display_c2_selftest.json')
 assert c2['status']=='PASS' and len(c2['tests'])==53 and all(v['status']=='PASS' for v in c2['tests'])
 assert len(c2['tail_checks'])==2 and all(v['status']=='PASS' for v in c2['tail_checks'])
 counts.update(c2_rtl=53,c2_tail=2,quality_actual_isp_chain=len(result['quality_isp_chain']['cases']))
 select_current(R)
 cold_audit=R/'logs/soc_cold_audit.json';cold=load(cold_audit)
 assert cold['status']=='PASS_OFFLINE_COLD_IMPLEMENTATION'
 cold_files={rel:digest for field in ['source_sha256','evidence_sha256'] for rel,digest in cold[field].items()}
 for rel,digest in cold_files.items():assert sha(R/rel)==digest,rel
 c10=dict(status='PASS_FROZEN_C10_IDENTITY',hardware_accessed=False,audit_sha256=sha(cold_audit),
  files=len(cold_files),image_sha256=sha(R/'projects/10_soc_cold/outflow/soc_physical.bit'))
 p=out/'c10_image_identity.json'
 if p.exists():assert load(p)==c10
 else:p.write_text(json.dumps(c10,indent=2)+'\n',encoding='utf-8')
 evidence.update([cold_audit,p])
 packages=[]
 for variant in ['linebuffer','linebuffer_csr','linebuffer_edges','linebuffer_reset','linebuffer_stream','linebuffer_quality']:
  image,audit=select(R,variant);p=R/'fpga_bitstreams'/('c9_'+variant+'_100mhz')
  record=load(p/'BUILD_RECORD.json');assert sha(p/'soc_physical.bit')==sha(image)==record['image_sha256']
  assert sha(p/'IMPLEMENTATION_AUDIT.json')==sha(audit)==record['audit_sha256']
  for rel,digest in record['evidence_sha256'].items():assert sha(R/rel)==digest,rel
  evidence.update([p/'BUILD_RECORD.json',p/'soc_physical.bit',p/'IMPLEMENTATION_AUDIT.json'])
  packages.append(dict(variant=variant,image_sha256=sha(image),audit_sha256=sha(audit)))
 # Replay the accepted pattern-DMA trial, including actual saved readback bytes.
 folder=R/'logs/ram_diagnostic_20261101/20261102_193055';attempt=load(folder/'attempt.json')
 manifest=folder/'firmware_build_record.json'
 assert sha(manifest)==attempt['build_record_sha256']
 assert sha(folder/'readback.bin')==attempt['readback_sha256']==attempt['firmware_sha256']
 assert attempt['fpga_configured'] and not attempt['flash_written']
 assert load(manifest)['version']==attempt['firmware_version']
 dma=dma_check((folder/'uart.log').read_text(errors='replace'),'dma')
 assert dma['status']=='PASS' and dma['dma_cache_handoff_verified'] and not dma['real_camera_verified']
 evidence.update(folder/n for n in ['attempt.json','uart.log','readback.bin','firmware_build_record.json'])
 # Recompute static TinyML raw scores from the latest restore and cold-boot log.
 manifest=R/'firmware/c1_static_person_detect/C1_INPUT_MANIFEST.json'
 reference=R/'logs/pc_ai/c1_reference.json';gold=load(reference);inputs=load(manifest)
 restores=[];static_comparisons={}
 for rel in ['logs/c10_warm_boot_20261101/20261103_182056',
             'logs/c7_cold_boot_20261101/20261101_175401']:
  folder=R/rel;meta=load(folder/'attempt.json');uart=folder/'uart.log'
  assert sha(uart)==meta['uart_sha256']
  comparison=compare(uart.read_text(errors='replace'),inputs,gold)
  assert comparison['status']=='PASS',comparison
  static_comparisons['warm_static_reference.json' if 'c10_warm' in rel else 'cold_static_reference.json']=comparison
  target=out/(folder.parent.name+'_reference_replay.json')
  target.write_text(json.dumps(comparison,indent=2)+'\n',encoding='utf-8')
  evidence.update([folder/'attempt.json',uart,target])
  restores.append(dict(attempt=(folder/'attempt.json').relative_to(R).as_posix(),
    status=meta['status'],raw_score_reference_match=True,log_sha256=sha(uart)))
 evidence.update([manifest,reference])
 for name,want in [('warm_static_reference.json','PASS'),('cold_static_reference.json','PASS'),
                   ('pattern_dma_replay.json','PASS'),('missed_scan_failure_replay.json','FAIL')]:
  p=out/name
  if not p.exists():
   if name in static_comparisons:v=static_comparisons[name]
   elif name=='pattern_dma_replay.json':v=dma
   else:
    try:dma_check((R/'logs/ram_diagnostic_20261101/20261102_183914/uart.log').read_text(errors='replace'),'dma')
    except AssertionError as exc:v=dict(status='FAIL',error=str(exc))
    else:raise AssertionError('Historical missed-scan log accepted')
   p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
  v=load(p);assert v['status']==want,(name,v)
  if want=='FAIL':assert v['error']=='Display underflow/missed scans'
  evidence.add(p)
 # A captured diagnostic status is successful evidence capture, not camera acceptance.
 meta=load(R/'logs/c9_linebuffer_quality_board_20261103/20261103_181949/result.json')
 camera=(R/meta['camera_attempt']).parent;seen=geometry_check(camera/'uart.log')
 assert not seen['geometry_verified'] and not seen['board_acceptance_passed']
 assert seen['after']['csr']['phy_active_error_seen']
 evidence.update([camera/'attempt.json',camera/'uart.log',camera/'readback.bin'])
 report=dict(status='PASS_OFFLINE_EVIDENCE_VERIFICATION',verified_at=datetime.datetime.now().astimezone().isoformat(),
  hardware_accessed=False,flash_written=False,new_board_test_performed=False,
  test_case_counts=counts,
  real_camera_verified=False,physical_hdmi_verified=False,
  historical_dma_pattern_pass_replayed=True,latest_camera_failure_preserved=True,
  frozen_files_checked=result['frozen_files'],c10_frozen_files_checked=len(cold_files),
  packages=packages,static_reference_replays=restores,
  source_sha256={p.relative_to(R).as_posix():sha(p) for p in [Path(__file__),R/'tools/run_c9_pc_acceptance.py',R/'tools/compare_c1_reference.py',R/'tools/check_c9_uart.py']},
  evidence_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(evidence)})
 target=out/'evidence_verification.json';target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(status=report['status'],evidence_files=len(evidence),packages=len(packages),
   frozen_files=result['frozen_files'],report=str(target)),ensure_ascii=False))
 return 0
if __name__=='__main__':raise SystemExit(main())
