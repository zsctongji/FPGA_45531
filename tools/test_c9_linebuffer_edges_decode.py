"""Prove stale pre-start status cannot hide fresh errors in geometry gate."""
from pathlib import Path
import copy,hashlib,json
from check_c9_linebuffer_edges import decode,geometry_failures
R=Path(__file__).resolve().parents[1]
def main():
 n=(0xf1<<56)|(1<<55)|(1<<54)|(518400<<27)|0x88002
 phy=[n&0xffffffff,n>>32];camera=[0xc9f20002,0x4418,2,0x012c012c,(7<<24)|7|(0xcf<<4),0,0,0]
 video=[300,0,0,0,0,0,(2<<30)|(7<<27)|(1<<26)|(1<<25)|(1<<22)|(1920<<11)|1920,(1920<<20)|(1080<<8)|128|64|8]
 good=decode(phy,camera,video);assert not geometry_failures(good,video)
 assert good['csr']['native_rises']==300 and good['csr']['native_falls']==300 and good['csr']['native_image_seen']
 for key in ['csr_fail','csr_pending','post_isr','fresh_crc','input_payload','shape','format','source_gate','pixel_width']:
  a=copy.deepcopy(good);v=video.copy()
  if key=='csr_fail':a['csr']['fault']=True
  if key=='csr_pending':a['csr']['capture_enable']=False
  if key=='post_isr':a['csr']['post_status_hex']='00004418'
  if key=='fresh_crc':a['normalizer']['transport_error_bits_hex']='00000004'
  if key=='input_payload':a['normalizer']['last_frame_beats']=518399
  if key=='shape':v[7]&=~64
  if key=='format':v[1]=1
  if key=='source_gate':a['video']['fault_gate']=True
  if key=='pixel_width':a['video']['pixel_maximum']=72
  assert geometry_failures(a,v),key
 for key in ['csr_marker','native_marker','native_fault_consistency','video_marker','csr_reserved','camera_tail']:
  a=phy.copy();b=camera.copy();c=video.copy()
  if key=='csr_marker':b[0]^=1
  if key=='native_marker':a[1]^=1<<24
  if key=='native_fault_consistency':a[1]^=1<<21
  if key=='video_marker':c[6]^=1<<30
  if key=='csr_reserved':b[4]|=4096
  if key=='camera_tail':b[5]=1
  try:decode(a,b,c)
  except AssertionError:pass
  else:raise AssertionError('Protocol accepted '+key)
 files=[Path(__file__),R/'tools/check_c9_linebuffer_edges.py']
 report=dict(status='PASS',synthetic_only=True,hardware_accessed=False,positive_stale_cleared_case=True,negative_geometry_cases=9,negative_protocol_cases=6,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
 (R/'logs/c9_linebuffer_edges_decode_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('PASS: cleared historical errors allowed; fresh/errors/payload/shape faults rejected; malformed protocols rejected')
if __name__=='__main__':main()
