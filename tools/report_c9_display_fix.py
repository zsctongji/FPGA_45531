"""Summarize verified pattern concurrency separately from failed real-camera capture."""
from pathlib import Path
import hashlib,json,re,shutil
from c9_probe_image import select_current
from check_c9_ddr_calibration import check as cal_check
from check_c9_uart import check,snapshots
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 image,audit,profile=select_current(R);assert read(profile)['variant']=='display'
 evidence={}
 def bind(p):evidence[p.relative_to(R).as_posix()]=sha(p)
 for item in read(profile)['calibration_attempts']:
  p=R/item['path'];assert cal_check(p,audit)['calibration_verified'];bind(p);bind(p.parent/'samples.json')
 d=R/'logs/ram_diagnostic_20261101/20261102_193055';meta=read(d/'attempt.json');text=(d/'uart.log').read_text();result=check(text,'dma')
 assert result['status']=='PASS' and read(d/'dma_check.json')['status']=='PASS'
 assert meta['fpga_image_sha256']==sha(image) and meta['firmware_sha256']==meta['readback_sha256']==sha(d/'readback.bin')
 assert sha(d/'run_ram_diagnostic.py')==meta['runner_sha256']
 for f in ['attempt.json','uart.log','readback.bin','firmware_build_record.json','dma_check.json','run_ram_diagnostic.py','check_c9_uart.py']:bind(d/f)
 c=R/'logs/ram_diagnostic_20261101/20261102_195114';cm=read(c/'attempt.json');ct=(c/'uart.log').read_text()
 assert cm['status']=='FAIL_OR_INCOMPLETE' and cm['fpga_image_sha256']==sha(image)
 assert cm['firmware_sha256']==cm['readback_sha256']==sha(c/'readback.bin')
 assert sha(c/'run_ram_diagnostic.py')==cm['runner_sha256']
 assert 'C9|TIME status=PASS' in ct and 'C24|FAIL stage=live_frames' in ct
 camera=snapshots(ct);video=camera['after']['words'][1]
 assert video[0]==505 and video[1]==504 and video[2]==0 and video[7]&15==8
 for f in ['attempt.json','uart.log','readback.bin','firmware_build_record.json','camera_observation.json','run_ram_diagnostic.py']:bind(c/f)
 old=R/'logs/ram_diagnostic_20261101/20261102_193610';assert 'stage=time_progress' in (old/'uart.log').read_text();bind(old/'uart.log');bind(old/'attempt.json')
 restore_log=R/'logs/c10_after_camera_format_failure_20261102.log'
 match=re.search(r'^ATTEMPT_DIR=(.+)$',restore_log.read_text(),re.M);assert match
 restore=Path(match[1].strip());assert restore.is_relative_to(R)
 restored=read(restore/'attempt.json');assert restored['status']=='PASS_WARM_ROM_FLASH_BOOT' and read(restore/'reference_check.json')['status']=='PASS'
 for f in ['attempt.json','uart.log','reference_check.json']:bind(restore/f)
 build=read(audit);assert not any(v['violations'] for v in build['timing'].values())
 reg=read(R/'logs/c9_display_c2_selftest.json');assert reg['status']=='PASS' and len(reg['tests'])==53
 for p in [image,audit,profile,Path(__file__),R/'tools/check_c9_uart.py',R/'logs/c9_display_c2_selftest.json',R/'build/c9_scanout_startup_20261102/baseline_result.json',R/'build/c9_scanout_startup_20261102/fixed_result.json',R/'build/c9_time_progress_20261102/fixed_result.json',R/'build/c9_uart_hex_format_20261102.json']:bind(p)
 report=dict(status='PASS_PATTERN_DMA_VIDEO_CAMERA_FORMAT_PENDING',pattern_dma_concurrent_passed=True,dma_cache_handoff_verified=True,
  display_missed_before=result['snapshots']['before']['words'][2][4],display_missed_after=result['snapshots']['after']['words'][2][4],
  display_underflows_after=result['snapshots']['after']['words'][2][3],axi_errors_after=result['snapshots']['after']['words'][0][2:4],
  fpga_image_sha256=sha(image),setup_ns=build['timing']['setup']['minimum_slack_ns'],hold_ns=build['timing']['hold']['minimum_slack_ns'],
  c2_regressions=53,tail_burst_checks=2,gray_cdc_bits=66,real_camera_verified=False,valid_camera_inferences=0,
  camera_time_progress_fixed=True,camera_source_frames=video[0],camera_format_errors=video[1],camera_overflow_frames=video[2],
  physical_hdmi_picture_verified=False,c3_present=False,flash_written=False,acceptance_thresholds_changed=False,
  numeric_log_parser_change='Accept optional 0x hexadecimal prefix; original PASS/FAIL cases retained',
  final_board='C10',final_c10_restore_passed=True,final_c10_attempt=(restore/'attempt.json').relative_to(R).as_posix(),evidence_sha256=evidence)
 output=R/'logs/c9_display_board_20261102.json';output.write_text(json.dumps(report,indent=2)+'\n')
 target=R/'fpga_bitstreams/c9_display_fix_100mhz';target.mkdir(exist_ok=True);artifacts={}
 for name in ['soc_physical.bit','soc_physical.hex','soc_physical.place.rpt','soc_physical.pinout.csv','soc_physical.review_timing.rpt','soc_physical.bus_setup.rpt','soc_physical.bus_hold.rpt']:
  shutil.copyfile(image.parent/name,target/name);artifacts[name]=dict(bytes=(target/name).stat().st_size,sha256=sha(target/name))
 shutil.copyfile(profile,target/'QUALIFIED_PROFILE.json')
 (target/'BUILD_RECORD.json').write_text(json.dumps(dict(status=report['status'],diagnostic_only=True,rom_entry_parked=True,c3_present=False,
  flash_boot_image=False,full_system_passed=False,artifacts=artifacts,board_summary_sha256=sha(output),source_sha256=build['source_sha256'],implementation_audit_sha256=sha(audit)),indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='evidence_sha256'},indent=2))
if __name__=='__main__':main()
