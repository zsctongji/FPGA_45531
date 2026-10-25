"""Generate the C2 vendor-interface integration test from the existing full-frame test.
The DDR and vendor interconnect used here are behavioural stand-ins, not encrypted IP.
"""
from pathlib import Path
import re
import json
import hashlib
import shutil
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/06_soc_c2'
SP=[["awvalid","in",1],["awready","out",1],["awaddr","in",32],["awlen","in",8],["wvalid","in",1],["wready","out",1],["wdata","in",128],["wstrb","in",16],["wlast","in",1],["bvalid","out",1],["bready","in",1],["bresp","out",2],["arvalid","in",1],["arready","out",1],["araddr","in",32],["arlen","in",8],["rvalid","out",1],["rready","in",1],["rdata","out",128],["rlast","out",1],["rresp","out",2]]
MP=[["awvalid","out",1],["awready","in",1],["awaddr","out",32],["awlen","out",8],["awsize","out",3],["awburst","out",2],["wvalid","out",1],["wready","in",1],["wdata","out",128],["wstrb","out",16],["wlast","out",1],["bvalid","in",1],["bready","out",1],["bresp","in",2],["arvalid","out",1],["arready","in",1],["araddr","out",32],["arlen","out",8],["arsize","out",3],["arburst","out",2],["rvalid","in",1],["rready","out",1],["rdata","in",128],["rlast","in",1],["rresp","in",2]]
def generate_test():
    s=(P/'sim/tb_c2_boundary.sv').read_text(encoding='utf-8-sig')
    s=s.replace('module tb_c2_boundary #','module tb_c2_vendor #')
    s=s.replace('localparam N=3;', 'localparam N=3;\nreg pclk=0;always #11 pclk=~pclk;')
    a=s.index('c2_system_boundary dut(');b=s.index('c2_ddr_model memory_model(',a)
    code='''reg [15:0] paddr=0;reg psel=0,penable=0,pwrite=0;
reg [31:0] pwdata=0;wire [31:0] prdata;wire pready,pslverror,irq;
wire core_protocol_error,cpu_adapter_error,cpu_rejected;
wire [7:0] cpu_bid,cpu_rid;
'''
    code+='\n'.join(f'wire [{3*w-1}:0] u_{n};' for n,d,w in SP)+'\n'
    code+='c2_vendor_attachment #(.SHARED_BASE(0),.VIDEO_BASE(32\'h20000),.VIDEO_BYTES(32\'h10000)) dut(\n'
    code+='''.arst_n(rst_n),.mem_clk(clk),.video_clk(vclk),.pclk(pclk),.map_enable(1'b1),
.external_protocol_error(cpu_adapter_error || cpu_rejected),
.v_source_valid(1'b0),.v_source_ready(),.v_source_error(1'b0),.v_source_frame_id(32'b0),.v_source_fnv(32'b0),
.paddr(paddr),.psel(psel),.penable(penable),.pwrite(pwrite),.pwdata(pwdata),
.pready(pready),.prdata(prdata),.pslverror(pslverror),.irq(irq),
.v_frame_valid(req_valid),.v_frame_ready(req_ready),.v_descriptor(req_payload[511:0]),
.v_grant_valid(grant_valid),.v_grant_ready(grant_ready),.v_grant_frame_id(grant_frame_id),
.v_word_valid(image_valid),.v_word_ready(image_ready),.v_word_data(image_words),
.v_event_valid(delivered_valid),.v_event_ready(event_ready),
.v_event_status(delivered[547:545]),.v_event_slot(delivered[544]),
.v_event_generation(delivered[543:512]),.v_event_descriptor(delivered[511:0]),
.video_awid(4'he),.video_arid(4'h7),.video_bid(),.video_rid(),
.video_awsize(3'd4),.video_arsize(3'd4),
.video_awburst(2'b01),.video_arburst(2'b01),.video_awlock(1'b0),.video_arlock(1'b0),
'''
    code+=',\n'.join(f'.video_{n}(s_{n}[{2*w}+:{w}])' for n,d,w in SP)+',\n'
    names={n:w for n,d,w in SP}
    code+=',\n'.join(f'.m_{n}(u_{n}[{w}+:{w}])' if n in names else f'.m_{n}()' for n,d,w in MP)+',\n.protocol_error(core_protocol_error));\n'
    code+='''c2_axi_to_vendor #(.ALLOW_NARROW(1),.WINDOW_BYTES(32'h40000)) cpu_adapter(
.clk(clk),.rst_n(rst_n),.enable(1'b1),
.s_awid(8'hc7),.s_arid(8'hd9),.s_bid(cpu_bid),.s_rid(cpu_rid),
.s_awsize(3'd4),.s_arsize(3'd4),.s_awburst(2'b01),.s_arburst(2'b01),.s_awlock(1'b0),.s_arlock(1'b0),
'''
    code+=',\n'.join(f'.s_{n}(s_{n}[0+:{w}])' for n,d,w in SP)+',\n'
    code+=',\n'.join(f'.m_{n}(u_{n}[0+:{w}])' for n,d,w in SP)+',\n.rejected(cpu_rejected),.protocol_error(cpu_adapter_error));\n'
    code+='\n'.join((f'assign u_{n}[{2*w}+:{w}]=s_{n}[{w}+:{w}];' if d=='in' else
                      f'assign s_{n}[{w}+:{w}]=u_{n}[{2*w}+:{w}];') for n,d,w in SP)+'\n'
    code+='c2_axi_arbiter #(.N(3)) vendor_interface_model(.clk(clk),.rst_n(rst_n),\n'
    code+=',\n'.join(f'.s_{n}(u_{n})' for n,d,w in SP)+',\n'
    code+=',\n'.join(f'.m_{n}(m_{n})' for n,d,w in MP)+',\n.protocol_error(protocol_error));\n'
    code+='''assign image_start_valid=dut.core.image_start_valid;assign image_start_ready=dut.core.image_start_ready;
assign image_done_valid=dut.core.image_done_valid;assign image_done_ready=dut.core.image_done_ready;
assign image_error=dut.core.image_error;assign frame_valid=dut.core.frame_valid;assign frame_ready=dut.core.frame_ready;
assign states=dut.core.slot_states;assign grant_ready=!active;
always @(posedge clk) if(rst_n) begin
 if(s_bvalid[0] && cpu_bid!==8'hc7) $fatal(1,"CPU BID lost");
 if(s_rvalid[0] && cpu_rid!==8'hd9) $fatal(1,"CPU RID lost");
end
'''
    s=s[:a]+code+s[b:]
    # The earlier full-frame monitor now observes the encapsulated core.
    s=s.replace('dut.hub.','dut.core.hub.').replace('dut.publisher.','dut.core.publisher.')
    a=s.index('task control(');b=s.index('task read_image',a)
    control='''reg [31:0] apb_value;
task apb(input bit wr,input [15:0] address,input [31:0] data);
 begin
  @(negedge pclk);paddr=address;pwdata=data;pwrite=wr;psel=1;penable=0;
  @(negedge pclk);penable=1;
  do @(posedge pclk);while(!pready);
  if(pslverror) $fatal(1,"Unexpected integration APB error");
  apb_value=prdata;
  @(negedge pclk);psel=0;penable=0;pwrite=0;
 end
endtask
task control(input [2:0] op,input bit id,input [31:0] gen,input [1:0] expected);
 begin
  // Unsupported opcode is now rejected by APB before reaching the owner.
  if(op!=0) begin
   apb(1,16'h10,gen);apb(1,16'h0c,{23'b0,id,5'b0,op});
   apb(0,8,0);while(apb_value!=2) apb(0,8,0);
   apb(0,16'h18,0);
   if(apb_value[1:0]!==expected || apb_value[8]!==id) $fatal(1,"APB control status/slot");
   if(op==5) begin
    apb(0,16'h1c,0);if(apb_value!==gen) $fatal(1,"APB QUERY generation");
    apb(0,16'h4c,0);if(apb_value!=={31'b0,id}) $fatal(1,"APB descriptor slot");
   end
   apb(1,16'h14,1);ctrl_calls=ctrl_calls+1;
  end
 end
endtask
'''
    s=s[:a]+control+s[b:]
    s=s.replace("write_burst(2,32'h20000+t2*256", "write_burst(2,t2*256")
    s=s.replace("read_burst(2,32'h20000+t2*256", "read_burst(2,t2*256")
    s=s.replace('if(protocol_error) $fatal', 'if(core_protocol_error || cpu_adapter_error || cpu_rejected) $fatal(1,"Adapter protocol error");\n if(protocol_error) $fatal')
    s=s.replace('PASS tb_c2_boundary','PASS tb_c2_vendor').replace('async_pixel_FIFO grant error_drain','APB CPU_ID vendor_S1 video_relocation async_pixel_FIFO grant error_drain')
    (P/'sim/tb_c2_vendor.sv').write_text(s)
