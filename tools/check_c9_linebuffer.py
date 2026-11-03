"""Identity-bound linebuffer/transport/geometry observations, not AI acceptance."""
from pathlib import Path
import argparse,json,re
from check_c9_geometry import sha
from check_c9_stage_min import counter
from check_c9_uart import snapshots
from c9_probe_image import select
R=Path(__file__).resolve().parents[1];TRANSPORT_MASK=0x7447d
def decode(phy,isp,video):
 assert len(phy)>=2 and len(isp)>=5 and len(video)>=8
 assert all(type(w)is int and 0<=w<2**32 for w in [*phy,*isp,*video])
 n=phy[0]|phy[1]<<32;i=sum(w<<(32*k) for k,w in enumerate(isp[:5]));v=video[6]
 assert n>>56==0xf1 and i>>128==0xc9e21001 and v>>30==2,'Wrong diagnostic protocol'
 assert not any(isp[5:]),'Camera bank tail changed'
 errors=(n>>46)&127;fault=bool(n&(1<<53));assert fault==bool(errors),'Fault/flags inconsistent'
 debug=n&0x1ffffff;flags=(i>>120)&255
 st={name:counter((i>>(24*k))&0xffffff) for k,name in enumerate(['raw_2ppc','rgb_de','rgb_valid','rgb_joint','gray_2ppc'])}
 st['pixel_1ppc']=dict(maximum_contiguous_cycles=v&2047,maximum_at_least=(v&2047)==2047)
 st['source_1ppc']=dict(maximum_contiguous_cycles=(v>>11)&2047,maximum_at_least=((v>>11)&2047)==2047)
 return dict(stages=st,normalizer=dict(run=bool(n&(1<<55)),armed=bool(n&(1<<54)),fault=fault,error_flags_hex=f'{errors:02x}',error_names=[name for k,name in enumerate(['buffer_overflow','metadata','ppc','frame_payload_or_boundary','transport','boundary_queue_overrun','partial_line_timeout']) if errors&(1<<k)],last_frame_beats=(n>>27)&0x7ffff,input_frames_mod4=(n>>25)&3,debug_seen_hex=f'{debug:08x}',init_done_seen=bool(debug&0x8000),transport_error_bits_hex=f'{debug&TRANSPORT_MASK:08x}',pixel_fifo_empty_seen=bool(debug&2)),
  isp=dict(run=bool(flags&128),raw_vs_seen=bool(flags&1),rgb_vs_seen=bool(flags&2),gray_vs_seen=bool(flags&4),rgb_de_without_valid_seen=bool(flags&8),rgb_valid_without_de_seen=bool(flags&16),raw_overflow_seen=bool(flags&32),raw_de_seen=bool(flags&64)),
  video=dict(run=bool(v&(1<<22)),pattern_mode=bool(v&(1<<23)),fault_gate=bool(v&(1<<24)),config_valid=bool(v&(1<<25)),time_valid=bool(v&(1<<26)),pixel_vs_seen=bool(v&(1<<27)),source_vs_seen=bool(v&(1<<28)),source_de_seen=bool(v&(1<<29))))
def geometry_failures(after,video):
 f=video[7];norm=after['normalizer'];isp=after['isp'];vid=after['video'];reasons=[]
 if norm['fault'] or not norm['armed'] or norm['last_frame_beats']!=518400:reasons.append('normalizer/payload not verified')
 if not norm['init_done_seen'] or int(norm['transport_error_bits_hex'],16):reasons.append('transport/init not verified')
 if not(f&64) or (f>>20)&4095!=1920 or (f>>8)&4095!=1080 or f&48:reasons.append('no complete 1920x1080 capture record')
 if video[0]<3 or video[1] or video[2]:reasons.append('source format/overflow errors or too few frames')
 if isp['raw_overflow_seen'] or isp['rgb_de_without_valid_seen'] or isp['rgb_valid_without_de_seen'] or vid['fault_gate']:reasons.append('downstream fault')
 return reasons
def check(log):
 log=Path(log);p=log.parent;a=json.loads((p/'attempt.json').read_text());fw=p/'firmware_build_record.json';m=json.loads(fw.read_text())
 assert a['status']=='CAPTURED_DONE_REQUIRES_CHECKER' and a['fpga_configured'] and a['flash_written'] is False
 assert a['readback_sha256']==a['firmware_sha256']==m['artifacts']['c9_geometry.bin']['sha256'] and a['build_record_sha256']==sha(fw)
 assert sha(fw)==sha(R/'firmware/c9_camera_geometry/BUILD_RECORD.json') and sha(p/'readback.bin')==a['readback_sha256']
 image,audit=select(R,'linebuffer');assert a['probe_variant']=='linebuffer' and a['fpga_image_sha256']==sha(image) and a['implementation_audit_sha256']==sha(audit)
 text=log.read_text();assert not re.search(r'\|(?:FAIL|TRAP)\b|CRASH',text)
 assert 'C9|MAP status=PASS independent_locations=6 words=24 source_off=1' in text
 assert 'C9|BOOT mode=geometry version='+m['version'] in text and 'C9|DONE mode=geometry version='+m['version'] in text and a['firmware_version']==m['version']
 s=snapshots(text);b=s['before']['words'];z=s['after']['words'];before=decode(b[4],b[3],b[1]);after=decode(z[4],z[3],z[1])
 assert (b[1][7]&12)==0 and (z[1][7]&12)==8,'Source selection changed'
 assert all(not before[k]['run'] and after[k]['run'] for k in ['normalizer','isp','video'])
 assert all(v['maximum_contiguous_cycles']==0 for v in before['stages'].values())
 assert ((s['after']['start']-s['before']['end'])&0xffffffff)>0
 f=z[1][7];reasons=geometry_failures(after,z[1])
 return dict(status='CAPTURED_LINEBUFFER_STATUS_ONLY',geometry_verified=not reasons,geometry_failures=reasons,tinyml_accelerator_present=False,real_camera_verified=False,board_acceptance_passed=False,flash_written=False,before=before,after=after,source_frames=z[1][0],format_errors=z[1][1],overflow_frames=z[1][2],a_completed=z[1][3],width=(f>>20)&4095,segments=(f>>8)&4095,record_complete=bool(f&64),uart_sha256=sha(log),attempt_sha256=sha(p/'attempt.json'),image_sha256=sha(image),snapshots=s,scope='Fixed RAW10/VC0 Pack40 linebuffer candidate. Native transport and last-frame count observed coherently in PHY bank; stage maxima remain in own domains. No AI/HDMI/cold-start acceptance; C2 timestamps remain first output GRAY8 DE, not original CSI arrival time.')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
 try:result=check(args.log)
 except Exception as exc:result=dict(status='FAIL_EVIDENCE',error=str(exc),board_acceptance_passed=False)
 if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2));return 0 if result['status']=='CAPTURED_LINEBUFFER_STATUS_ONLY' else 1
if __name__=='__main__':raise SystemExit(main())
