"""A/B diagnostic: same USER2 RTL and constraints, cong -> speed only."""
from pathlib import Path
import datetime,hashlib,json,shutil,xml.etree.ElementTree as E
R=Path(__file__).resolve().parents[1]
B=R/'build/c9_ddr_probe_20261101';P=R/'build/c9_ddr_probe_speed_20261101'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 a=json.loads((B/'implementation_audit.json').read_text());assert a['status']=='PASS_OFFLINE_READONLY_DDR_PROBE'
 for key in ['source_sha256','evidence_sha256']:
  for n,d in a[key].items():assert sha(R/n)==d,n
 assert not P.exists(),'Preserve existing A/B experiment'
 shutil.copytree(B,P)
 (P/'implementation_audit.json').write_text('{"status":"PENDING_SPEED_BUILD_DO_NOT_PROGRAM"}\n')
 q=lambda s:'{http://www.efinixinc.com/enf_proj}'+s
 text=(B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix())
 old='<efx:param name="mode" value="cong"';assert text.count(old)==1
 text=text.replace(old,'<efx:param name="mode" value="speed"',1)
 (P/'soc_physical.xml').write_text(text,newline='\n')
 (P/'bind_cdc.py').write_text((B/'bind_cdc.py').read_text().replace(B.name,P.name))
 runner=R/'tools/run_c9_ddr_probe_speed.ps1'
 runner.write_text((R/'tools/run_c9_ddr_probe.ps1').read_text().replace(B.name,P.name),newline='\n')
 # Retain the already verified capture implementation in this private root.
 capture=(R/'tools/capture_c9_ddr_probe.py').read_text()
 old="R=Path(__file__).resolve().parents[1];E=R/'tools/efinity/2026.1';P=R/'build/c9_ddr_probe_20261101'"
 assert capture.count(old)==1
 capture=capture.replace(old,"R=Path(__file__).resolve().parents[2];E=R/'tools/efinity/2026.1';P=Path(__file__).resolve().parent",1)
 capture=capture.replace("cpu_firmware_loaded=False,","cpu_firmware_loaded=False,synthesis_variant='speed',",1)
 (P/'capture_speed.py').write_text(capture,newline='\n')
 files=[P/n for n in ['physical_soc_core.v','soc_physical_top.sv','soc_physical.xml','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl','bind_cdc.py']]
 files+=list(P.glob('*ram_symbol*.bin'))+[R/'team_work/03_ai_soc/c9_live/debug/c9_ddr_probe.sv']
 record=dict(status='PREPARED_SPEED_AB_ONLY',started=datetime.datetime.now().astimezone().isoformat(),flash_written=False,
             parent_audit_sha256=sha(B/'implementation_audit.json'),generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),
             controlled_change='Synthesis cong -> speed; COMB4=1, CONGESTION_2, seed=2, all RTL, clocks, pins and DDR parameters retained',
             source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'SPEED_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

if __name__=='__main__':main()