def generate_cache_test():
    source=ROOT/'projects/03_tinyml/ip/sapphire_soc/sapphire_soc.v'
    text=source.read_text(encoding='utf-8-sig')
    module=re.search(r'module (DataCache_[a-f0-9]+)\s*\((.*?)endmodule',text,re.S)
    assert module and "32'h0000500f" in text
    build=ROOT/'build/c2';build.mkdir(parents=True,exist_ok=True)
    (build/'vendor_datacache.v').write_text('`timescale 1ns/1ps\nmodule '+module.group(1)+' ('+module.group(2)+'endmodule\n')
    ports=re.findall(r'(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*(\w+)',module.group(2).split(');',1)[0])
    special={'io_systemClk':'clk','systemCd_logic_outputReset':'reset',
             'io_cpu_flush_valid':'flush','io_cpu_flush_ready':'ready',
             'io_mem_cmd_ready':"1'b1",'io_mem_cmd_valid':'mem_valid'}
    connections=[]
    for direction,width,name in ports:
        value=special.get(name)
        if value is None:
            value='' if direction=='output' else ((width.split(':')[0].strip('[')+'\'b0') if width else "1'b0")
            if width and direction=='input':
                high=int(width.split(':')[0].strip('['));value=str(high+1)+"'b0"
        connections.append('.'+name+'('+value+')')
    bench='''`timescale 1ns/1ps
module tb_c2_cache;
reg clk=0,reset=1,flush=0;wire ready,mem_valid;
always #5 clk=~clk;
'''+module.group(1)+' dut(\n'+',\n'.join(connections)+''');
integer i,round,cycles;
initial begin
 repeat(5) @(negedge clk);reset=0;
 repeat(100) @(negedge clk);
 for(round=0;round<3;round=round+1) begin
  // Test fixture seeds valid tags; the unmodified vendor flusher clears them.
  for(i=0;i<32;i=i+1) begin dut.ways_0_tags[i]=23'h12345;dut.ways_1_tags[i]=23'h23457;end
  flush=1;cycles=0;
  do begin @(posedge clk);cycles=cycles+1;end while(!ready);
  @(negedge clk);flush=0;
  if(cycles<32) $fatal(1,"Whole-cache flush completed prematurely");
  for(i=0;i<32;i=i+1)
   if(dut.ways_0_tags[i][0]!==0 || dut.ways_1_tags[i][0]!==0) $fatal(1,"Vendor cache tag still valid");
  repeat(8) @(negedge clk);
 end
 $display("PASS tb_c2_cache vendor_DataCache ways=2 sets=32 rounds=3 invalidate_all_tags CPU_instruction_execution_not_simulated");
 $finish;
end
always @(posedge clk) if(!reset && mem_valid) $fatal(1,"Flush unexpectedly issued a DDR operation");
initial begin #100000;$fatal(1,"Cache flush timeout");end
endmodule
'''
    (P/'sim/tb_c2_cache.sv').write_text(bench)

