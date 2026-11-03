"""Clone qualified display C9; expose existing rejected-frame geometry only."""
from pathlib import Path
import datetime,hashlib,json,shutil
R=Path(__file__).resolve().parents[1]
B=R/'build/c9_display_fix_20261102';P=R/'build/c9_camera_geometry_image_20261102'
S=R/'team_work/03_ai_soc/c9_live/camera_geometry'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def modified_top(text):
 changes={
  'physical_soc_core soc(':'''wire capture_record_valid,capture_record_complete;
wire [15:0] capture_record_width,capture_record_height;
wire [31:0] geometry_flags;
c9_capture_geometry capture_geometry(.clk(pixel1_clk),.arst_n(camera_reset_n),
 .record_valid(capture_record_valid),.record_complete(capture_record_complete),
 .record_width(capture_record_width),.record_height(capture_record_height),
 .source_flags({run_sync[3],mode_sync[1],pat_busy,fault2}),.flags(geometry_flags));
physical_soc_core soc(''',
  '.c9_source_flags({28\'b0,run_sync[3],mode_sync[1],pat_busy,fault2})':'.c9_source_flags(geometry_flags)',
  '.c2_capture_record_valid()':'.c2_capture_record_valid(capture_record_valid)',
  '.c2_capture_record_complete()':'.c2_capture_record_complete(capture_record_complete)',
  '.c2_capture_record_width()':'.c2_capture_record_width(capture_record_width)',
  '.c2_capture_record_height()':'.c2_capture_record_height(capture_record_height)'}
 for old,new in changes.items():assert text.count(old)==1,old;text=text.replace(old,new)
 return text
def project_xml():
 text=(B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix())
 needle='<efx:top_module name="soc_physical_top" />';assert text.count(needle)==1
 return text.replace(needle,needle+'\n        <efx:design_file name="'+(S/'c9_capture_geometry.sv').as_posix()+'" version="default" library="default" />')
def main():
 a=json.loads((B/'implementation_audit.json').read_text());assert a['status']=='PASS_OFFLINE_READONLY_DDR_PROBE'
 for field in ['source_sha256','evidence_sha256']:
  for n,d in a[field].items():assert sha(R/n)==d,n
 assert not P.exists(),'Preserve existing experiment'
 test=R/'logs/c9_camera_geometry_tests_20261102.json';t=json.loads(test.read_text());assert t['status']=='PASS'
 for n,d in t['source_sha256'].items():assert sha(R/n)==d,n
 P.mkdir()
 for directory in ['overrides','rtl','vendor_a']:shutil.copytree(B/directory,P/directory)
 names=['physical_soc_core.v','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']+[p.name for p in B.glob('*ram_symbol*.bin')]
 for n in names:shutil.copyfile(B/n,P/n)
 (P/'soc_physical_top.sv').write_text(modified_top((B/'soc_physical_top.sv').read_text()),newline='\n')
 (P/'soc_physical.xml').write_text(project_xml(),newline='\n')
 (P/'bind_cdc.py').write_text((B/'bind_cdc.py').read_text().replace(B.name,P.name),newline='\n')
 runner=R/'tools/run_c9_camera_geometry.ps1'
 runner.write_text((R/'tools/run_c9_display_fix.ps1').read_text().replace(B.name,P.name),newline='\n')
 files=[P/n for n in [*names,'soc_physical_top.sv','soc_physical.xml','bind_cdc.py']]+[S/'c9_capture_geometry.sv']
 manifest=dict(status='PREPARED_READONLY_GEOMETRY',started=datetime.datetime.now().astimezone().isoformat(),parent_audit_sha256=sha(B/'implementation_audit.json'),
  generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),test_report_sha256=sha(test),
  controlled_change='Connect existing capture width/height/complete to reserved upper source_flags via video-domain observer; no pixel/control/DDR/clock/pin changes',
  source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'GEOMETRY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('PREPARED isolated read-only geometry diagnostic; qualified active profile unchanged')
if __name__=='__main__':main()
