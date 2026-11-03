"""Instrument frozen Pack40 seed3 without changing its pixel/DDR path."""
from pathlib import Path
import datetime,hashlib,json,re,shutil
from c9_probe_image import select
R=Path(__file__).resolve().parents[1]
B=R/'build/c9_sideband_seed3_image_20261103';P=R/'build/c9_stage_image_20261103'
S=R/'team_work/03_ai_soc/c9_live/camera_geometry'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def modified_top(text):
 start=text.index('wire [63:0] sideband_observation;');end=text.index('physical_soc_core soc(',start)
 inst='''wire [63:0] stage_phy_data;wire [159:0] stage_isp_data;wire [31:0] stage_video_data;
wire stage_config_valid,stage_time_valid;
c9_stage_probe stage_monitor(.arst_n(camera_reset_n),.run_async(c9_run),
 .phy_clk(i_mipi_rx_pclk),.isp_clk(pixel2_clk),.video_clk(pixel1_clk),
 .native_vs(w_mipi_rx_vs),.native_hs(w_mipi_rx_hs),.native_de(w_mipi_rx_de),
 .native_wc(sb_wc),.native_dt(sb_dt),.native_vc(sb_vc),.native_ppc(sb_ppc),
 .raw_vs(raw_vs),.raw_de(raw_de),.raw_overflow(raw_overflow),
 .rgb_vs(rgb_vs),.rgb_de(rgb_de),.rgb_valid(rgb_valid),.gray_vs(gray_vs),.gray_de(gray_de),
 .pixel_vs(pixel_vs),.pixel_de(pixel_de),.source_vs(source_vs),.source_de(source_de),
 .mode(mode_sync[1]),.fault(fault2),.config_valid(stage_config_valid),.time_valid(stage_time_valid),
 .phy_data(stage_phy_data),.isp_data(stage_isp_data),.video_data(stage_video_data));
'''
 text=text[:start]+inst+text[end:]
 changes={'.c9_camera_clk(CLK_5M) ' : '.c9_camera_clk(pixel2_clk) '}
 for old,new in [('.c9_camera_clk(CLK_5M)', '.c9_camera_clk(pixel2_clk)'),
  (".c9_camera_data({31'b0,camera_registers_valid_5m,camera_registers_5m})",'.c9_camera_data(stage_isp_data)'),
  ('.c9_phy_data(sideband_observation)','.c9_phy_data(stage_phy_data)'),
  ('.c9_pattern_completed(pat_completed)','.c9_pattern_completed(stage_video_data)'),
  ('.c2_capture_config_valid()', '.c2_capture_config_valid(stage_config_valid)'),
  ('.c2_shared_video_valid()', '.c2_shared_video_valid(stage_time_valid)')]:
  assert text.count(old)==1,old;text=text.replace(old,new)
 return text
def project_xml():
 text=(B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix())
 old=(S/'c9_sideband_probe_small.sv').as_posix();assert text.count(old)==1
 return text.replace(old,(S/'c9_stage_probe.sv').as_posix())
def main():
 image,audit=select(R,'sideband_seed3');assert not P.exists(),'Preserve experiment'
 t=R/'logs/c9_stage_chain_tests_20261103.json';m=json.loads(t.read_text());assert m['status']=='PASS'
 for n,d in m['source_sha256'].items():assert sha(R/n)==d,n
 P.mkdir()
 for name in ['rtl','overrides','vendor_a']:shutil.copytree(B/name,P/name)
 for name in ['physical_soc_core.v','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']+[p.name for p in B.glob('*ram_symbol*.bin')]:shutil.copy2(B/name,P/name)
 (P/'soc_physical_top.sv').write_text(modified_top((B/'soc_physical_top.sv').read_text()),newline='\n')
 (P/'soc_physical.xml').write_text(project_xml(),newline='\n')
 for name in ['bind_cdc.py','capture_geometry.py']:
  (P/name).write_text((B/name).read_text().replace(B.name,P.name).replace('scanout_sideband_observer','scanout_stage_observer'),newline='\n')
 runner=R/'tools/run_c9_stage.ps1';runner.write_text((R/'tools/run_c9_sideband_seed3.ps1').read_text().replace(B.name,P.name),newline='\n')
 files=[p for p in P.rglob('*') if p.is_file()]+[S/'c9_stage_probe.sv']
 record=dict(status='PREPARED_STAGE_DIAGNOSTIC',started=datetime.datetime.now().astimezone().isoformat(),parent_audit_sha256=sha(audit),generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),tests_sha256=sha(t),controlled_change='Native-domain stage run/segment probes. Repurpose camera snapshot to pixel2_clk stage data; pattern-completed word to pixel/source maximums. No pixel, source, DDR, clock, pin or IP parameter changes. Pack40 diagnostic only.',source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'STAGE_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n',newline='\n')
 print('PREPARED stage diagnostic; original qualified image unchanged')
if __name__=='__main__':main()
