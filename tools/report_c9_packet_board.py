"""Recheck saved compact packet trials; never accesses the board."""
from pathlib import Path
import json,re,hashlib
from check_c9_packet_compact_v2 import check
from check_c9_ddr_calibration import check as ddr_check
from c9_probe_image import select
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 image,audit=select(R,'packet_compact');files=sorted((R/'logs/c9_packet_compact_board_20261103').glob('*/result.json'));assert files,'No real trial'
 rows=[];evidence=[Path(__file__),audit]
 for f in files:
  m=json.loads(f.read_text());assert m['flash_written'] is False and m['c10_restore_passed']
  ddr=R/m['ddr_status']['attempt'];d=ddr_check(ddr,audit);assert d['calibration_verified']
  text=(f.parent/'camera_geometry.log').read_text();matches=re.findall(r'^ATTEMPT_DIR=(.+)$',text,re.M);assert len(matches)==1
  folder=Path(matches[0].strip()).resolve();assert folder.is_relative_to(R/'logs/ram_diagnostic_20261101')
  obs=check(folder/'uart.log');restore=R/m['restore_attempt'];back=json.loads(restore.read_text());assert back['status']=='PASS_WARM_ROM_FLASH_BOOT' and back['flash_written'] is False and back['uart_sha256']==sha(restore.parent/'uart.log')
  rows.append(dict(result=f.relative_to(R).as_posix(),camera_attempt=(folder/'attempt.json').relative_to(R).as_posix(),calibration_verified=True,observation=obs,restore=restore.relative_to(R).as_posix()))
  evidence += [f,ddr,ddr.parent/'samples.json',folder/'attempt.json',folder/'firmware_build_record.json',folder/'uart.log',restore,restore.parent/'uart.log']
 report=dict(status='PACKET_DIAGNOSTIC_RECORDED_VIDEO_ACCEPTANCE_PENDING',real_camera_verified=False,flash_written=False,active_profile_changed=False,
  packet_header_clock_coherence_verified=False,pixel_per_clk_samples_are_last_valid_only=True,
  image_sha256=sha(image),trials=rows,final_restore=rows[-1]['restore'],cold_boot_verified_this_session=False,
  evidence_sha256={p.relative_to(R).as_posix():sha(p) for p in evidence})
 (R/'logs/c9_packet_board_result_20261103.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],trials=[dict(camera_attempt=v['camera_attempt'],native=v['observation']['native_after'],source_frames=v['observation']['source_frames'],format_errors=v['observation']['format_errors'],width=v['observation']['width']) for v in rows],final_restore=report['final_restore']),indent=2))
if __name__=='__main__':main()
