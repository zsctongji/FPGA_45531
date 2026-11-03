"""Recheck saved compact packet trials; never accesses the board."""
from pathlib import Path
import json,re,hashlib
from check_c9_sideband_seed3 import check
from check_c9_ddr_calibration import check as ddr_check
from c9_probe_image import select
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 image,audit=select(R,'sideband_seed3');files=sorted((R/'logs/c9_sideband_seed3_board_20261103').glob('*/result.json'));assert files,'No real trial'
 rows=[];host_failures=[];evidence=[Path(__file__),audit]
 for f in files:
  m=json.loads(f.read_text());assert m['flash_written'] is False and m['c10_restore_passed']
  if 'ddr_status' not in m:
   restore=R/m['restore_attempt'];back=json.loads(restore.read_text());assert back['status']=='PASS_WARM_ROM_FLASH_BOOT' and back['uart_sha256']==sha(restore.parent/'uart.log')
   text=(f.parent/'ddr_status.log').read_text();a=re.findall(r'^ATTEMPT_DIR=(.+)$',text,re.M);assert len(a)==1
   attempt=Path(a[0].strip())/'attempt.json';a=json.loads(attempt.read_text())
   assert a['status']=='HOST_ERROR' and 'FileNotFoundError' in a['error'] and a['fpga_image_sha256']==sha(image)
   host_failures.append(dict(result=f.relative_to(R).as_posix(),attempt=attempt.relative_to(R).as_posix(),error=a['error'],calibration_verdict='NOT_CAPTURED',restore=restore.relative_to(R).as_posix()))
   evidence.extend([f,attempt,restore,restore.parent/'uart.log']);continue
  ddr=R/m['ddr_status']['attempt'];d=ddr_check(ddr,audit);assert d['calibration_verified']
  text=(f.parent/'camera_geometry.log').read_text();matches=re.findall(r'^ATTEMPT_DIR=(.+)$',text,re.M);assert len(matches)==1
  folder=Path(matches[0].strip()).resolve();assert folder.is_relative_to(R/'logs/ram_diagnostic_20261101')
  obs=check(folder/'uart.log');restore=R/m['restore_attempt'];back=json.loads(restore.read_text());assert back['status']=='PASS_WARM_ROM_FLASH_BOOT' and back['flash_written'] is False and back['uart_sha256']==sha(restore.parent/'uart.log')
  rows.append(dict(result=f.relative_to(R).as_posix(),camera_attempt=(folder/'attempt.json').relative_to(R).as_posix(),calibration_verified=True,observation=obs,restore=restore.relative_to(R).as_posix()))
  evidence += [f,ddr,ddr.parent/'samples.json',folder/'attempt.json',folder/'firmware_build_record.json',folder/'uart.log',restore,restore.parent/'uart.log']
 assert rows,'No successful pixel-sideband trial'
 report=dict(status='PIXEL_SIDEBAND_DIAGNOSTIC_VIDEO_ACCEPTANCE_PENDING',real_camera_verified=False,flash_written=False,active_profile_changed=False,
  pixel_header_source='vendor_pixel_sideband',byte_domain_header_sampled=False,ppc_set_after_RUN=True,error_debug_interface_enabled=False,
  image_sha256=sha(image),trials=rows,host_failures=host_failures,diagnostic_pack_type=1,disabled_pack_classes=[48,56,64],final_restore=rows[-1]['restore'],cold_boot_verified_this_session=False,
  evidence_sha256={p.relative_to(R).as_posix():sha(p) for p in evidence})
 (R/'logs/c9_sideband_board_result_20261103.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],trials=[dict(camera_attempt=v['camera_attempt'],native=v['observation']['native_after'],source_frames=v['observation']['source_frames'],format_errors=v['observation']['format_errors'],width=v['observation']['width']) for v in rows],final_restore=report['final_restore']),indent=2))
if __name__=='__main__':main()
