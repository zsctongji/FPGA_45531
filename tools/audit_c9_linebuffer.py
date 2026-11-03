"""Qualify diagnostic implementation; all pixel-path inputs remain pinned."""
from pathlib import Path
import datetime,hashlib,json,re,xml.etree.ElementTree as E
from c9_probe_image import select
from prepare_c9_linebuffer import B,P,R,modified_top,project_xml
from audit_soc_physical import timing_summary,bus_summary
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(s):return E.canonicalize(s,strip_text=True,rewrite_prefixes=True)
def main():
 image,parent=select(R,'stage_min');m=json.loads((P/'LINEBUFFER_MANIFEST.json').read_text())
 assert sha(parent)==m['parent_audit_sha256']
 assert sha(R/'tools/prepare_c9_linebuffer.py')==m['generator_sha256'] and sha(R/'tools/run_c9_linebuffer.ps1')==m['runner_sha256']
 for n,d in m['source_sha256'].items():
  f=R/n
  if f.name=='soc_physical.xml':assert hashlib.sha256(f.read_text().encode()).hexdigest()==d,n
  else:assert sha(f)==d,n
 assert (P/'soc_physical_top.sv').read_text()==modified_top((B/'soc_physical_top.sv').read_text())
 assert canon((P/'soc_physical.xml').read_text())==canon(project_xml())
 for e in E.parse(B/'soc_physical.xml').iter():
  if not e.tag.endswith('}design_file'):continue
  old=Path(e.get('name'))
  if old.name in ['soc_physical_top.sv','c9_sideband_probe_small.sv']:continue
  new=P/old.relative_to(B) if old.is_relative_to(B) else old
  assert sha(new)==sha(old),'Changed pixel/DDR/IP source: '+str(old)
 for name in ['soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']:
  if name.endswith('.xml'):assert canon((B/name).read_text())==canon((P/name).read_text())
  else:assert sha(B/name)==sha(P/name)
 tests=[R/'logs/c9_linebuffer_tests_20261103.json',R/'logs/c9_linebuffer_decode_tests_20261103.json']
 assert sha(tests[0])==m['tests_sha256']
 for path in tests:
  test=json.loads(path.read_text());assert test['status']=='PASS'
  for field in ['source_sha256','generated_sha256']:
   for n,d in test.get(field,{}).items():assert sha(R/n)==d,n
 fwcheck=R/'logs/c9_stage_min_firmware_audit_20261103.json';fw=json.loads(fwcheck.read_text())
 assert fw['status']=='PASS_NO_CUSTOM_ACCELERATOR_OPCODE_IN_EXECUTABLE_SECTIONS'
 for n,d in fw['source_sha256'].items():assert sha(R/n)==d,n
 rows=lambda p:[s for s in p.read_text(encoding='utf-8-sig').splitlines() if s and not s.startswith('#')]
 assert rows(B/'outflow/soc_physical.pinout.csv')==rows(P/'outflow/soc_physical.pinout.csv')
 binding=json.loads((P/'cdc_binding.json').read_text());assert binding['status']=='PASS' and binding['pointer_bits']==66
 for f,key in [(P/'outflow/soc_physical.map.v','netlist_sha256'),(P/'soc_physical_cdc.sdc','constraint_sha256'),(R/'tools/generate_physical_cdc.py','generator_sha256')]:assert sha(f)==binding[key]
 timing=timing_summary(P/'outflow/soc_physical.review_timing.rpt');assert all(not v['violations'] for v in timing.values()),timing
 cdc={c:bus_summary(P/f'outflow/soc_physical.bus_{c}.rpt',binding) for c in ['setup','hold']}
 for flow in ['interface','map','pnr','sta_tclsh','pgm']:
  data=(P/(flow+'.log')).read_bytes();text=data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')
  assert not re.search(r'\bFAIL\b|Failed to run command|No bus skew paths found|Skipping Interface Designer',text),flow
  if flow!='sta_tclsh':assert re.search(r'\b'+flow+r'\s*:\s*PASS\b',text),flow
 evidence=[P/'work_pnr/soc_physical.lbf',*[P/'outflow'/('soc_physical.'+n) for n in ['bit','hex','review_timing.rpt','bus_setup.rpt','bus_hold.rpt']]]
 assert all(f.stat().st_mtime>=datetime.datetime.fromisoformat(m['started']).timestamp() for f in evidence),'Stale/missing output'
 evidence += [P/'LINEBUFFER_MANIFEST.json',parent,Path(__file__),R/'tools/prepare_c9_linebuffer.py',R/'tools/run_c9_linebuffer.ps1',*tests,fwcheck,R/'tools/audit_c9_stage_min_firmware.py',P/'cdc_binding.json',P/'capture_geometry.py',R/'tools/check_c9_linebuffer.py',R/'tools/run_c9_linebuffer.py']
 result=dict(status='PASS_OFFLINE_READONLY_DDR_PROBE',diagnostic_only=True,board_test_passed=False,flash_written=False,controlled_change=m['controlled_change'],diagnostic_pack_type=1,timing=timing,cdc=cdc,source_sha256={n:sha(R/n) for n in m['source_sha256']},evidence_sha256={p.relative_to(R).as_posix():sha(p) for p in evidence})
 (P/'implementation_audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(status=result['status'],timing=timing,image_sha256=sha(P/'outflow/soc_physical.bit')),indent=2))
if __name__=='__main__':main()