def generate_overlay():
    base=ROOT/'projects/03_tinyml'
    out=P/'integration';out.mkdir(exist_ok=True)
    source=base/'src/tinyml_soc_top.v';text=source.read_text(encoding='utf-8-sig')
    original_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    # Keep the original five projects read-only. This is a separate generated top.
    text=text.replace('module tinyml_soc_top #','module c2_tinyml_soc_top #',1)
    text=text.replace('parameter                       RANK_RATIO', 'parameter integer C2_FRAME_WIDTH=1920,C2_FRAME_HEIGHT=1080,C2_STEP_X=20,C2_STEP_Y=20,\nparameter                       RANK_RATIO',1)
    for name,path in [('ddr3_controller/ddr3_parameter.vh',base/'src/ddr3_controller/ddr3_parameter.vh'),
                      ('define.v',base/'src/define.v'),('src/tinyml/defines.v',base/'src/tinyml/defines.v')]:
        text=text.replace('"'+name+'"','"'+path.as_posix()+'"',1)
    attachment=(P/'rtl/c2_vendor_attachment.sv').read_text(encoding='utf-8-sig').split(')(\n',1)[1].split('\n);',1)[0]
    ports=[]
    for direction,width,name in re.findall(r'(input|output)\s+wire\s*(\[[^]]+\])?\s*(\w+)',attachment):
        if name.startswith('video_') or name.startswith('v_'):
            ports.append((direction,width.replace('VIDEO_ID_WIDTH','4'),name))
    # The source completion pair shares one input declaration in the HDL.
    if 'v_source_frame_id' in {n for d,w,n in ports} and 'v_source_fnv' not in {n for d,w,n in ports}:
        ports.append(('input','[31:0]','v_source_fnv'))
    spi_ports=['output wire system_spi_0_io_sclk_write,system_spi_0_io_ss']
    for lane in range(4):
        spi_ports.append(f'input wire system_spi_0_io_data_{lane}_read')
        spi_ports.append(f'output wire system_spi_0_io_data_{lane}_write,system_spi_0_io_data_{lane}_writeEnable')
    sample_ports=['input wire c2_pixel_vs,c2_pixel_de',
                  'input wire [7:0] c2_pixel_gray',
                  'output wire c2_capture_config_valid,c2_capture_record_valid,c2_capture_record_complete',
                  'output wire [31:0] c2_capture_record_frame_id,c2_capture_record_timestamp_ms',
                  'output wire [15:0] c2_capture_record_width,c2_capture_record_height',
                  'output wire [31:0] c2_capture_source_frames,c2_capture_format_errors',
                  'output wire [31:0] c2_shared_video_ms',
                  'output wire c2_shared_video_valid',
                  'output wire [31:0] c2_a_completed,c2_a_rejected,c2_a_source_faults']
    display_ports=['input wire c2_display_clk,c2_display_vs,c2_display_de,c2_display_hs',
                   'output wire [23:0] c2_display_rgb',
                   'output wire c2_out_vs,c2_out_de,c2_out_hs,c2_display_busy,c2_display_available,c2_display_failed',
                   'output wire [31:0] c2_display_frame_id,c2_display_timestamp_ms',
                   'output wire [31:0] c2_video_published,c2_video_dropped,c2_video_overflow_frames',
                   'output wire [31:0] c2_video_write_errors,c2_video_read_errors,c2_video_underflows',
                   'output wire [31:0] c2_video_repeated,c2_video_empty_scans,c2_video_missed_scans,c2_video_completed_scans',
                   'output wire [31:0] c2_video_max_aw_wait,c2_video_max_ar_wait']
    declarations=['input wire c2_video_clk,c2_map_enable',*spi_ports,*sample_ports,*display_ports]
    text=text.replace('   // Clock and reset ports',',\n'.join(declarations)+',\n   // Clock and reset ports',1)
    # Match vendor beta's 8-bit DDR IDs explicitly; no implicit 8-to-4 truncation.
    text=re.sub(r'ddr3_top\s+u_ddr3_top',"ddr3_top #(.AXI_ID_WIDTH(8)) u_ddr3_top",text,count=1)
    declarations='''wire [15:0] apb_paddr;
wire [31:0] apb_pwdata,apb_prdata;
wire apb_psel,apb_penable,apb_pready,apb_pwrite,apb_pslverror;
wire c2_irq,c2_protocol_error,c2_cpu_rejected,c2_cpu_protocol_error;
wire c2_peripheral_reset;
reg [1:0] c2_mem_release;
always @(posedge io_memoryClk or posedge io_systemReset)
 if(io_systemReset) c2_mem_release<=0;else c2_mem_release<={c2_mem_release[0],1'b1};
wire userInterruptB;
assign userInterruptB=c2_irq;
'''
    text=text.replace('wire io_systemReset;',declarations+'\nwire io_systemReset;',1)
    text=text.replace('parameter FREQ = 200;','localparam FREQ = 200;',1)
    text=re.sub(r'wire\s+axi_inter_s2_(awlock|arlock);',r'wire [1:0] axi_inter_s2_\1;',text)
    text=text.replace('//    .io_peripheralReset                 (                                   ),',
                      '    .io_peripheralReset                 (c2_peripheral_reset),',1)
    for lane in (2,3):
        text=re.sub(r'(\.system_spi_0_io_data_'+str(lane)+r'_(read|write|writeEnable)\s*\()\s*(\))',
                    lambda m:m.group(1)+'system_spi_0_io_data_'+str(lane)+'_'+m.group(2)+m.group(3),text)
    text=text.replace('wire io_systemReset;',
        "assign axi_inter_m_awqos=4'b0;\nassign axi_inter_m_arqos=4'b0;\nwire io_systemReset;",1)
    text=re.sub(r'(\.io_ddrA_b_payload_resp\s*\()\s*(\))',r'\1axi_inter_s0_bresp\2',text,count=1)
    a=text.index('axi_interconnect_beta #(')
    vendor=text[a:]
    for name,d,w in SP:
        vendor=re.sub(r'\baxi_inter_s0_'+name+r'\b','c2_cpu_'+name,vendor)
    text=text[:a]+vendor
    wires='\n'.join(f'wire [{w-1}:0] c2_cpu_{n};' for n,d,w in SP)
    wires+='\n'+'\n'.join('wire '+w+' c2_'+n+';' for d,w,n in ports if n.startswith('v_'))
    wires+='\n'+'\n'.join('wire '+w+' c2_'+n+';' for d,w,n in ports if n.startswith('video_'))
    cpu='''c2_axi_to_vendor #(.ALLOW_NARROW(1),.SOURCE_BASE(32'h1000),
 .TARGET_BASE(32'h1000),.WINDOW_BYTES(32'he0000000)) c2_cpu_adapter(
.clk(io_memoryClk),.rst_n(c2_mem_release[1]),.enable(1'b1),
'''
    cpu+=',\n'.join(f'.s_{n}(axi_inter_s0_{n})' for n,d,w in SP)+',\n'
    cpu+=',\n'.join(f'.s_{n}(axi_inter_s0_{n})' for n in ['awid','arid','bid','rid','awsize','arsize','awburst','arburst','awlock','arlock'])+',\n'
    cpu+=',\n'.join(f'.m_{n}(c2_cpu_{n})' for n,d,w in SP)+',\n.rejected(c2_cpu_rejected),.protocol_error(c2_cpu_protocol_error));\n'
    block='''c2_vendor_attachment #(.REQUIRE_SOURCE_COMPLETION(1)) c2_attachment(
.arst_n(!io_systemReset),.mem_clk(io_memoryClk),.video_clk(c2_video_clk),.pclk(i_peripheralClk),.map_enable(c2_map_enable),
.external_protocol_error(c2_cpu_rejected || c2_cpu_protocol_error),
.shared_video_ms(c2_shared_video_ms),.shared_video_valid(c2_shared_video_valid),
.paddr(apb_paddr),.psel(apb_psel),.penable(apb_penable),.pwrite(apb_pwrite),.pwdata(apb_pwdata),
.pready(apb_pready),.prdata(apb_prdata),.pslverror(apb_pslverror),.irq(c2_irq),
'''+',\n'.join('.'+n+'(c2_'+n+')' for d,w,n in ports)+',\n'
    block+=',\n'.join(f'.m_{n}(axi_inter_s1_{n})' if n in {x[0] for x in SP} else f'.m_{n}()' for n,d,w in MP)
    block+=',\n.protocol_error(c2_protocol_error));\n'
    image_source='''c2_a_video_source #(.FRAME_WIDTH(C2_FRAME_WIDTH),.FRAME_HEIGHT(C2_FRAME_HEIGHT),
.STEP_X(C2_STEP_X),.STEP_Y(C2_STEP_Y)) c2_video_source(
.arst_n(!io_systemReset),.video_clk(c2_video_clk),.enable(c2_map_enable),
.pixel_vs(c2_pixel_vs),.pixel_de(c2_pixel_de),.pixel_gray(c2_pixel_gray),
.shared_now_ms(c2_shared_video_ms),.shared_time_valid(c2_shared_video_valid),
.capture_config_valid(c2_capture_config_valid),
.capture_record_valid(c2_capture_record_valid),.capture_record_complete(c2_capture_record_complete),
.capture_record_frame_id(c2_capture_record_frame_id),.capture_record_timestamp_ms(c2_capture_record_timestamp_ms),
.capture_record_width(c2_capture_record_width),.capture_record_height(c2_capture_record_height),
.capture_source_frames(c2_capture_source_frames),.capture_format_errors(c2_capture_format_errors),
'''
    source_names=['frame_valid','frame_ready','descriptor','grant_valid','grant_ready','grant_frame_id',
                  'word_valid','word_ready','word_data','source_valid','source_ready','source_error','source_frame_id','source_fnv',
                  'event_valid','event_ready','event_status','event_descriptor']
    image_source+=',\n'.join('.v_'+n+'(c2_v_'+n+')' for n in source_names)
    image_source+=''',
.completed(c2_a_completed),.rejected(c2_a_rejected),.source_faults(c2_a_source_faults),
.source_commits(),.source_drops(),.source_malformed(),.last_frame_id(),.last_sum32(),.last_fnv(),.last_status());
'''
    # Declarations precede instances so implicit-net warnings cannot hide widths.
    text=text.replace('axi_interconnect_beta #(',wires+'\naxi_interconnect_beta #(',1)
    video_pipeline='''c2_video_pipeline #(.WIDTH(C2_FRAME_WIDTH),.HEIGHT(C2_FRAME_HEIGHT)) c2_full_video(
.arst_n(!io_systemReset),.mem_clk(io_memoryClk),.video_clk(c2_video_clk),.display_clk(c2_display_clk),
.enable(c2_map_enable),.time_valid(c2_shared_video_valid && c2_capture_config_valid),
.pixel_vs(c2_pixel_vs),.pixel_de(c2_pixel_de),.pixel_gray(c2_pixel_gray),
.now_ms(c2_shared_video_ms),.source_frames(c2_capture_source_frames),
.record_valid(c2_capture_record_valid),.record_complete(c2_capture_record_complete),
.record_id(c2_capture_record_frame_id),.record_ms(c2_capture_record_timestamp_ms),
.display_vs(c2_display_vs),.display_de(c2_display_de),.display_hs(c2_display_hs),
.display_rgb(c2_display_rgb),.out_vs(c2_out_vs),.out_de(c2_out_de),.out_hs(c2_out_hs),
.display_busy(c2_display_busy),.display_available(c2_display_available),.display_failed(c2_display_failed),
.display_frame_id(c2_display_frame_id),.display_timestamp_ms(c2_display_timestamp_ms),
'''
    stats=['published','dropped','overflow_frames','write_errors','read_errors','repeated','empty_scans',
           'underflows','missed_scans','completed_scans','max_aw_wait','max_ar_wait']
    video_pipeline+=',\n'.join('.'+n+'(c2_video_'+n+')' for n in stats)+',\n'
    video_pipeline+=',\n'.join('.'+n+'(c2_video_'+n+')' for n,d,w in SP)+');\n'
    video_pipeline+="""assign c2_video_awid=4'he;assign c2_video_arid=4'h7;
assign c2_video_awsize=3'd4;assign c2_video_arsize=3'd4;
assign c2_video_awburst=2'b01;assign c2_video_arburst=2'b01;
assign c2_video_awlock=1'b0;assign c2_video_arlock=1'b0;
"""
    text=text.rsplit('endmodule',1)[0]+cpu+block+image_source+video_pipeline+'endmodule\n'
    (out/'c2_tinyml_soc_top.v').write_text(text)
    ns='http://www.efinixinc.com/enf_proj';ET.register_namespace('efx',ns)
    ET.register_namespace('xsi','http://www.w3.org/2001/XMLSchema-instance')
    n=lambda x:'{'+ns+'}'+x
    tree=ET.parse(base/'Ti60F225_tinyml_helloworld.xml');project=tree.getroot()
    project.set('name','c2_native');project.set('description','Map-only SoC with GRAY8 triple framebuffer and raster scanout; physical pins/timing absent')
    design=project.find(n('design_info'));design.find(n('top_module')).set('name','c2_tinyml_soc_top')
    architecture=design.find(n('top_vhdl_arch'))
    if architecture is not None:design.remove(architecture)
    sources=[]
    for item in list(design.findall(n('design_file'))):
        design.remove(item);name=item.get('name')
        if name=='src/tinyml_soc_top.v':sources.append(out/'c2_tinyml_soc_top.v')
        elif name=='src/source.f':
            sources.extend(base/'src'/line.strip() for line in (base/name).read_text(encoding='utf-8-sig').splitlines() if line.strip())
        else:sources.append(base/name)
    sources.append(base/'ip/sapphire_soc/sapphire_soc.v');sources.extend(sorted((P/'rtl').glob('*.sv')))
    sources.extend(sorted((P/'a_side').glob('*.v')))
    for path in dict.fromkeys(sources):
        assert path.is_file(),path
        ET.SubElement(design,n('design_file'),name=path.as_posix(),version='default',library='default')
    if architecture is not None:design.append(architecture)
    project.remove(project.find(n('ip_info')))
    for constraint in list(project.find(n('constraint_info'))):project.find(n('constraint_info')).remove(constraint)
    ET.SubElement(project.find(n('constraint_info')),n('inter_file'),name='')
    for setting in project.find(n('synthesis')):
        if setting.get('name')=='include':setting.set('value',(base/'ip/sapphire_soc').as_posix())
    ET.indent(tree,space='    ');tree.write(out/'c2_native.xml',encoding='utf-8',xml_declaration=True)
    for file in (base/'ip/sapphire_soc').glob('*.bin'):shutil.copyfile(file,out/file.name)
    manifest={'scope':'native SoC/DDR map-only with pinned A capture, GRAY8 triple framebuffer and raster scanout; physical MIPI/HDMI constraints absent',
              'video_input_contract':'GRAY8_1PPC_VS_HIGH_DE_v1',
              'timestamp_latch':'first source DE pixel; preserved through grid EOF and DDR descriptor',
              'capture_default':{'width':1920,'height':1080,'step_x':20,'step_y':20},
              'framebuffer':{'format':'GRAY8','byte_order':'leftmost pixel in lowest byte','stride':1920,
                             'frame_bytes':2073600,'bank_pitch':2076672,'banks':3,
                             'relative_bank_bases':[0,2076672,4153344],
                             'candidate_physical_base':'0x08010000','physical_map_verified':False,
                             'publish_fence':'complete A source verdict and all AXI BRESP OKAY',
                             'selection':'oldest READY at display VS; otherwise repeat DISPLAY; drop new source if no FREE'},
              'baseline_top_sha256':original_sha,'baseline_modified':False,'candidate_map_requires_external_enable':True,
              'ddr_instances':len(re.findall(r'ddr3_top\s*#',text)),
              'sources':{str(path.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}}
    assert manifest['ddr_instances']==1
    (out/'INTEGRATION_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':
    generate_test()
    generate_cache_test()
    generate_overlay()
    print('Prepared vendor-interface test, real cache-flush test and separate native SoC/DDR overlay.')

