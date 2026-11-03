"""Recheck saved stage trials without opening serial or JTAG."""
from pathlib import Path
import hashlib,json
from check_c9_linebuffer_reset import check
from check_c9_ddr_calibration import check as ddr_check
from c9_probe_image import select
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 image,audit=select(R,'linebuffer_reset');rows=[];evidence=[Path(__file__),audit]
 for f in sorted((R/'logs/c9_linebuffer_reset_board_20261103').glob('*/result.json')):
  m=json.loads(f.read_text());assert m['status']=='CAPTURED_LINEBUFFER_STATUS_ONLY' and m['flash_written'] is False
  assert m['runner_sha256']==sha(R/'tools/run_c9_linebuffer_reset.py') and m['c10_restore_passed']
  ddr=R/m['ddr_status']['attempt'];d=ddr_check(ddr,audit);assert d['calibration_verified']
  camera=R/m['camera_attempt'];obs=check(camera.parent/'uart.log')
  # snapshots uses integer bank keys; JSON persists them as strings.
  assert json.loads(json.dumps(obs))==m['observation'],'Stored stage summary differs'
  restore=R/m['restore_attempt'];back=json.loads(restore.read_text());assert back['status']=='PASS_WARM_ROM_FLASH_BOOT' and back['flash_written'] is False and back['uart_sha256']==sha(restore.parent/'uart.log')
  rows.append(dict(result=f.relative_to(R).as_posix(),calibration_verified=True,observation=obs,restore=restore.relative_to(R).as_posix()))
  evidence.extend([f,ddr,ddr.parent/'samples.json',camera,camera.parent/'uart.log',camera.parent/'readback.bin',restore,restore.parent/'uart.log'])
 assert rows,'No successful stage captures'
 report=dict(status='STAGE_DIAGNOSTIC_VIDEO_ACCEPTANCE_PENDING',real_camera_verified=False,board_acceptance_passed=False,flash_written=False,active_profile_changed=False,ddr_parameters_changed=False,calibration_algorithm_changed=False,cold_boot_verified_this_session=False,image_sha256=sha(image),trials=rows,final_restore=rows[-1]['restore'],evidence_sha256={p.relative_to(R).as_posix():sha(p) for p in evidence})
 (R/'logs/c9_linebuffer_reset_board_result_20261103.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],trials=[dict(result=v['result'],after=v['observation']['after'],width=v['observation']['width'],source_frames=v['observation']['source_frames'],format_errors=v['observation']['format_errors']) for v in rows],final_restore=report['final_restore']),indent=2))
if __name__=='__main__':main()
