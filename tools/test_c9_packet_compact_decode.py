from pathlib import Path
import json,hashlib
from check_c9_packet_compact import decode_words
R=Path(__file__).resolve().parents[1]
def main():
 lo=(1<<31)|(4<<22)|(43<<16)|2400;hi=0xc9c20011
 v=decode_words([lo,hi]);assert (v['word_count'],v['datatype'],v['pixel_per_clk'],v['vs_edge_mod16'],v['hs_edge_mod16'])==(2400,43,4,1,1)
 v=decode_words([lo|(7<<28),0xc9c20000]);assert v['camera_fault'] and v['vs_level'] and v['hs_level'] and v['vs_edge_mod16']==0
 # Equal modulo counters are not reported as zero activity.
 assert 'activity_absent' not in v and 'hs_edges_last_vs' not in v
 for words in [[0,0],[lo,hi|256],[lo,1<<32],[lo]]:
  try:decode_words(words)
  except AssertionError:continue
  raise AssertionError('Malformed packet accepted')
 report=dict(status='PASS',synthetic_only=True,hardware_accessed=False,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'tools/check_c9_packet_compact.py']})
 (R/'logs/c9_packet_compact_decode_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS compact packet fields, modulo ambiguity, faults and malformed rejection')
if __name__=='__main__':main()
