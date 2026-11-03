"""CSI native-clock line observation; no real-video acceptance claim."""
from pathlib import Path
import argparse,json
from check_c9_geometry import decode,sha
from c9_probe_image import select
R=Path(__file__).resolve().parents[1]
def decode_phy_words(words):
 assert len(words)>=2 and all(type(w) is int and 0<=w<2**32 for w in words),'Invalid PHY words'
 flags=words[1]
 assert flags&2048,'No payload-bearing CSI HS measured'
 groups=(flags>>22)&1023;runs=(flags>>12)&1023
 assert flags&510==0,'Reserved CSI bits set'
 assert groups>=runs>0,'Invalid CSI count'
 assert not flags&1024 or groups==1023 or runs==1023,'Invalid CSI saturation'
 return dict(csi_payload_groups=groups,csi_valid_runs=runs,
  csi_count_clipped=bool(flags&1024),csi_valid_outside_hs=bool(flags&512),camera_fault=bool(flags&1),mipi_debug_hex=f'{words[0]:08x}',
  csi_geometry_flags_hex=f'{flags:08x}',
  csi_scope='Last nonempty HS in native CSI pixel clock; no cross-domain atomicity with capture dimensions; configured RAW10 interface carries four pixels/group')
def check(log):
 log=Path(log);folder=log.parent;a=json.loads((folder/'attempt.json').read_text());fw=folder/'firmware_build_record.json';m=json.loads(fw.read_text())
 assert a['status']=='CAPTURED_DONE_REQUIRES_CHECKER' and a['fpga_configured'] is True and a['flash_written'] is False
 assert a['readback_sha256']==a['firmware_sha256']==m['artifacts']['c9_geometry.bin']['sha256']
 assert a['build_record_sha256']==sha(fw)
 image,audit=select(R,'geometry_phy')
 assert a['probe_variant']=='geometry_phy' and a['fpga_image_sha256']==sha(image) and a['implementation_audit_sha256']==sha(audit),'CSI observer image mismatch'
 text=log.read_text(errors='replace');assert a['firmware_version']==m['version'] and text.count('version='+m['version'])==2
 result=decode(text);result.update(decode_phy_words(result['snapshots']['after']['words'][4]))
 result.update(status='CAPTURED_CSI_GEOMETRY_ONLY',uart_sha256=sha(log),attempt_sha256=sha(folder/'attempt.json'),fpga_image_sha256=sha(image),firmware_sha256=a['firmware_sha256'])
 return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:result=check(a.log)
 except Exception as e:result=dict(status='FAIL_EVIDENCE',error=str(e),board_acceptance_passed=False,real_camera_verified=False)
 if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2));return 0 if result['status']=='CAPTURED_CSI_GEOMETRY_ONLY' else 1
if __name__=='__main__':raise SystemExit(main())
