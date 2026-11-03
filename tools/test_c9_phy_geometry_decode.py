"""Exercise native CSI diagnostic decoding; all vectors are synthetic."""
from pathlib import Path
import hashlib,json
from check_c9_phy_geometry import decode_phy_words
R=Path(__file__).resolve().parents[1]
def main():
 cases=[]
 for name,groups,runs,extra in [('continuous',480,1,0),('bursty',480,60,0),('clipped',1023,60,1024),('faults_retained',480,60,513)]:
  flags=(groups<<22)|(runs<<12)|2048|extra
  v=decode_phy_words([0x44,flags])
  assert v['csi_payload_groups']==groups and v['csi_valid_runs']==runs
  assert v['csi_count_clipped']==bool(extra&1024) and v['csi_valid_outside_hs']==bool(extra&512) and v['camera_fault']==bool(extra&1)
  cases.append(name)
 valid=(480<<22)|(60<<12)|2048
 bad=[('not_seen',[0,valid&~2048]),('reserved',[0,valid|2]),('zero_runs',[0,(480<<22)|2048]),('runs_exceed_groups',[0,(2<<22)|(3<<12)|2048]),('false_clip',[0,valid|1024]),('truncated',[0]),('out_of_range',[0,1<<32])]
 for name,words in bad:
  try:decode_phy_words(words)
  except AssertionError:cases.append(name+'_rejected');continue
  raise AssertionError('Accepted invalid '+name)
 report=dict(status='PASS',synthetic_only=True,hardware_accessed=False,board_test_passed=False,cases=cases,
  source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'tools/check_c9_phy_geometry.py',R/'tools/check_c9_geometry.py',R/'tools/check_c9_uart.py']})
 (R/'logs/c9_phy_geometry_decode_tests_20261102.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS CSI decoder: '+str(len(cases))+' cases; synthetic only')
if __name__=='__main__':main()
