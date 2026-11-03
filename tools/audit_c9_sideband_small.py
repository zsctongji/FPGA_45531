"""Fail closed on unrelated RTL, DDR, pin, clock, timing or CDC changes."""
from pathlib import Path
import datetime,hashlib,json,re,xml.etree.ElementTree as E
from audit_soc_physical import timing_summary,bus_summary
from prepare_c9_sideband_small import modified_top,project_xml
from patch_c9_sideband_vendor import patched_bytes
def expected_capture():
 return (B/'capture_geometry.py').read_text().replace('scanout_geometry_observer','scanout_sideband_observer')
R=Path(__file__).resolve().parents[1];B=R/'build/c9_camera_geometry_image_20261102';P=R/'build/c9_sideband_small_image_20261103'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(s):return E.canonicalize(s,strip_text=True,rewrite_prefixes=True)
def main():
 m=json.loads((P/'SIDEBAND_MANIFEST.json').read_text());parent=json.loads((B/'implementation_audit.json').read_text())
 assert parent['status']=='PASS_OFFLINE_READONLY_DDR_PROBE' and sha(B/'implementation_audit.json')==m['parent_audit_sha256']
 for field in ['source_sha256','evidence_sha256']:
  for n,d in parent[field].items():assert sha(R/n)==d,n
 assert sha(R/'tools/prepare_c9_sideband_small.py')==m['generator_sha256']
 assert sha(R/'tools/run_c9_sideband_small.ps1')==m['runner_sha256']
 for n,d in m['source_sha256'].items():
  p=R/n
  if p.name=='soc_physical.xml':assert hashlib.sha256(p.read_text().encode()).hexdigest()==d,n
  else:assert sha(p)==d,n
 assert (P/'soc_physical_top.sv').read_text()==modified_top((B/'soc_physical_top.sv').read_text())
 assert canon((P/'soc_physical.xml').read_text())==canon(project_xml())
 assert (P/'capture_geometry.py').read_text()==expected_capture(),'USER2 capture protocol changed'
 for e in E.parse(B/'soc_physical.xml').iter():
  if e.tag.endswith('}design_file'):
   old=Path(e.get('name'));target=P/old.relative_to(B) if old.is_relative_to(B) else old
   if old.name=='csi_rx_controller.sv':assert target.read_bytes()==patched_bytes(old.read_bytes()),'Vendor patch differs'
   elif old.name!='soc_physical_top.sv':assert sha(old)==sha(target),'Uncontrolled compiled RTL: '+str(old)
 for name in ['soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl','overrides/ddr3_parameter.vh','overrides/ddr3_top.v']:
  if name.endswith('.xml'):assert canon((P/name).read_text())==canon((B/name).read_text())
  else:assert sha(P/name)==sha(B/name)
 tests=R/'logs/c9_sideband_small_tests_20261103.json';test=json.loads(tests.read_text())
 assert sha(tests)==m['test_report_sha256'] and test['status']=='PASS'
 for n,d in test['source_sha256'].items():assert sha(R/n)==d,n
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
 evidence += [P/'SIDEBAND_MANIFEST.json',B/'implementation_audit.json',Path(__file__),R/'tools/prepare_c9_sideband_small.py',R/'tools/run_c9_sideband_small.ps1',tests,P/'cdc_binding.json',P/'capture_geometry.py',R/'tools/prepare_c9_geometry_capture.py']
 report=dict(status='PASS_OFFLINE_READONLY_DDR_PROBE',diagnostic_only=True,board_test_passed=False,flash_written=False,
  controlled_change=m['controlled_change'],timing=timing,cdc=cdc,
  source_sha256={n:sha(R/n) for n in m['source_sha256']},evidence_sha256={f.relative_to(R).as_posix():sha(f) for f in evidence})
 (P/'implementation_audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],timing=timing,image_sha256=sha(P/'outflow/soc_physical.bit'),board_test_passed=False),indent=2))
if __name__=='__main__':main()
