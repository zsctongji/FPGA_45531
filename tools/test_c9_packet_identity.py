from pathlib import Path
import json,hashlib,tempfile,shutil
from check_c9_packet_compact_v2 import check
from check_c9_packet_compact import check as baseline
R=Path(__file__).resolve().parents[1];A=R/'logs/ram_diagnostic_20261101/20261103_114336'
def main():
 try:baseline(A/'uart.log')
 except AssertionError:pass
 else:raise AssertionError('Baseline must reproduce variant mismatch')
 v=check(A/'uart.log');assert v['status']=='CAPTURED_PACKET_STATUS_ONLY' and not v['real_camera_verified']
 cases=['baseline_variant_mismatch_reproduced','saved_hardware_log_replayed']
 with tempfile.TemporaryDirectory(prefix='c9_packet_identity_') as td:
  p=Path(td)
  for name in ['uart.log','attempt.json','firmware_build_record.json']:shutil.copyfile(A/name,p/name)
  original=json.loads((p/'attempt.json').read_text())
  for name,key,value in [('wrong_variant','probe_variant','packet'),('wrong_image','fpga_image_sha256','0'*64),('bad_readback','readback_sha256','0'*64)]:
   m=dict(original);m[key]=value;(p/'attempt.json').write_text(json.dumps(m))
   try:check(p/'uart.log')
   except AssertionError:cases.append(name+'_rejected');continue
   raise AssertionError(name+' accepted')
 report=dict(status='PASS',hardware_accessed=False,real_camera_verified=False,cases=cases,
  source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'tools/check_c9_packet_compact_v2.py',A/'attempt.json',A/'uart.log']})
 (R/'logs/c9_packet_identity_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS identity: '+', '.join(cases))
if __name__=='__main__':main()
