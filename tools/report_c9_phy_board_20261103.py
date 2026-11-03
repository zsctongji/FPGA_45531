"""Replay three saved board trials; never convert diagnostic data to acceptance."""
from pathlib import Path
import hashlib,json,shutil
from c9_probe_image import select
from check_c9_uart import snapshots
from check_c9_geometry import check as geometry_check
from check_c9_phy_geometry import check as phy_check,decode_phy_words
from check_c9_ddr_calibration import check as ddr_check
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 trials=[('phy_first','logs/c9_phy_geometry_board_20261102/20261103_105110','20261103_105157','geometry_phy'),('phy_repeat','logs/c9_phy_geometry_board_20261102/20261103_105333','20261103_105419','geometry_phy'),('geometry_control','logs/c9_geometry_board_20261102/20261103_105641','20261103_105727','geometry')]
 rows=[];evidence=[Path(__file__)]
 for name,parent,attempt,variant in trials:
  folder=R/parent;result=json.loads((folder/'result.json').read_text());camera=R/'logs/ram_diagnostic_20261101'/attempt
  image,audit=select(R,variant)
  ddr=R/result['ddr_status']['attempt'];cal=ddr_check(ddr,audit);assert cal['calibration_verified'] and cal['c10_restore_passed']
  a=json.loads((camera/'attempt.json').read_text());assert a['status']=='CAPTURED_DONE_REQUIRES_CHECKER' and a['flash_written'] is False
  assert a['readback_sha256']==a['firmware_sha256'] and a['fpga_image_sha256']==sha(image)
  assert a['implementation_audit_sha256']==sha(audit)
  assert sha(camera/'firmware_build_record.json')==a['build_record_sha256']
  text=(camera/'uart.log').read_text();snap=snapshots(text);video=snap['after']['words'][1]
  try:
   checked=phy_check(camera/'uart.log') if variant=='geometry_phy' else geometry_check(camera/'uart.log')
   strict_status=checked['status'];error=None
  except AssertionError as e:
   assert name=='phy_repeat' and str(e)=='No capture record measured',str(e)
   strict_status='FAIL_EVIDENCE';error=str(e)
  raw=decode_phy_words(snap['after']['words'][4]) if variant=='geometry_phy' else None
  restore=R/result['restore_attempt'];rest=json.loads(restore.read_text())
  assert result['c10_restore_passed'] and rest['status']=='PASS_WARM_ROM_FLASH_BOOT' and rest['flash_written'] is False and rest['cold_boot_passed'] is False
  row=dict(name=name,image_sha256=sha(image),calibration_verified=True,source_frames=video[0],format_errors=video[1],overflow_frames=video[2],a_completed=video[3],
   width=(video[7]>>20)&4095,segments=(video[7]>>8)&4095,segments_clipped=bool(video[7]&16),record_seen=bool(video[7]&128),record_complete=bool(video[7]&64),
   strict_status=strict_status,strict_error=error,raw_phy_observation_only=raw,board_acceptance_passed=False,real_camera_verified=False,
   camera_attempt=(camera/'attempt.json').relative_to(R).as_posix(),restore_attempt=restore.relative_to(R).as_posix())
  rows.append(row);evidence += [folder/'result.json',camera/'attempt.json',camera/'uart.log',camera/'firmware_build_record.json',ddr,ddr.parent/'samples.json',restore,restore.parent/'uart.log',audit]
 report=dict(status='DIAGNOSTIC_COMPLETE_VIDEO_NOT_ACCEPTED',flash_written=False,real_camera_verified=False,board_acceptance_passed=False,
  trials=rows,new_probe_board_disposition='NOT_QUALIFIED_FOR_PIXEL_PATH_CAUSAL_INFERENCE',
  conclusion='Old geometry image reproduces 72-pixel segments; added CSI observer image gives different unstable downstream observations. CSI counters saturate, so payload length and line semantics are not established.',
  next_steps=['Compare two implementations and startup/reset behavior without changing DDR','Capture native VS/HS edge counts and packet word_count/datatype/pixel_per_clk with wider counters','Require consistent measurements before any pixel-path normalization'],
  final_restore=rows[-1]['restore_attempt'],cold_boot_verified_this_session=False,
  evidence_sha256={p.relative_to(R).as_posix():sha(p) for p in evidence})
 (R/'logs/c9_phy_board_result_20261103.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],trials=rows,final_restore=report['final_restore']),indent=2))
if __name__=='__main__':main()
