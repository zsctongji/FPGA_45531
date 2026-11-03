"""Synthetic parser checks; these fixtures are never real camera evidence."""
from pathlib import Path
import hashlib,json
from check_c9_geometry import decode
R=Path(__file__).resolve().parents[1]
def fixture(flags):
 lines=['C9|BOOT mode=geometry version=fixture','C9|MAP status=PASS independent_locations=6 words=24 source_off=1','C9|GEOMETRY protocol=1 synthetic=0 upper_flags=width12_height12_seen_complete_clip2']
 for label,ms in [('before',1),('after',10001)]:
  words={b:[0]*8 for b in range(5)}
  words[1]=[251,250,0,0,0,0,0,flags] if label=='after' else [0,0,0,0,0,0,0,0]
  lines.append(f'C9|SNAP_BEGIN label={label} start_ms={ms:x}')
  for pair in range(4):
   for bank in range(5):lines.append(f'C9|BANK pair={pair:x} bank={bank:x} sequence={pair+(1 if label=="before" else 5):x} lo={words[bank][pair*2]:08x} hi={words[bank][pair*2+1]:08x}')
  lines.append(f'C9|SNAP_END label={label} end_ms={ms+1:x} pairs=4')
 lines.append('C9|DONE mode=geometry version=fixture');return '\n'.join(lines)
def main():
 cases=[]
 f=(960<<20)|(2160<<8)|128|8
 r=decode(fixture(f));assert (r['width'],r['height'],r['record_complete'])==(960,2160,False)
 assert r['board_acceptance_passed'] is False and r['real_camera_verified'] is False
 cases.append('fragmented_record_is_observation_only')
 r=decode(fixture((4095<<20)|(4095<<8)|128|32|16|8));assert r['width_clipped'] and r['height_clipped'];cases.append('clipped_record_explicit')
 for name,text in [('no_record',fixture(8)),('no_done',fixture(f).replace('C9|DONE','C9|OTHER')),('pattern_source',fixture(f|4)),('bad_hex',fixture(f).replace('hi=','hi=0xZ',1))]:
  try:decode(text)
  except (AssertionError,KeyError,TypeError):cases.append(name+'_rejected');continue
  raise AssertionError(name+' accepted')
 report=dict(status='PASS',synthetic_only=True,board_test_passed=False,cases=cases,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'tools/check_c9_geometry.py',R/'tools/check_c9_uart.py']})
 (R/'logs/c9_geometry_decode_tests_20261102.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS geometry decode: '+', '.join(cases))
if __name__=='__main__':main()
