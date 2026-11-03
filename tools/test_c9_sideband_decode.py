from pathlib import Path
import json,hashlib
from check_c9_sideband import decode_words
R=Path(__file__).resolve().parents[1]
def main():
 lo=(1<<31)|(4<<22)|(43<<16)|2400
 v=decode_words([lo,0xc9d10014]);assert v['image_ppc_values']==[2,4] and v['last_image_ppc']==4 and v['pixel_wordcount']==2400
 v=decode_words([lo|(7<<28),0xc9d10015]);assert v['other_payload_seen'] and v['image_valid_outside_hs_seen'] and v['camera_fault'] and 0 in v['image_ppc_values']
 v=decode_words([43<<16,0xc9d10000]);assert not v['image_seen'] and v['image_ppc_values']==[]
 for words in [[lo,0xc9c20014],[lo,0xc9d10004],[lo,0xc9d10000],[43<<16,0xc9d10010],[lo],[lo,1<<32]]:
  try:decode_words(words)
  except AssertionError:continue
  raise AssertionError('Inconsistent sideband accepted')
 report=dict(status='PASS',hardware_accessed=False,synthetic_only=True,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'tools/check_c9_sideband.py']})
 (R/'logs/c9_sideband_decode_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS sideband mask, last-PPC membership, RUN-off, anomalous flags and malformed rejection')
if __name__=='__main__':main()
