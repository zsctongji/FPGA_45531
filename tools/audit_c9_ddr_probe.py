"""Offline gate for temporary USER2 status instrumentation, not a release."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as E
import prepare_c9_ddr_probe as g
from audit_soc_physical import timing_summary,bus_summary
R=g.ROOT;B=g.BASE;P=g.P
sha=g.sha

def main():
 m=json.loads((P/'PROBE_MANIFEST.json').read_text())
 assert sha(R/'tools/prepare_c9_ddr_probe.py')==m['generator_sha256']
 base=R/'logs/soc_live_audit.json';a=json.loads(base.read_text());assert sha(base)==m['base_audit_sha256']
 for key in ['source_sha256','evidence_sha256']:
  for n,d in a[key].items():assert sha(R/n)==d,n
 expected=g.expected_texts()
 for n,t in expected.items():
  f=P/n
  if f.suffix=='.xml':
   assert E.canonicalize(f.read_text(),strip_text=True,rewrite_prefixes=True)==E.canonicalize(t,strip_text=True,rewrite_prefixes=True),n
   assert hashlib.sha256(t.encode()).hexdigest()==m['source_sha256'][f.relative_to(R).as_posix()]
  else:assert f.read_text()==t and sha(f)==m['source_sha256'][f.relative_to(R).as_posix()],n
 for n,d in m['source_sha256'].items():
  if (R/n).suffix!='.xml':assert sha(R/n)==d,n
 for n,d in a['source_sha256'].items():
  f=R/n
  if f.is_relative_to(B) and f.name not in expected:assert sha(P/f.relative_to(B))==d,n
 for i in range(4):
  n=f'EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol{i}.bin'
  old=(B/n).read_text().split();new=(P/n).read_text().split()
  assert len(old)==len(new)==1024 and old[1:]==new[1:] and int(new[0],2)==(0x6f if i==0 else 0)
 for n in ['review_timing.tcl','overrides/ddr3_parameter.vh','overrides/ddr3_top.v']:
  assert (P/n).read_bytes()==(B/n).read_bytes(),n
 pinrows=lambda p:[s for s in p.read_text(encoding='utf-8-sig').splitlines() if s and not s.startswith('#')]
 assert pinrows(P/'outflow/soc_physical.pinout.csv')==pinrows(B/'outflow/soc_physical.pinout.csv'),'Physical pinout changed'
 tests=json.loads((R/'logs/c9_ddr_probe_rtl.json').read_text());assert tests['status']=='PASS'
 for n,d in tests['source_sha256'].items():assert sha(R/n)==d,n
 binding=json.loads((P/'cdc_binding.json').read_text());assert binding['status']=='PASS' and binding['pointer_bits']==66
 assert sha(P/'outflow/soc_physical.map.v')==binding['netlist_sha256']
 assert sha(P/'soc_physical_cdc.sdc')==binding['constraint_sha256']
 timing=timing_summary(P/'outflow/soc_physical.review_timing.rpt')
 assert all(not v['violations'] for v in timing.values()),timing
 cdc={corner:bus_summary(P/f'outflow/soc_physical.bus_{corner}.rpt',binding) for corner in ['setup','hold']}
 for flow in ['interface','map','pnr','sta_tclsh','pgm']:
  data=(P/(flow+'.log')).read_bytes();text=data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')
  assert not re.search(r'\bFAIL\b|Failed to run command|No bus skew paths found|Skipping Interface Designer',text),flow
  if flow not in ['sta_tclsh']:assert re.search(r'\b'+flow+r'\s*:\s*PASS\b',text),flow
 evidence=[P/'work_pnr/soc_physical.lbf',P/'outflow/soc_physical.bit',P/'outflow/soc_physical.hex',P/'outflow/soc_physical.review_timing.rpt',P/'outflow/soc_physical.bus_setup.rpt',P/'outflow/soc_physical.bus_hold.rpt']
 source_time=max((R/n).stat().st_mtime for n in m['source_sha256'] if (R/n).suffix!='.xml')
 assert all(p.stat().st_mtime>=source_time for p in evidence),'Stale copied outputs'
 evidence += [P/'PROBE_MANIFEST.json',R/'logs/c9_ddr_probe_rtl.json',Path(__file__),R/'tools/prepare_c9_ddr_probe.py',R/'tools/run_c9_ddr_probe.ps1']
 result=dict(status='PASS_OFFLINE_READONLY_DDR_PROBE',diagnostic_only=True,board_test_passed=False,flash_written=False,timing=timing,cdc=cdc,
             source_sha256={n:sha(R/n) for n in m['source_sha256']},evidence_sha256={p.relative_to(R).as_posix():sha(p) for p in evidence},
             scope='CPU-independent USER2 status; multi-bit banks are best-effort and must be read repeatedly; no functional control outputs')
 (P/'implementation_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
