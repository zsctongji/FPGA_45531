"""Require one bounded RTL change, fresh positive STA and all 66 CDC bits."""
from pathlib import Path
import datetime,hashlib,json,re,xml.etree.ElementTree as E
from audit_soc_physical import timing_summary,bus_summary
R=Path(__file__).resolve().parents[1];B=R/'build/c9_ddr_probe_nopack_20261101';P=R/'build/c9_display_fix_20261102'
FIX=R/'team_work/03_ai_soc/c9_live/display_fix/c2_video_scanout.sv';OLD=R/'projects/06_soc_c2/rtl/c2_video_scanout.sv'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(s):return E.canonicalize(s,strip_text=True,rewrite_prefixes=True)
def main():
 m=json.loads((P/'DISPLAY_MANIFEST.json').read_text());parent=json.loads((B/'implementation_audit.json').read_text())
 assert parent['status']=='PASS_OFFLINE_READONLY_DDR_PROBE' and sha(B/'implementation_audit.json')==m['parent_audit_sha256']
 for key in ['source_sha256','evidence_sha256']:
  for n,d in parent[key].items():assert sha(R/n)==d,n
 assert sha(R/'tools/prepare_c9_display_fix.py')==m['generator_sha256'] and sha(R/'tools/run_c9_display_fix.ps1')==m['runner_sha256']
 for n,d in m['source_sha256'].items():
  f=R/n
  if f.suffix=='.xml' and f.name=='soc_physical.xml':assert hashlib.sha256(f.read_text().encode()).hexdigest()==d,n
  else:assert sha(f)==d,n
 new=(P/'soc_physical.xml').read_text().replace(P.as_posix(),B.as_posix()).replace(FIX.as_posix(),OLD.as_posix())
 assert canon(new)==canon((B/'soc_physical.xml').read_text()),'Uncontrolled project options'
 for e in E.parse(B/'soc_physical.xml').iter():
  if e.tag.endswith('}design_file'):
   old=Path(e.get('name'));target=P/old.relative_to(B) if old.is_relative_to(B) else old
   if old==OLD:target=FIX
   else:assert sha(old)==sha(target),'Other compiled RTL changed: '+str(old)
 for name in ['soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl','overrides/ddr3_parameter.vh','overrides/ddr3_top.v']:
  if name.endswith('.xml'):assert canon((P/name).read_text())==canon((B/name).read_text())
  else:assert sha(P/name)==sha(B/name)
 tests=json.loads((R/'build/c9_scanout_startup_20261102/fixed_result.json').read_text());assert tests['status']=='PASS'
 assert tests['source_sha256'][FIX.relative_to(R).as_posix()]==sha(FIX)
 regression_path=R/'logs/c9_display_c2_selftest.json';regression=json.loads(regression_path.read_text())
 assert regression['status']=='PASS' and len(regression['tests'])==53 and len(regression['tail_checks'])==2
 assert regression['display_scanout_fix'] is True
 for n,d in regression['source_sha256'].items():assert sha(R/n)==d,n
 scan_sources=[v for v in regression['source_clone_provenance'].values() if v['compiled_from']==FIX.relative_to(R).as_posix()]
 assert len(scan_sources)==1 and scan_sources[0]['compiled_sha256']==sha(FIX)
 rows=lambda f:[s for s in f.read_text(encoding='utf-8-sig').splitlines() if s and not s.startswith('#')]
 assert rows(P/'outflow/soc_physical.pinout.csv')==rows(B/'outflow/soc_physical.pinout.csv')
 binding=json.loads((P/'cdc_binding.json').read_text());assert binding['status']=='PASS' and binding['pointer_bits']==66
 for f,key in [(P/'outflow/soc_physical.map.v','netlist_sha256'),(P/'soc_physical_cdc.sdc','constraint_sha256'),(R/'tools/generate_physical_cdc.py','generator_sha256')]:assert sha(f)==binding[key]
 timing=timing_summary(P/'outflow/soc_physical.review_timing.rpt');assert all(not v['violations'] for v in timing.values()),timing
 cdc={c:bus_summary(P/f'outflow/soc_physical.bus_{c}.rpt',binding) for c in ['setup','hold']}
 for flow in ['interface','map','pnr','sta_tclsh','pgm']:
  data=(P/(flow+'.log')).read_bytes();t=data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')
  assert not re.search(r'\bFAIL\b|Failed to run command|No bus skew paths found|Skipping Interface Designer',t),flow
  if flow!='sta_tclsh':assert re.search(r'\b'+flow+r'\s*:\s*PASS\b',t),flow
 evidence=[P/'work_pnr/soc_physical.lbf',*[P/'outflow'/('soc_physical.'+n) for n in ['bit','hex','review_timing.rpt','bus_setup.rpt','bus_hold.rpt']]]
 assert all(f.stat().st_mtime>=datetime.datetime.fromisoformat(m['started']).timestamp() for f in evidence),'Stale output'
 evidence += [P/'DISPLAY_MANIFEST.json',B/'implementation_audit.json',Path(__file__),R/'tools/prepare_c9_display_fix.py',R/'tools/run_c9_display_fix.ps1',P/'capture_display.py',R/'build/c9_scanout_startup_20261102/fixed_result.json',regression_path,R/'tools/test_c9_display_c2.py']
 report=dict(status='PASS_OFFLINE_READONLY_DDR_PROBE',synthesis_mode='cong',comb4_packing=0,diagnostic_only=True,board_test_passed=False,flash_written=False,
  controlled_change=m['controlled_change'],timing=timing,cdc=cdc,source_sha256={n:sha(R/n) for n in m['source_sha256']},evidence_sha256={f.relative_to(R).as_posix():sha(f) for f in evidence})
 (P/'implementation_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
