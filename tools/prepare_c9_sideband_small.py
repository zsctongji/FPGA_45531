"""Clone audited capture observer; measure actual CSI HS/valid without changing pixels."""
from pathlib import Path
import datetime,hashlib,json,shutil
R=Path(__file__).resolve().parents[1]
B=R/'build/c9_camera_geometry_image_20261102';P=R/'build/c9_sideband_small_image_20261103'
S=R/'team_work/03_ai_soc/c9_live/camera_geometry'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def modified_top(text):
 import re
 text=text.replace('csi_rx_controller inst_efx_csi2_rx',"wire [15:0] sb_wc;wire [5:0] sb_dt;wire [3:0] sb_ppc;wire [1:0] sb_vc;\ncsi_rx_controller inst_efx_csi2_rx",1)
 needle='.pixel_data_valid';pos=text.index(needle)
 text=text[:pos]+'.pixel_wordcount(sb_wc),.pixel_datatype(sb_dt),.pixel_vc(sb_vc),\n              '+text[pos:]
 text,n=re.subn(r'\.pixel_per_clk\s*\(\s*\)', '.pixel_per_clk(sb_ppc)',text);assert n==1
 old=".c9_phy_data({31'b0,camera_fault,mipi_debug_out})";assert text.count(old)==1
 text=text.replace(old,'.c9_phy_data(sideband_observation)')
 inst="wire [63:0] sideband_observation;\nc9_sideband_probe sb_monitor(.clk(i_mipi_rx_pclk),.arst_n(camera_reset_n),.run_async(c9_run),\n .hs(w_mipi_rx_hs),.de(w_mipi_rx_de),.fault(camera_fault),\n .pixel_wordcount(sb_wc),.pixel_datatype(sb_dt),.pixel_per_clk(sb_ppc),.pixel_vc(sb_vc),.observation(sideband_observation));\nphysical_soc_core soc("
 assert text.count('physical_soc_core soc(')==1
 return text.replace('physical_soc_core soc(',inst)

def project_xml():
 text=(B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix())
 needle='<efx:top_module name="soc_physical_top" />';assert text.count(needle)==1
 return text.replace(needle,needle+'\n        <efx:design_file name="'+(S/'c9_sideband_probe_small.sv').as_posix()+'" version="default" library="default" />')
def main():
 a=json.loads((B/'implementation_audit.json').read_text());assert a['status']=='PASS_OFFLINE_READONLY_DDR_PROBE'
 for field in ['source_sha256','evidence_sha256']:
  for n,d in a[field].items():assert sha(R/n)==d,n
 assert not P.exists(),'Preserve existing experiment'
 test=R/'logs/c9_sideband_small_tests_20261103.json';t=json.loads(test.read_text());assert t['status']=='PASS'
 for n,d in t['source_sha256'].items():assert sha(R/n)==d,n
 P.mkdir()
 for directory in ['overrides','rtl','vendor_a']:shutil.copytree(B/directory,P/directory)
 names=['physical_soc_core.v','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']+[p.name for p in B.glob('*ram_symbol*.bin')]
 for n in names:shutil.copyfile(B/n,P/n)
 from patch_c9_sideband_vendor import patched_bytes
 v=P/'vendor_a/rtl/csi_rx_controller.sv';v.write_bytes(patched_bytes((B/'vendor_a/rtl/csi_rx_controller.sv').read_bytes()))
 (P/'soc_physical_top.sv').write_text(modified_top((B/'soc_physical_top.sv').read_text()),newline='\n')
 (P/'soc_physical.xml').write_text(project_xml(),newline='\n')
 (P/'capture_geometry.py').write_text((B/'capture_geometry.py').read_text().replace('scanout_geometry_observer','scanout_sideband_observer'),newline='\n')
 (P/'bind_cdc.py').write_text((B/'bind_cdc.py').read_text().replace(B.name,P.name),newline='\n')
 runner=R/'tools/run_c9_sideband_small.ps1'
 runner_text=(R/'tools/run_c9_camera_geometry.ps1').read_text()
 assert runner_text.count("'build/"+B.name+"'")==1,'Unexpected runner project path'
 runner_text=runner_text.replace(B.name,P.name)
 assert "'build/"+P.name+"'" in runner_text and B.name not in runner_text
 runner.write_text(runner_text,newline='\n')
 files=[P/n for n in [*names,'soc_physical_top.sv','soc_physical.xml','bind_cdc.py','capture_geometry.py']]+[S/'c9_sideband_probe_small.sv',P/'vendor_a/rtl/csi_rx_controller.sv',R/'tools/patch_c9_sideband_vendor.py']
 manifest=dict(status='PREPARED_READONLY_GEOMETRY',started=datetime.datetime.now().astimezone().isoformat(),parent_audit_sha256=sha(B/'implementation_audit.json'),
  generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),test_report_sha256=sha(test),
  controlled_change='Enable existing pixel sideband ports through plain vendor wrapper; record RAW10 VC0 PPC set after RUN. Protected IP tail and all IP parameters retained; pixel/control/DDR/clock/pin paths unchanged',
  source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'SIDEBAND_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('PREPARED isolated read-only geometry diagnostic; qualified active profile unchanged')
if __name__=='__main__':main()
