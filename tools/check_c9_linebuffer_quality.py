"""Identity-bound linebuffer/transport/geometry observations, not AI acceptance."""
from pathlib import Path
import argparse,json,re
from check_c9_geometry import sha
from check_c9_stage_min import counter
from check_c9_uart import snapshots
from c9_probe_image import select
R=Path(__file__).resolve().parents[1];TRANSPORT_MASK=0x447d
def decode(phy,camera,video):
 assert len(phy)>=2 and len(camera)>=5 and len(video)>=8
 assert all(type(w)is int and 0<=w<2**32 for w in [*phy,*camera,*video])
 n=phy[0]|phy[1]<<32;v=video[6];info=camera[4]
 assert ((info>>24)&255)<=8 and ((info>>16)&255)<=7,'CSR state/retry encoding invalid'
 assert n>>56==0xf1 and camera[0]==0xc9f20003 and v>>30==2 and not any(camera[5:]),'Wrong CSR diagnostic protocol'

 errors=(n>>46)&127;fault=bool(n&(1<<53));assert fault==bool(errors)
 debug=n&0x1ffffff
 return dict(normalizer=dict(run=bool(n&(1<<55)),armed=bool(n&(1<<54)),fault=fault,error_flags_hex=f'{errors:02x}',last_frame_beats=(n>>27)&0x7ffff,input_frames_mod4=(n>>25)&3,debug_seen_hex=f'{debug:08x}',init_done_seen=bool(debug&0x8000),transport_error_bits_hex=f'{debug&TRANSPORT_MASK:08x}'),
 csr=dict(phy_prequalification_error_seen=bool(info&4096),phy_active_error_seen=bool(info&8192),phy_quality_released=bool(info&16384),phy_error_in_input_data_seen=bool(info&32768),run=bool(info&1),init_seen=bool(info&2),capture_enable=bool(info&4),fault=bool(info&8),state=(info>>24)&255,retries=(info>>16)&255,pre_status_hex=f'{camera[1]:08x}',post_status_hex=f'{camera[2]:08x}',native_rises=camera[3]&65535,native_falls=camera[3]>>16,native_flags_hex=f'{(info>>4)&255:02x}',native_vs_level=bool(info&(1<<11)),native_hs_level=bool(info&(1<<10)),native_de_seen=bool(info&(1<<4)),native_hs_seen=bool(info&(1<<5)),native_vs_seen=bool(info&(1<<6)),native_image_seen=bool(info&(1<<7)),native_non4_ppc_seen=bool(info&(1<<8)),native_bad_wc_seen=bool(info&(1<<9))),
 video=dict(run=bool(v&(1<<22)),pattern_mode=bool(v&(1<<23)),fault_gate=bool(v&(1<<24)),config_valid=bool(v&(1<<25)),time_valid=bool(v&(1<<26)),pixel_maximum=v&2047,source_maximum=(v>>11)&2047))
def geometry_failures(after,video):
 f=video[7];n=after['normalizer'];c=after['csr'];v=after['video'];bad=[]
 if not c['phy_quality_released'] or c['phy_active_error_seen']:bad.append('PHY release quality not verified')
 if c['fault'] or not c['capture_enable'] or c['state']!=7 or int(c['post_status_hex'],16)&0x7ffd:bad.append('CSR initialization/clear/readback not verified')
 if n['fault'] or not n['armed'] or n['last_frame_beats']!=518400:bad.append('normalizer/payload not verified')
 if not n['init_done_seen'] or int(n['transport_error_bits_hex'],16):bad.append('fresh transport/init error')
 if not(f&64) or (f>>20)&4095!=1920 or (f>>8)&4095!=1080 or f&48:bad.append('no complete 1920x1080 capture record')
 if video[0]<3 or video[1] or video[2]:bad.append('source format/overflow errors or too few frames')
 if v['fault_gate'] or not v['config_valid'] or not v['time_valid'] or v['pixel_maximum']!=1920 or v['source_maximum']!=1920:bad.append('downstream not verified')
 return bad
def check(log):
 log=Path(log);p=log.parent;a=json.loads((p/'attempt.json').read_text());fw=p/'firmware_build_record.json';m=json.loads(fw.read_text())
 assert a['status']=='CAPTURED_DONE_REQUIRES_CHECKER' and a['fpga_configured'] and a['flash_written'] is False
 assert a['readback_sha256']==a['firmware_sha256']==m['artifacts']['c9_geometry.bin']['sha256'] and a['build_record_sha256']==sha(fw)
 assert sha(fw)==sha(R/'firmware/c9_camera_geometry/BUILD_RECORD.json') and sha(p/'readback.bin')==a['readback_sha256']
 image,audit=select(R,'linebuffer_quality');assert a['probe_variant']=='linebuffer_quality' and a['fpga_image_sha256']==sha(image) and a['implementation_audit_sha256']==sha(audit)
 text=log.read_text();assert not re.search(r'\|(?:FAIL|TRAP)\b|CRASH',text)
 assert 'C9|MAP status=PASS independent_locations=6 words=24 source_off=1' in text
 assert 'C9|BOOT mode=geometry version='+m['version'] in text and 'C9|DONE mode=geometry version='+m['version'] in text and a['firmware_version']==m['version']
 s=snapshots(text);b=s['before']['words'];z=s['after']['words'];before=decode(b[4],b[3],b[1]);after=decode(z[4],z[3],z[1])
 assert (b[1][7]&12)==0 and (z[1][7]&12)==8,'Source selection changed'
 assert all(not before[k]['run'] and after[k]['run'] for k in ['normalizer','csr','video'])
 assert before['video']['pixel_maximum']==before['video']['source_maximum']==0
 assert ((s['after']['start']-s['before']['end'])&0xffffffff)>0
 f=z[1][7];reasons=geometry_failures(after,z[1])
 return dict(status='CAPTURED_LINEBUFFER_STATUS_ONLY',geometry_verified=not reasons,geometry_failures=reasons,tinyml_accelerator_present=False,real_camera_verified=False,board_acceptance_passed=False,flash_written=False,before=before,after=after,source_frames=z[1][0],format_errors=z[1][1],overflow_frames=z[1][2],a_completed=z[1][3],width=(f>>20)&4095,segments=(f>>8)&4095,record_complete=bool(f&64),uart_sha256=sha(log),attempt_sha256=sha(p/'attempt.json'),image_sha256=sha(image),snapshots=s,scope='PHY output held until32 clean cycles after arm; prequalification PHY status retained separately, postqualification errors fatal. Fixed RAW10/VC0 Pack40 linebuffer candidate. Native transport and last-frame count observed coherently in PHY bank; native VS edges/flags after CSR enable and video maxima remain in own domains. PHY debug set begins after CSR enable, including the pre-arm interval. No AI/HDMI/cold-start acceptance; C2 timestamps remain first output GRAY8 DE, not original CSI arrival time.')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
 try:result=check(args.log)
 except Exception as exc:result=dict(status='FAIL_EVIDENCE',error=str(exc),board_acceptance_passed=False)
 if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2));return 0 if result['status']=='CAPTURED_LINEBUFFER_STATUS_ONLY' else 1
if __name__=='__main__':raise SystemExit(main())
