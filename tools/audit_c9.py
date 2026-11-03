"""C9 data-path equivalence supplement to the actual implementation audit."""
import hashlib,json
from pathlib import Path
import audit_soc_live
ROOT=Path(__file__).resolve().parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 audit_soc_live.main()
 mf=json.loads((ROOT/'projects/09_c7_live_acceptance/LIVE_MANIFEST.json').read_text())
 assert mf['diagnostic_counter_bits']==32 and mf['synthesis_mode']=='cong' and mf['comb4_packing']==1 and mf['pnr_optimization']=='CONGESTION_2'
 baseline=ROOT/'logs/physical_c2_selftest.json';tests=json.loads(baseline.read_text(encoding='utf-8-sig'))
 assert tests['status']=='PASS' and tests['passed']==53 and all(t['status']=='PASS' for t in tests['tail_checks'])
 clones=[]
 for row in tests['source_clone_provenance'].values():
  old=ROOT/row['compiled_from'];assert sha(old)==row['compiled_sha256']
  if row['compiled_from'].startswith('projects/07_soc_physical/overrides/'):
   new=ROOT/row['compiled_from'].replace('projects/07_soc_physical','projects/09_c7_live_acceptance')
   assert sha(new)==row['compiled_sha256'];clones.append(new.relative_to(ROOT).as_posix())
 assert sha(ROOT/'tools/test_physical_c2.py')==tests['wrapper_sha256']
 path=ROOT/'logs/soc_live_audit.json';result=json.loads(path.read_text())
 result.update(c2_data_path_regression_audit='PASS_SAME_AS_QUALIFIED_C7_C2',c9_auditor_sha256=sha(Path(__file__)),diagnostic_counter_bits=32,byte_identical_physical_overrides=clones)
 for p in [baseline,ROOT/'tools/test_physical_c2.py',ROOT/'tools/audit_c9.py']:
  result['evidence_sha256'][p.relative_to(ROOT).as_posix()]=sha(p)
 path.write_text(json.dumps(result,indent=2)+'\n');print('PASS C9 full 32-bit counters and byte-identical qualified C2 data path')
if __name__=='__main__':main()
