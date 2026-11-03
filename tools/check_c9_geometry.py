"""Decode identity-bound camera geometry; never grant video/TinyML acceptance."""
from pathlib import Path
import argparse,hashlib,json,re
from check_c9_uart import snapshots
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(text):
 assert not re.search(r'\|(?:FAIL|TRAP)\b|CRASH',text),'Firmware failure/trap'
 assert 'C9|BOOT mode=geometry version=' in text and 'C9|DONE mode=geometry version=' in text,'Wrong/incomplete diagnostic'
 assert 'C9|MAP status=PASS independent_locations=6 words=24 source_off=1' in text,'Missing map check'
 assert 'C9|GEOMETRY protocol=1 synthetic=0 upper_flags=width12_height12_seen_complete_clip2' in text,'Unknown geometry protocol'
 s=snapshots(text);before=s['before']['words'];after=s['after']['words'];v=after[1];flags=v[7]
 assert (before[1][7]&8)==0 and (flags&15)==8,'Camera source isolation failed'
 assert flags&128,'No capture record measured'
 assert v[0]>=2 and v[6]==0,'No camera frames or pattern source used'
 assert ((s['after']['start']-s['before']['end'])&0xffffffff)>0,'No measurement interval'
 width=(flags>>20)&4095;height=(flags>>8)&4095;wc=bool(flags&32);hc=bool(flags&16)
 # Explicit clipping keeps an oversized record from wrapping to a plausible size.
 assert not wc or width==4095,'Invalid width saturation'
 assert not hc or height==4095,'Invalid height saturation'
 return dict(status='CAPTURED_GEOMETRY_ONLY',real_camera_verified=False,dma_cache_handoff_verified=False,board_acceptance_passed=False,
  width=width,height=height,width_clipped=wc,height_clipped=hc,record_complete=bool(flags&64),
  source_frames=v[0],format_errors=v[1],overflow_frames=v[2],a_completed=v[3],source_flags_hex=f'{flags:08x}',
  expected_width=1920,expected_height=1080,
  scope='Latest capture record counts contiguous DE segments, not necessarily physical sensor HS lines; pairs/domains sampled separately',snapshots=s)
def check(log):
 log=Path(log);folder=log.parent;a=json.loads((folder/'attempt.json').read_text());fw=folder/'firmware_build_record.json';m=json.loads(fw.read_text())
 assert a['status']=='CAPTURED_DONE_REQUIRES_CHECKER' and a['fpga_configured'] is True and a['flash_written'] is False,'Invalid capture scope'
 assert a['readback_sha256']==a['firmware_sha256']==m['artifacts']['c9_geometry.bin']['sha256'],'Firmware readback mismatch'
 assert a['build_record_sha256']==sha(fw),'Firmware manifest changed'
 from c9_probe_image import select
 image,audit=select(R,'geometry')
 assert a['probe_variant']=='geometry' and a['fpga_image_sha256']==sha(image) and a['implementation_audit_sha256']==sha(audit),'Geometry image identity mismatch'
 text=log.read_text(errors='replace');assert a['firmware_version']==m['version'] and text.count('version='+m['version'])==2,'Firmware version mismatch'
 result=decode(text);result.update(uart_sha256=sha(log),attempt_sha256=sha(folder/'attempt.json'),fpga_image_sha256=sha(image),firmware_sha256=a['firmware_sha256'])
 return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:result=check(a.log)
 except Exception as e:result=dict(status='FAIL_EVIDENCE',error=str(e),real_camera_verified=False,board_acceptance_passed=False)
 if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2));return 0 if result['status']=='CAPTURED_GEOMETRY_ONLY' else 1
if __name__=='__main__':raise SystemExit(main())
