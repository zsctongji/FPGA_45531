"""Isolate the startup scanout fix from the board-qualified COMB4-off C9."""
from pathlib import Path
import datetime,hashlib,json,shutil
R=Path(__file__).resolve().parents[1]
B=R/'build/c9_ddr_probe_nopack_20261101';P=R/'build/c9_display_fix_20261102'
OLD=R/'projects/06_soc_c2/rtl/c2_video_scanout.sv'
FIX=R/'team_work/03_ai_soc/c9_live/display_fix/c2_video_scanout.sv'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=json.loads((B/'implementation_audit.json').read_text());assert a['status']=='PASS_OFFLINE_READONLY_DDR_PROBE'
 for field in ['source_sha256','evidence_sha256']:
  for n,d in a[field].items():assert sha(R/n)==d,n
 assert not P.exists(),'Preserve existing display experiment'
 P.mkdir()
 for directory in ['overrides','rtl','vendor_a']:shutil.copytree(B/directory,P/directory)
 names=['physical_soc_core.v','soc_physical_top.sv','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']
 names += [p.name for p in B.glob('*ram_symbol*.bin')]
 for n in names:shutil.copyfile(B/n,P/n)
 text=(B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix())
 assert text.count(OLD.as_posix())==1
 (P/'soc_physical.xml').write_text(text.replace(OLD.as_posix(),FIX.as_posix()),newline='\n')
 (P/'bind_cdc.py').write_text((B/'bind_cdc.py').read_text().replace(B.name,P.name),newline='\n')
 runner=R/'tools/run_c9_display_fix.ps1'
 runner.write_text((R/'tools/run_c9_ddr_probe_nopack.ps1').read_text().replace(B.name,P.name),newline='\n')
 capture=(B/'capture_nopack.py').read_text().replace("synthesis_variant='cong_comb4_off_seed2'","synthesis_variant='cong_comb4_off_seed2_scanout_startup_fix'")
 (P/'capture_display.py').write_text(capture,newline='\n')
 files=[P/n for n in [*names,'soc_physical.xml','bind_cdc.py','capture_display.py']]+[FIX]
 manifest=dict(status='PREPARED_SCANOUT_FIX_ONLY',started=datetime.datetime.now().astimezone().isoformat(),
  parent_audit_sha256=sha(B/'implementation_audit.json'),generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),
  controlled_change='Scanout startup guard only; COMB4=0, cong/CONGESTION_2/seed2 and DDR/clock/pin configuration retained',
  source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'DISPLAY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('PREPARED isolated display fix; original C9/C10 and DDR profile unchanged')
if __name__=='__main__':main()
