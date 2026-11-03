"""Package the audited observer without promoting it to the active profile."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys
from c9_probe_image import select,select_current
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 image,audit=select(R,'linebuffer_csr');project=image.parents[1];a=json.loads(audit.read_text())
 active,_,profile=select_current(R);assert json.loads(profile.read_text())['variant']=='display','Do not promote an untested observer'
 fw=R/'firmware/c9_camera_geometry';f=json.loads((fw/'BUILD_RECORD.json').read_text())
 for n,d in f['source_sha256'].items():assert sha(R/n)==d,n
 for n,d in f['artifacts'].items():assert sha(fw/n)==d['sha256'],n
 tests=[R/'logs/c9_linebuffer_csr_tests_20261103.json',R/'logs/c9_linebuffer_csr_chain_tests_20261103.json',R/'logs/c9_linebuffer_csr_decode_tests_20261103.json']
 for t in tests:
  m=json.loads(t.read_text());assert m['status']=='PASS'
  for n,d in m['source_sha256'].items():assert sha(R/n)==d,n
 q=subprocess.run([sys.executable,'-X','utf8',str(R/'tools/run_c9_linebuffer_csr.py')],cwd=R,capture_output=True,text=True,timeout=90)
 assert q.returncode==0,q.stdout+q.stderr
 preflight=json.loads(q.stdout);assert preflight['status']=='PASS_OFFLINE_PREFLIGHT' and preflight['hardware_accessed'] is False
 place=project/'outflow/soc_physical.place.rpt';text=place.read_text();xlr=re.search(r'^XLRs:\s*(\d+)\s*/\s*(\d+)',text,re.M);assert xlr
 package=R/'fpga_bitstreams/c9_linebuffer_csr_100mhz';package.mkdir(exist_ok=True)
 for suffix in ['bit','hex','place.rpt','pinout.csv','review_timing.rpt','bus_setup.rpt','bus_hold.rpt']:
  src=project/'outflow'/('soc_physical.'+suffix);dst=package/src.name
  if dst.exists():assert sha(dst)==sha(src),'Preserve packaged output'
  else:shutil.copyfile(src,dst)
 frozen_audit=package/'IMPLEMENTATION_AUDIT.json'
 if frozen_audit.exists():assert sha(frozen_audit)==sha(audit),'Preserve packaged audit'
 else:shutil.copyfile(audit,frozen_audit)
 record=dict(status='OFFLINE_READY_BOARD_REQUIRED',hardware_accessed=False,board_test_passed=False,real_camera_verified=False,flash_written=False,
  controlled_change=a['controlled_change'],image_sha256=sha(image),audit_path=audit.relative_to(R).as_posix(),audit_sha256=sha(audit),
  firmware_build_record_sha256=sha(fw/'BUILD_RECORD.json'),active_profile_sha256=sha(profile),active_image_sha256=sha(active),
  active_profile_changed=False,ddr_parameters_changed=False,calibration_algorithm_changed=False,acceptance_criteria_changed=False,
  timing=a['timing'],xlrs=int(xlr[1]),xlrs_available=int(xlr[2]),cdc_pointer_bits=66,
  hypothesis='Native-domain ISR cleanup/readback before capture. Fresh errors remain fatal, no TinyML accelerator.',
  evidence_sha256={p.relative_to(R).as_posix():sha(p) for p in [audit,*tests,fw/'BUILD_RECORD.json',Path(__file__),R/'tools/run_c9_linebuffer_csr.py',R/'tools/check_c9_linebuffer_csr.py']},
  packaged_sha256={p.name:sha(p) for p in package.iterdir() if p.name!='BUILD_RECORD.json'},preflight=preflight)
 (package/'BUILD_RECORD.json').write_text(json.dumps(record,indent=2)+'\n')
 (R/'logs/c9_linebuffer_csr_ready_20261103.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps({k:v for k,v in record.items() if k not in ['evidence_sha256','packaged_sha256']},indent=2))
if __name__=='__main__':main()
