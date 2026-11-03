"""Decode native-domain stage measurements; never grant video acceptance."""
from pathlib import Path
import argparse,json,re
from check_c9_geometry import sha
from check_c9_uart import snapshots
from c9_probe_image import select
R=Path(__file__).resolve().parents[1]
def counter(value):
 assert type(value)is int and 0<=value<2**23,'Reserved stage counter bit'
 maximum=value>>12;segments=value&4095
 assert bool(maximum)==bool(segments),'Run/segment inconsistency'
 return dict(maximum_contiguous_cycles=maximum,maximum_at_least=maximum==2047,segments=segments,segments_at_least=segments==4095)
def decode(phy,isp,video):
 assert len(phy)>=2 and len(isp)>=5 and len(video)>=8
 assert all(type(v)is int and 0<=v<2**32 for v in [*phy,*isp,*video])
 n=phy[0]|phy[1]<<32;i=sum(w<<(32*k) for k,w in enumerate(isp[:5]));v=video[6]
 assert n>>56==0xe1 and not(n&0xff000000),'Native stage protocol mismatch'
 assert i>>128==0xc9e21001 and v>>30==2,'Stage signature mismatch'
 assert not any(isp[5:]),'Unexpected camera bank tail'
 nf=(n>>48)&255;flags=(i>>120)&255
 stages={name:counter((i>>(24*k))&0xffffff) for k,name in enumerate(['raw_2ppc','rgb_de','rgb_valid','rgb_joint','gray_2ppc'])}
 stages['native_4ppc']=counter(n&0xffffff)
 stages['pixel_1ppc']=dict(maximum_contiguous_cycles=v&2047,maximum_at_least=(v&2047)==2047)
 stages['source_1ppc']=dict(maximum_contiguous_cycles=(v>>11)&2047,maximum_at_least=((v>>11)&2047)==2047)
 return dict(stages=stages,native=dict(run=bool(nf&128),vs_seen=bool(nf&1),hs_seen=bool(nf&2),image_seen=bool(nf&4),image_valid_outside_hs=bool(nf&8),non4_image_ppc_seen=bool(nf&16),other_enabled_payload_seen=bool(nf&32),raw_overflow_seen=bool(nf&64),last_image_wc=(n>>32)&65535),
  isp=dict(run=bool(flags&128),raw_vs_seen=bool(flags&1),rgb_vs_seen=bool(flags&2),gray_vs_seen=bool(flags&4),rgb_de_without_valid_seen=bool(flags&8),rgb_valid_without_de_seen=bool(flags&16),raw_overflow_seen=bool(flags&32),raw_de_seen=bool(flags&64)),
  video=dict(run=bool(v&(1<<22)),pattern_mode=bool(v&(1<<23)),fault_gate=bool(v&(1<<24)),config_valid=bool(v&(1<<25)),time_valid=bool(v&(1<<26)),pixel_vs_seen=bool(v&(1<<27)),source_vs_seen=bool(v&(1<<28)),source_de_seen=bool(v&(1<<29))))
def check(log):
 log=Path(log);folder=log.parent;a=json.loads((folder/'attempt.json').read_text());fw=folder/'firmware_build_record.json';m=json.loads(fw.read_text())
 assert a['status']=='CAPTURED_DONE_REQUIRES_CHECKER' and a['fpga_configured'] and a['flash_written'] is False
 assert a['readback_sha256']==a['firmware_sha256']==m['artifacts']['c9_geometry.bin']['sha256'] and a['build_record_sha256']==sha(fw)
 assert sha(fw)==sha(R/'firmware/c9_camera_geometry/BUILD_RECORD.json') and sha(folder/'readback.bin')==a['readback_sha256'],'Frozen firmware/readback identity differs'
 image,audit=select(R,'stage');assert a['probe_variant']=='stage' and a['fpga_image_sha256']==sha(image) and a['implementation_audit_sha256']==sha(audit)
 text=log.read_text();assert not re.search(r'\|(?:FAIL|TRAP)\b|CRASH',text)
 assert 'C9|MAP status=PASS independent_locations=6 words=24 source_off=1' in text
 assert 'C9|BOOT mode=geometry version='+m['version'] in text and 'C9|DONE mode=geometry version='+m['version'] in text and a['firmware_version']==m['version']
 s=snapshots(text);b=s['before']['words'];z=s['after']['words']
 before=decode(b[4],b[3],b[1]);after=decode(z[4],z[3],z[1])
 assert (b[1][7]&12)==0 and (z[1][7]&12)==8,'Wrong source selection'
 assert all(not before[d]['run'] for d in ['native','isp','video']) and all(after[d]['run'] for d in ['native','isp','video'])
 assert all(v['maximum_contiguous_cycles']==0 for v in before['stages'].values()),'Counters active before RUN'
 assert ((s['after']['start']-s['before']['end'])&0xffffffff)>0
 f=z[1][7]
 return dict(status='CAPTURED_STAGE_STATUS_ONLY',real_camera_verified=False,board_acceptance_passed=False,flash_written=False,before=before,after=after,source_frames=z[1][0],format_errors=z[1][1],overflow_frames=z[1][2],a_completed=z[1][3],width=(f>>20)&4095,segments=(f>>8)&4095,segments_at_least=bool(f&16),record_seen=bool(f&128),record_complete=bool(f&64),uart_sha256=sha(log),attempt_sha256=sha(folder/'attempt.json'),image_sha256=sha(image),snapshots=s,scope='Pack40 diagnostic, maxima/segments since synchronized RUN, not physical HS rows or a frame trace. Stages, domains and snapshot pairs are not atomic together. camera bank now uses pixel2_clk, not I2C registers. Geometry firmware upper-flags word unchanged; pattern count word repurposed. Error debug remains disabled; no CRC conclusion.')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
 try:result=check(args.log)
 except Exception as exc:result=dict(status='FAIL_EVIDENCE',error=str(exc),board_acceptance_passed=False)
 if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2));return 0 if result['status']=='CAPTURED_STAGE_STATUS_ONLY' else 1
if __name__=='__main__':raise SystemExit(main())
