"""Gate the isolated synthesis-mode A/B experiment against frozen USER2 C9."""
from pathlib import Path
import datetime,hashlib,json,re,xml.etree.ElementTree as E
from audit_soc_physical import timing_summary,bus_summary
R=Path(__file__).resolve().parents[1]
B=R/'build/c9_ddr_probe_20261101';P=R/'build/c9_ddr_probe_nopack_20261101'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canon=lambda s:E.canonicalize(s,strip_text=True,rewrite_prefixes=True)

def main():
 m=json.loads((P/'NOPACK_MANIFEST.json').read_text())
 assert sha(R/'tools/prepare_c9_ddr_probe_nopack.py')==m['generator_sha256']
 assert sha(R/'tools/run_c9_ddr_probe_nopack.ps1')==m['runner_sha256']
 assert sha(B/'implementation_audit.json')==m['parent_audit_sha256']
 parent=json.loads((B/'implementation_audit.json').read_text())
 assert parent['status']=='PASS_OFFLINE_READONLY_DDR_PROBE'
 for key in ['source_sha256','evidence_sha256']:
  for n,d in parent[key].items():assert sha(R/n)==d,n
 base=json.loads((R/'logs/soc_live_audit.json').read_text())
 for key in ['source_sha256','evidence_sha256']:
  for n,d in base[key].items():assert sha(R/n)==d,n
 for n,d in m['source_sha256'].items():
  f=R/n
  if f.name=='soc_physical.xml':assert hashlib.sha256(f.read_text().encode()).hexdigest()==d,n
  else:assert sha(f)==d,n
 new=(P/'soc_physical.xml').read_text().replace(P.as_posix(),B.as_posix())
 token='<efx:param name="pack-luts-to-comb4" value="0"';assert new.count(token)==1
 new=new.replace(token,'<efx:param name="pack-luts-to-comb4" value="1"',1)
 seed=m.get('pnr_seed',2);assert seed in [1,2]
 seed_token='<efx:param name="seed" value="%d"'%seed;assert new.count(seed_token)==1
 new=new.replace(seed_token,'<efx:param name="seed" value="2"',1)
 assert canon(new)==canon((B/'soc_physical.xml').read_text()),'Only recorded COMB4 setting, route seed and project paths may change'
 tree=E.parse(B/'soc_physical.xml')
 for e in tree.iter():
  if e.tag.endswith('}design_file'):
   old=Path(e.get('name'));target=Path(str(old).replace(str(B),str(P)))
   if old.is_relative_to(B):target=P/old.relative_to(B)
   assert sha(old)==sha(target),'Compiled RTL differs: '+str(old)
 for name in ['soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl','overrides/ddr3_parameter.vh','overrides/ddr3_top.v']:
  if name.endswith('.xml'):assert canon((P/name).read_text())==canon((B/name).read_text()),name
  else:assert sha(P/name)==sha(B/name),name
 for old in B.glob('*ram_symbol*.bin'):assert sha(P/old.name)==sha(old),old.name
 rows=lambda f:[s for s in f.read_text(encoding='utf-8-sig').splitlines() if s and not s.startswith('#')]
 assert rows(P/'outflow/soc_physical.pinout.csv')==rows(B/'outflow/soc_physical.pinout.csv')
 binding=json.loads((P/'cdc_binding.json').read_text());assert binding['status']=='PASS' and binding['pointer_bits']==66
 for f,key in [(P/'outflow/soc_physical.map.v','netlist_sha256'),(P/'soc_physical_cdc.sdc','constraint_sha256'),(R/'tools/generate_physical_cdc.py','generator_sha256')]:assert sha(f)==binding[key],str(f)
 timing=timing_summary(P/'outflow/soc_physical.review_timing.rpt');assert all(not v['violations'] for v in timing.values()),timing
 cdc={corner:bus_summary(P/f'outflow/soc_physical.bus_{corner}.rpt',binding) for corner in ['setup','hold']}
 for flow in ['interface','map','pnr','sta_tclsh','pgm']:
  data=(P/(flow+'.log')).read_bytes();text=data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')
  assert not re.search(r'\bFAIL\b|Failed to run command|No bus skew paths found|Skipping Interface Designer',text),flow
  if flow!='sta_tclsh':assert re.search(r'\b'+flow+r'\s*:\s*PASS\b',text),flow
 evidence=[P/'work_pnr/soc_physical.lbf',P/'outflow/soc_physical.bit',P/'outflow/soc_physical.hex',P/'outflow/soc_physical.review_timing.rpt',P/'outflow/soc_physical.bus_setup.rpt',P/'outflow/soc_physical.bus_hold.rpt']
 assert all(f.stat().st_mtime>=datetime.datetime.fromisoformat(m.get('retry_started',m['started'])).timestamp() for f in evidence),'Stale A/B output'
 evidence += [P/'NOPACK_MANIFEST.json',B/'implementation_audit.json',Path(__file__),R/'tools/prepare_c9_ddr_probe_nopack.py',R/'tools/run_c9_ddr_probe_nopack.ps1',P/'capture_nopack.py']
 out=dict(status='PASS_OFFLINE_READONLY_DDR_PROBE',synthesis_mode='cong',comb4_packing=0,controlled_ab_only=True,diagnostic_only=True,board_test_passed=False,flash_written=False,
          controlled_change=m['controlled_change'],timing=timing,cdc=cdc,source_sha256={n:sha(R/n) for n in m['source_sha256']},evidence_sha256={f.relative_to(R).as_posix():sha(f) for f in evidence})
 (P/'implementation_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
