from pathlib import Path
import hashlib,json
from check_c9_sideband_small import decode_words
R=Path(__file__).resolve().parents[1]
def main():
 lo=(1<<31)|(43<<16)|2400
 v=decode_words([lo,0xc9d20014]);assert v['image_ppc_values_0_to_4']==[2,4] and not v['ppc_above_4_seen']
 v=decode_words([lo|(7<<28),0xc9d28015]);assert v['ppc_above_4_seen'] and 0 in v['image_ppc_values_0_to_4'] and v['image_valid_outside_hs_seen'] and v['other_payload_seen'] and v['camera_fault']
 assert not decode_words([43<<16,0xc9d20000])['image_seen']
 for w in [[lo,0xc9d10014],[lo,0xc9d20020],[lo|(4<<22),0xc9d20014],[lo,0xc9d20000],[43<<16,0xc9d20014],[lo]]:
  try:decode_words(w)
  except AssertionError:continue
  raise AssertionError('bad protocol accepted')
 report=dict(status='PASS',hardware_accessed=False,synthetic_only=True,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'tools/check_c9_sideband_small.py']})
 (R/'logs/c9_sideband_small_decode_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS small sideband protocol, reserved bits, bounded PPC set and preserved anomalies')
if __name__=='__main__':main()
