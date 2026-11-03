from pathlib import Path
import json,hashlib
from check_c9_packet import decode_words
R=Path(__file__).resolve().parents[1]
def main():
 lo=(1<<31)|(4<<22)|(0x2b<<16)|2400;hi=(300<<20)|(1080<<8)|17
 v=decode_words([lo,hi]);assert (v['word_count'],v['datatype'],v['pixel_per_clk'],v['vs_edges'],v['hs_edges_last_vs'])==(2400,43,4,300,1080)
 assert v['metadata_seen'] and v['interval_seen'] and not v['camera_fault']
 v=decode_words([lo|(7<<28),hi|12]);assert all(v[k] for k in ['metadata_changed','valid_outside_hs','camera_fault','vs_count_clipped','hs_count_clipped'])
 for words in [[0,0],[lo,hi|2],[lo,1<<32],[0]]:
  try:decode_words(words)
  except AssertionError:continue
  raise AssertionError('malformed data accepted')
 report=dict(status='PASS',synthetic_only=True,hardware_accessed=False,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'tools/check_c9_packet.py']})
 (R/'logs/c9_packet_decode_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS packet decode fields, anomalies and malformed rejection')
if __name__=='__main__':main()
