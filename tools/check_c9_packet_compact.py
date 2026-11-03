"""Identity-bound packet observations; no camera acceptance thresholds relaxed."""
from pathlib import Path
import argparse,json,re
from check_c9_geometry import sha
from check_c9_uart import snapshots
from c9_probe_image import select
R=Path(__file__).resolve().parents[1]
def decode_words(words):
 assert len(words)>=2 and all(type(v)is int and 0<=v<2**32 for v in words)
 lo,hi=words[:2];assert hi>>16==0xc9c2 and hi&0xff00==0,'Compact packet signature mismatch'
 return dict(word_count=lo&65535,datatype=(lo>>16)&63,pixel_per_clk=(lo>>22)&15,vc=(lo>>26)&3,
  metadata_seen=bool(lo&(1<<31)),vs_level=bool(lo&(1<<30)),hs_level=bool(lo&(1<<29)),camera_fault=bool(lo&(1<<28)),
  vs_edge_mod16=(hi>>4)&15,hs_edge_mod16=hi&15)

def check(log):
 log=Path(log);p=log.parent;a=json.loads((p/'attempt.json').read_text());fw=p/'firmware_build_record.json';m=json.loads(fw.read_text())
 assert a['status']=='CAPTURED_DONE_REQUIRES_CHECKER' and a['fpga_configured'] and a['flash_written'] is False
 assert a['readback_sha256']==a['firmware_sha256']==m['artifacts']['c9_geometry.bin']['sha256'] and a['build_record_sha256']==sha(fw)
 image,audit=select(R,'packet_compact');assert a['probe_variant']=='packet' and a['fpga_image_sha256']==sha(image) and a['implementation_audit_sha256']==sha(audit)
 text=log.read_text();assert not re.search(r'\|(?:FAIL|TRAP)\b|CRASH',text)
 assert 'C9|MAP status=PASS independent_locations=6 words=24 source_off=1' in text
 assert 'C9|BOOT mode=geometry version='+m['version'] in text and 'C9|DONE mode=geometry version='+m['version'] in text
 assert a['firmware_version']==m['version'];snap=snapshots(text);before=snap['before']['words'];after=snap['after']['words']
 assert (before[1][7]&8)==0 and (after[1][7]&12)==8,'Source selection differs'
 assert ((snap['after']['start']-snap['before']['end'])&0xffffffff)>0
 native_before=decode_words(before[4]);native=decode_words(after[4]);video=after[1];f=video[7]
 missing=[]
 if not native['metadata_seen']:missing.append('no valid payload metadata')
 result=dict(status='INCOMPLETE_PACKET_OBSERVATION' if missing else 'CAPTURED_PACKET_STATUS_ONLY',missing=missing,
  real_camera_verified=False,board_acceptance_passed=False,flash_written=False,native_before=native_before,native_after=native,
  source_frames=video[0],format_errors=video[1],overflow_frames=video[2],a_completed=video[3],
  width=(f>>20)&4095,segments=(f>>8)&4095,segments_clipped=bool(f&16),capture_record_seen=bool(f&128),capture_record_complete=bool(f&64),
  source_flags_hex=f'{f:08x}',uart_sha256=sha(log),attempt_sha256=sha(p/'attempt.json'),fpga_image_sha256=sha(image),
  scope='Diagnostic packet/header and edge observations only; Modulo-16 edge counts can wrap and cannot establish line counts or absence of activity. Metadata is last valid payload. Cross-domain observations are not simultaneous.',snapshots=snap)
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:result=check(a.log)
 except Exception as e:result=dict(status='FAIL_EVIDENCE',error=str(e),board_acceptance_passed=False)
 if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2));return 0 if result['status']=='CAPTURED_PACKET_STATUS_ONLY' else 1
if __name__=='__main__':raise SystemExit(main())
