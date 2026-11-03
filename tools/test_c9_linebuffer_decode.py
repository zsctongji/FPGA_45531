"""Protocol rejection and strict geometry gate, synthetic inputs only."""
from pathlib import Path
import copy,hashlib,json
from check_c9_linebuffer import decode,geometry_failures
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 n=(0xf1<<56)|(1<<55)|(1<<54)|(518400<<27)|0x88002
 i=(0xc9e21001<<128)|(0xc7<<120)|sum(((960<<12)|1080)<<(24*k) for k in range(5))
 phy=[n&0xffffffff,n>>32];isp=[(i>>(32*k))&0xffffffff for k in range(5)]+[0,0,0]
 video=[300,0,0,0,0,0,(2<<30)|(7<<27)|(1<<26)|(1<<25)|(1<<22)|(1920<<11)|1920,(1920<<20)|(1080<<8)|128|64|8]
 good=decode(phy,isp,video);assert not geometry_failures(good,video)
 assert good['normalizer']['pixel_fifo_empty_seen'] and not int(good['normalizer']['transport_error_bits_hex'],16)
 for key in ['crc','init','payload','fault','frame','too_few','format','overflow','isp_mismatch','source_gate']:
  x=copy.deepcopy(good);v=video.copy()
  if key=='crc':x['normalizer']['transport_error_bits_hex']='00000004'
  if key=='init':x['normalizer']['init_done_seen']=False
  if key=='payload':x['normalizer']['last_frame_beats']=518399
  if key=='fault':x['normalizer']['fault']=True
  if key=='frame':v[7]&=~64
  if key=='too_few':v[0]=2
  if key=='format':v[1]=1
  if key=='overflow':v[2]=1
  if key=='isp_mismatch':x['isp']['rgb_de_without_valid_seen']=True
  if key=='source_gate':x['video']['fault_gate']=True
  assert geometry_failures(x,v),'Accepted '+key
 for key in ['native_marker','fault_flag','isp_marker','video_marker','camera_tail']:
  a=phy.copy();b=isp.copy();c=video.copy()
  if key=='native_marker':a[1]^=1<<24
  if key=='fault_flag':a[1]^=1<<21
  if key=='isp_marker':b[4]^=1
  if key=='video_marker':c[6]^=1<<30
  if key=='camera_tail':b[5]=1
  try:decode(a,b,c)
  except AssertionError:pass
  else:raise AssertionError('Protocol accepted '+key)
 report=dict(status='PASS',synthetic_only=True,hardware_accessed=False,geometry_positive_case=True,negative_geometry_cases=10,negative_protocol_cases=5,source_sha256={p.relative_to(R).as_posix():sha(p) for p in [Path(__file__),R/'tools/check_c9_linebuffer.py']})
 (R/'logs/c9_linebuffer_decode_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('PASS linebuffer decode: strict geometry +10 rejection cases +5 malformed protocols; FIFO empty excluded from error mask')
if __name__=='__main__':main()
