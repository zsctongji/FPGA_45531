"""Build an isolated fixed-RAW10 linebuffer candidate from qualified stage_min."""
from pathlib import Path
import datetime,hashlib,json,shutil
from c9_probe_image import select
R=Path(__file__).resolve().parents[1];B=R/'build/c9_stage_min_image_20261103';P=R/'build/c9_linebuffer_v2_image_20261103'
S=R/'team_work/03_ai_soc/c9_live/camera_geometry'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def modified_top(text):
 old='wire raw_vs,raw_hs,raw_de;wire [15:0] raw2;wire raw_overflow,gray_overflow;'
 inst='''wire norm_vs,norm_hs,norm_de,norm_fault,norm_armed,norm_run;wire [31:0] norm_data;
wire [6:0] norm_errors;wire [18:0] norm_last_beats;wire [15:0] norm_input_frames,norm_output_lines;
wire native_transport_problem=!mipi_debug_out[15] || |(mipi_debug_out & 32'h0007447d);
c9_stage_run norm_run_sync(i_mipi_rx_pclk,camera_reset_n,c9_run,norm_run);
reg [24:0] norm_debug_seen;
always @(posedge i_mipi_rx_pclk or negedge camera_reset_n)
 if(!camera_reset_n)norm_debug_seen<=0;else if(!norm_run)norm_debug_seen<=0;
 else norm_debug_seen<=norm_debug_seen | mipi_debug_out[24:0];
c9_raw10_linebuffer normalizer(.clk(i_mipi_rx_pclk),.arst_n(camera_reset_n),.run_async(c9_run),
 .vs(w_mipi_rx_vs),.de(w_mipi_rx_de),
 .data({w_mipi_rx_data[39:32],w_mipi_rx_data[29:22],w_mipi_rx_data[19:12],w_mipi_rx_data[9:2]}),
 .wordcount(sb_wc),.datatype(sb_dt),.vc(sb_vc),.ppc(sb_ppc),.transport_fault(native_transport_problem),
 .ovs(norm_vs),.ohs(norm_hs),.ode(norm_de),.odata(norm_data),.fault(norm_fault),.armed(norm_armed),
 .errors(norm_errors),.last_frame_beats(norm_last_beats),.input_frames(norm_input_frames),.output_lines(norm_output_lines));
wire [63:0] norm_observation={8'hf1,norm_run,norm_armed,norm_fault,norm_errors,norm_last_beats,norm_input_frames[1:0],norm_debug_seen};
'''
 assert text.count(old)==1;text=text.replace(old,inst+old)
 old=".vs(w_mipi_rx_vs),.hs(w_mipi_rx_hs),.de(w_mipi_rx_de && w_mipi_rx_hs),\n .data({w_mipi_rx_data[39:32],w_mipi_rx_data[29:22],w_mipi_rx_data[19:12],w_mipi_rx_data[9:2]}),"
 assert text.count(old)==1;text=text.replace(old,'.vs(norm_vs),.hs(norm_hs),.de(norm_de),\n .data(norm_data),')
 old="else if(|(mipi_debug_out & 32'h0000447d))camera_fault<=1;"
 assert text.count(old)==1;text=text.replace(old,'else if(norm_armed && (native_transport_problem || norm_fault))camera_fault<=1;')
 import re
 text,n=re.subn(r'\.axi_clk\s*\(1\x27b0\)', '.axi_clk(i_mipi_rx_pclk)',text);assert n==1
 text,n=re.subn(r'\.axi_reset_n\s*\(1\x27b0\)', '.axi_reset_n(camera_reset_n)',text);assert n==1
 for old,new in [('.c9_phy_data(stage_phy_data)','.c9_phy_data(norm_observation)')]:
  assert text.count(old)==1;text=text.replace(old,new)
 return text
def project_xml():
 text=(B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix())
 needle='<efx:top_module name="soc_physical_top" />';assert text.count(needle)==1
 return text.replace(needle,needle+'\n        <efx:design_file name="'+(S/'c9_raw10_linebuffer.sv').as_posix()+'" version="default" library="default" />')
def main():
 image,audit=select(R,'stage_min');assert not P.exists(),'Preserve experiment'
 test=R/'logs/c9_linebuffer_tests_20261103.json';t=json.loads(test.read_text());assert t['status']=='PASS'
 for field in ['source_sha256','generated_sha256']:
  for n,d in t[field].items():assert sha(R/n)==d,n
 P.mkdir()
 for name in ['rtl','vendor_a','overrides']:shutil.copytree(B/name,P/name)
 for name in ['physical_soc_core.v','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']+[p.name for p in B.glob('*ram_symbol*.bin')]:shutil.copy2(B/name,P/name)
 (P/'soc_physical_top.sv').write_text(modified_top((B/'soc_physical_top.sv').read_text()),newline='\n')
 (P/'soc_physical.xml').write_text(project_xml(),newline='\n')
 for name in ['bind_cdc.py','capture_geometry.py']:
  (P/name).write_text((B/name).read_text().replace(B.name,P.name).replace('scanout_stage_min_observer','scanout_raw10_linebuffer'),newline='\n')
 runner=R/'tools/run_c9_linebuffer.ps1';runner.write_text((R/'tools/run_c9_stage_min.ps1').read_text().replace(B.name,P.name),newline='\n')
 files=[p for p in P.rglob('*') if p.is_file()]+[S/'c9_raw10_linebuffer.sv']
 m=dict(status='PREPARED_RAW10_LINEBUFFER_CANDIDATE',started=datetime.datetime.now().astimezone().isoformat(),parent_audit_sha256=sha(audit),generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),tests_sha256=sha(test),controlled_change='Fixed RAW10 VC0 whole-line ping-pong buffer before unchanged RAW split/ISP/luma/gray split. Validate WC/PPC and whole-frame payload; error stops publication. Enable vendor AXI/debug in native pixel clock, require init_done, fault mask 0x7447d (FIFO empty excluded). Repurpose PHY snapshot only; video word6 retains its native video-clock stage maxima. DDR, pin/PLL/SDC/IP parameters unchanged. Lightweight diagnostic has no TinyML accelerator.',source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'LINEBUFFER_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n')
 print('PREPARED isolated RAW10 linebuffer candidate; active profile unchanged')
if __name__=='__main__':main()
