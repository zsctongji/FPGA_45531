"""Derive an isolated C7 live acceptance project; preserve qualified C7/C24."""
from pathlib import Path
import hashlib,json,re,shutil,xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'projects/07_soc_physical';P=ROOT/'projects/09_c7_live_acceptance'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 prior=json.loads((ROOT/'fpga_bitstreams/soc_physical_100mhz/BUILD_RECORD.json').read_text())
 assert prior['board_cpu_test_passed'] and prior['board_static_tinyml_passed']
 assert sha(BASE/'PHYSICAL_MANIFEST.json')==prior['source_manifest_sha256']
 if P.exists() and not(P/'LIVE_MANIFEST.json').exists():raise RuntimeError('Unrelated live directory exists')
 P.mkdir(parents=True,exist_ok=True);derived={}
 for src in BASE.rglob('*'):
  rel=src.relative_to(BASE)
  if not src.is_file() or any(x.startswith('work_') or x=='outflow' for x in rel.parts):continue
  dst=P/rel;dst.parent.mkdir(parents=True,exist_ok=True)
  data=src.read_bytes()
  if src.suffix in ['.v','.sv','.vh','.xml','.sdc','.json','.tcl']:data=data.replace(BASE.as_posix().encode(),P.as_posix().encode())
  dst.write_bytes(data);derived[rel.as_posix()]=dict(original=src.relative_to(ROOT).as_posix(),original_sha256=sha(src))
 core=(P/'physical_soc_core.v').read_text()
 # This is a dedicated video/CPU/cache diagnostic. Remove the disabled C3
 # sensor peripheral from this variant to leave routing headroom for counters.
 # The qualified C7 and its real sensor backend remain unchanged.
 begin=core.index('c3_apb_peripheral c3_peripheral(')
 end=core.index(');',begin)+2
 core=core[:begin]+'''assign c3_apb_ready=1'b1;
assign c3_apb_prdata=32'b0;
assign c3_apb_error=1'b1;
assign c3_sensor_scl_drive_low=1'b0;
assign c3_sensor_sda_drive_low=1'b0;
assign c3_buzzer=1'b0;
assign c3_alarm_led=1'b0;
'''+core[end:]
 extra='''input wire c9_camera_clk,c9_phy_clk,
input wire [159:0] c9_camera_data,input wire [63:0] c9_phy_data,
input wire [31:0] c9_pattern_completed,c9_source_flags,
output wire c9_source_run,c9_pattern_mode,c9_pattern_valid,
input wire c9_pattern_ready,output wire [7:0] c9_pattern_gray,
'''
 needle='output wire integrated_reset,';assert core.count(needle)==1;core=core.replace(needle,needle+'\n'+extra,1)
 needle="wire c3_page=apb_paddr[15:8]==8'h10;"
 core=core.replace(needle,needle+"\nwire c9_page=apb_paddr[15:8]==8'he0;\nwire [31:0] c9_prdata;wire c9_ready,c9_error;",1)
 for what,new in [('prdata','c9_prdata'),('pready','c9_ready'),('pslverror','c9_error')]:
  old='assign apb_'+what+'=c3_page?';assert core.count(old)==1
  core=core.replace(old,'assign apb_'+what+'=c9_page?'+new+':c3_page?',1)
 assert '.psel(apb_psel && !c3_page)' in core
 core=core.replace('.psel(apb_psel && !c3_page)','.psel(apb_psel && !c3_page && !c9_page)',1)
 block='''
c9_live_control acceptance_control(
.arst_n(!io_systemReset),.pclk(i_peripheralClk),.mem_clk(io_memoryClk),.video_clk(c2_video_clk),.display_clk(c2_display_clk),.camera_clk(c9_camera_clk),.phy_clk(c9_phy_clk),
.paddr(apb_paddr[7:0]),.psel(apb_psel && c9_page),.penable(apb_penable),.pwrite(apb_pwrite),.pwdata(apb_pwdata),.pready(c9_ready),.prdata(c9_prdata),.pslverror(c9_error),
.source_run(c9_source_run),.pattern_mode(c9_pattern_mode),.pattern_valid(c9_pattern_valid),.pattern_ready(c9_pattern_ready),.pattern_gray(c9_pattern_gray),
.mem_data({c2_video_max_ar_wait,c2_video_max_aw_wait,c2_video_empty_scans,c2_video_repeated,c2_video_read_errors,c2_video_write_errors,c2_video_dropped,c2_video_published}),
.video_data({c9_source_flags,c9_pattern_completed,c2_a_source_faults,c2_a_rejected,c2_a_completed,c2_video_overflow_frames,c2_capture_format_errors,c2_capture_source_frames}),
.display_data({29'b0,c2_display_failed,c2_display_available,c2_display_busy,c2_video_missed_scans,c2_video_underflows,c2_video_completed_scans,c2_display_timestamp_ms,c2_display_frame_id}),
.camera_data(c9_camera_data),.phy_data(c9_phy_data));
'''
 assert core.endswith('endmodule\n');core=core[:-len('endmodule\n')]+block+'endmodule\n';(P/'physical_soc_core.v').write_text(core,encoding='utf-8',newline='\n')
 top=(P/'soc_physical_top.sv').read_text()
 block='''wire c9_run,c9_mode,c9_pattern_valid,c9_pattern_ready;wire [7:0] c9_pattern_gray;
wire pat_vs,pat_de,pat_busy,pat_ready;wire [7:0] pat_gray;wire [31:0] pat_completed;
(* async_reg="true" *) reg [3:0] run_sync;(* async_reg="true" *) reg [1:0] mode_sync;
always @(posedge pixel1_clk or negedge camera_reset_n)
 if(!camera_reset_n)begin run_sync<=0;mode_sync<=0;end
 else begin run_sync<={run_sync[2:0],c9_run};mode_sync<={mode_sync[0],c9_mode};end
c9_pattern_source test_source(.clk(pixel1_clk),.arst_n(camera_reset_n),
.command_valid(c9_pattern_valid && run_sync[3] && mode_sync[1]),.command_ready(pat_ready),.command_gray(c9_pattern_gray),
.vs(pat_vs),.de(pat_de),.gray(pat_gray),.completed(pat_completed),.busy(pat_busy));
assign c9_pattern_ready=pat_ready && run_sync[3] && mode_sync[1];
wire source_vs=run_sync[3] && (mode_sync[1]?pat_vs:(pixel_vs && !fault2));
wire source_de=run_sync[3] && (mode_sync[1]?pat_de:(pixel_de && !fault2));
wire [7:0] source_gray=mode_sync[1]?pat_gray:pixel_gray;
'''
 needle='physical_soc_core soc(';assert top.count(needle)==1;top=top.replace(needle,block+needle,1)
 for old,new in [('.c2_map_enable(live_arm)',".c2_map_enable(1'b1)"),('.c3_io_enable(live_arm)',".c3_io_enable(1'b0)"),('.c2_pixel_vs(pixel_vs && !fault2)','.c2_pixel_vs(source_vs)'),('.c2_pixel_de(pixel_de && !fault2)','.c2_pixel_de(source_de)'),('.c2_pixel_gray(pixel_gray)','.c2_pixel_gray(source_gray)')]:
  assert top.count(old)==1,old;top=top.replace(old,new,1)
 ports='''.c9_camera_clk(CLK_5M),.c9_phy_clk(i_mipi_rx_pclk),
.c9_camera_data({31'b0,camera_registers_valid_5m,camera_registers_5m}),.c9_phy_data({31'b0,camera_fault,mipi_debug_out}),
.c9_pattern_completed(pat_completed),.c9_source_flags({28'b0,run_sync[3],mode_sync[1],pat_busy,fault2}),
.c9_source_run(c9_run),.c9_pattern_mode(c9_mode),.c9_pattern_valid(c9_pattern_valid),.c9_pattern_ready(c9_pattern_ready),.c9_pattern_gray(c9_pattern_gray),
'''
 top=top.replace('physical_soc_core soc(\n','physical_soc_core soc(\n'+ports,1);(P/'soc_physical_top.sv').write_text(top,encoding='utf-8',newline='\n')
 xml=P/'soc_physical.xml';tree=E.parse(xml);ns='http://www.efinixinc.com/enf_proj';E.register_namespace('efx',ns);q=lambda n:'{'+ns+'}'+n
 synthesis=tree.getroot().find(q('synthesis'))
 mode=next(e for e in synthesis if e.get('name')=='mode');mode.set('value','cong')
 packing=next(e for e in synthesis if e.get('name')=='pack-luts-to-comb4');packing.set('value','1')
 pnr=tree.getroot().find(q('place_and_route'))
 effort=next(e for e in pnr if e.get('name')=='optimization_level');effort.set('value','CONGESTION_2')
 d=tree.getroot().find(q('design_info'));extra_sources=sorted((ROOT/'team_work/03_ai_soc/c9_live/rtl').glob('*.sv'))
 insert_at=max(i for i,e in enumerate(d) if e.tag==q('design_file'))+1
 for src in extra_sources:
  d.insert(insert_at,E.Element(q('design_file'),name=src.as_posix(),version='default',library='default'));insert_at+=1
 E.indent(tree,space='    ');tree.write(xml,encoding='utf-8',xml_declaration=True)
 mf=json.loads((P/'PHYSICAL_MANIFEST.json').read_text());mf['source_sha256']={str(Path(k).as_posix()).replace('projects/07_soc_physical','projects/09_c7_live_acceptance'):v for k,v in mf['source_sha256'].items()}
 for src in extra_sources:mf['source_sha256'][src.relative_to(ROOT).as_posix()]=sha(src)
 mf['source_sha256']={k:sha(ROOT/k) for k in mf['source_sha256']};(P/'PHYSICAL_MANIFEST.json').write_text(json.dumps(mf,indent=2)+'\n',encoding='utf-8')
 manifest=dict(kind='C7 isolated live acceptance variant',parent_image_sha256=prior['artifacts']['soc_physical.bit']['sha256'],parent_manifest_sha256=prior['source_manifest_sha256'],
  source_sha256=mf['source_sha256'],generator_sha256=sha(Path(__file__)),derived=derived,
  map='fixed ON from common reset; CPU must verify reserved DDR map before starting sources',source_run='default OFF; one irreversible source commit until common reset',c3_io_enabled=False,
  snapshots='one 64-bit pair per native domain, held until APB acknowledgement; pairs and groups are not simultaneous in wall time',hardware_test_pattern_is_real_camera=False,
  c3_sensor_peripheral_present=False,diagnostic_counter_bits=32,synthesis_mode='cong',comb4_packing=1,pnr_optimization='CONGESTION_2',
  scope='Video/CPU/cache diagnostic only; excludes sensor I2C/GPIO backend and cannot establish full C7 acceptance')
 (P/'LIVE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 print('Prepared isolated C7 live acceptance variant; qualified C7 and C24 unchanged.')
if __name__=='__main__':main()
