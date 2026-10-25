`timescale 1ns/1ps
module tb_c2_framebuffer #(parameter MEM_HALF=5,VIDEO_HALF=7,FRAME_WIDTH=384,FRAME_HEIGHT=216,STEP_X=4,STEP_Y=4,EXTENDED=1);
localparam N=3;
localparam STRIDE=((FRAME_WIDTH+15)/16)*16,PITCH=((STRIDE*FRAME_HEIGHT+4095)/4096)*4096;
reg dclk=0;always #13 dclk=~dclk;
reg display_vs=0,display_de=0,pause_ddr=0;wire [23:0] out_rgb;wire out_de;
wire raw_awready,raw_arready;
wire fb_busy,fb_available,fb_failed;
wire [31:0] fb_display_id,fb_display_ms,fb_published,fb_dropped,fb_overflow,fb_write_errors,fb_read_errors;
wire [31:0] fb_repeated,fb_empty,fb_underflows,fb_missed,fb_completed,fb_max_aw,fb_max_ar;

reg pclk=0;always #11 pclk=~pclk;
reg clk=0,vclk=0,rst_n=1,inject_b_error=0,inject_r_error=0;
always #(MEM_HALF) clk=~clk;always #(VIDEO_HALF) vclk=~vclk;
wire [N*1-1:0] s_awvalid;
reg [1:0] drive_awvalid=0;
assign s_awvalid[0+:2]=drive_awvalid;
wire [N*1-1:0] s_awready;
wire [N*32-1:0] s_awaddr;
reg [63:0] drive_awaddr=0;
assign s_awaddr[0+:64]=drive_awaddr;
wire [N*8-1:0] s_awlen;
reg [15:0] drive_awlen=0;
assign s_awlen[0+:16]=drive_awlen;
wire [N*1-1:0] s_wvalid;
reg [1:0] drive_wvalid=0;
assign s_wvalid[0+:2]=drive_wvalid;
wire [N*1-1:0] s_wready;
wire [N*128-1:0] s_wdata;
reg [255:0] drive_wdata=0;
assign s_wdata[0+:256]=drive_wdata;
wire [N*16-1:0] s_wstrb;
reg [31:0] drive_wstrb=0;
assign s_wstrb[0+:32]=drive_wstrb;
wire [N*1-1:0] s_wlast;
reg [1:0] drive_wlast=0;
assign s_wlast[0+:2]=drive_wlast;
wire [N*1-1:0] s_bvalid;
wire [N*1-1:0] s_bready;
reg [1:0] drive_bready=0;
assign s_bready[0+:2]=drive_bready;
wire [N*2-1:0] s_bresp;
wire [N*1-1:0] s_arvalid;
reg [1:0] drive_arvalid=0;
assign s_arvalid[0+:2]=drive_arvalid;
wire [N*1-1:0] s_arready;
wire [N*32-1:0] s_araddr;
reg [63:0] drive_araddr=0;
assign s_araddr[0+:64]=drive_araddr;
wire [N*8-1:0] s_arlen;
reg [15:0] drive_arlen=0;
assign s_arlen[0+:16]=drive_arlen;
wire [N*1-1:0] s_rvalid;
wire [N*1-1:0] s_rready;
reg [1:0] drive_rready=0;
assign s_rready[0+:2]=drive_rready;
wire [N*128-1:0] s_rdata;
wire [N*1-1:0] s_rlast;
wire [N*2-1:0] s_rresp;
wire [0:0] m_awvalid;
wire [0:0] m_awready;
wire [31:0] m_awaddr;
wire [7:0] m_awlen;
wire [2:0] m_awsize;
wire [1:0] m_awburst;
wire [0:0] m_wvalid;
wire [0:0] m_wready;
wire [127:0] m_wdata;
wire [15:0] m_wstrb;
wire [0:0] m_wlast;
wire [0:0] m_bvalid;
wire [0:0] m_bready;
wire [1:0] m_bresp;
wire [0:0] m_arvalid;
wire [0:0] m_arready;
wire [31:0] m_araddr;
wire [7:0] m_arlen;
wire [2:0] m_arsize;
wire [1:0] m_arburst;
wire [0:0] m_rvalid;
wire [0:0] m_rready;
wire [127:0] m_rdata;
wire [0:0] m_rlast;
wire [1:0] m_rresp;
wire protocol_error;
wire [31:0] completed_writes,completed_reads;
wire req_valid;reg event_ready=0;
wire [543:0] req_payload;assign req_payload[543:512]=0;
wire req_ready,frame_valid,frame_ready;
wire [543:0] frame_payload;
wire result_valid,result_ready,result_slot;
wire [2:0] result_status;
wire [31:0] result_generation;
wire [511:0] result_descriptor;
wire delivered_valid;
wire [547:0] delivered;
wire image_start_valid,image_start_ready,image_ready,image_done_valid,image_done_ready,image_error;
wire [31:0] image_address,image_checksum;
wire image_valid;
wire [127:0] image_words;
reg ctl_valid=0,ctl_rsp_ready=0,ctl_slot=0;
reg [2:0] ctl_cmd=0;
reg [31:0] ctl_generation=0;
wire ctl_ready,ctl_rsp_valid;
wire [1:0] ctl_status;
wire [511:0] ctl_descriptor;
wire [3:0] states;
wire [31:0] dropped;
wire ctl_rsp_slot;wire [31:0] ctl_rsp_generation;
wire grant_valid,grant_ready;wire [31:0] grant_frame_id;
reg [15:0] paddr=0;reg psel=0,penable=0,pwrite=0;
reg [31:0] pwdata=0;wire [31:0] prdata;wire pready,pslverror,irq;
wire core_protocol_error,cpu_adapter_error,cpu_rejected;
wire [7:0] cpu_bid,cpu_rid;
wire [2:0] u_awvalid;
wire [2:0] u_awready;
wire [95:0] u_awaddr;
wire [23:0] u_awlen;
wire [2:0] u_wvalid;
wire [2:0] u_wready;
wire [383:0] u_wdata;
wire [47:0] u_wstrb;
wire [2:0] u_wlast;
wire [2:0] u_bvalid;
wire [2:0] u_bready;
wire [5:0] u_bresp;
wire [2:0] u_arvalid;
wire [2:0] u_arready;
wire [95:0] u_araddr;
wire [23:0] u_arlen;
wire [2:0] u_rvalid;
wire [2:0] u_rready;
wire [383:0] u_rdata;
wire [2:0] u_rlast;
wire [5:0] u_rresp;
reg pixel_vs=0,pixel_de=0;reg [7:0] pixel_gray=0;
wire [31:0] shared_ms;wire sample_time_valid;reg [31:0] expected_stamp[0:31];
wire source_valid,core_source_ready,source_error;reg verdict_allow=1;
wire [31:0] source_frame_id,source_fnv;
wire core_event_valid,core_event_ready;wire [547:0] core_event;
wire [31:0] a_completed,a_rejected,a_faults,a_commits,a_drops,a_malformed;
reg [547:0] event_queue[0:63];integer event_write=0,event_read=0;
assign delivered_valid=event_write>event_read;assign delivered=event_queue[event_read];
always @(posedge vclk or negedge rst_n) begin
 if(!rst_n) begin event_write=0;event_read=0;end
 else begin
  if(core_event_valid && core_event_ready) begin event_queue[event_write]=core_event;event_write=event_write+1;end
  if(delivered_valid && event_ready) event_read=event_read+1;
 end
end
wire capture_config_valid,capture_record_valid,capture_record_complete;
wire [31:0] capture_record_frame_id,capture_record_timestamp_ms,capture_source_frames,capture_format_errors;
wire [15:0] capture_record_width,capture_record_height;
c2_a_video_source #(.FRAME_WIDTH(FRAME_WIDTH),.FRAME_HEIGHT(FRAME_HEIGHT),.STEP_X(STEP_X),.STEP_Y(STEP_Y)) a_source(.arst_n(rst_n),.video_clk(vclk),.enable(1'b1),
.pixel_vs(pixel_vs),.pixel_de(pixel_de),.pixel_gray(pixel_gray),
.shared_now_ms(shared_ms),.shared_time_valid(sample_time_valid),
.capture_config_valid(capture_config_valid),.capture_record_valid(capture_record_valid),.capture_record_complete(capture_record_complete),
.capture_record_frame_id(capture_record_frame_id),.capture_record_timestamp_ms(capture_record_timestamp_ms),
.capture_record_width(capture_record_width),.capture_record_height(capture_record_height),
.capture_source_frames(capture_source_frames),.capture_format_errors(capture_format_errors),
.v_frame_valid(req_valid),.v_frame_ready(req_ready),.v_descriptor(req_payload[511:0]),
.v_grant_valid(grant_valid),.v_grant_ready(grant_ready),.v_grant_frame_id(grant_frame_id),
.v_word_valid(image_valid),.v_word_ready(image_ready),.v_word_data(image_words),
.v_source_valid(source_valid),.v_source_ready(core_source_ready && verdict_allow),.v_source_error(source_error),
.v_source_frame_id(source_frame_id),.v_source_fnv(source_fnv),
.v_event_valid(core_event_valid),.v_event_ready(core_event_ready),.v_event_status(core_event[547:545]),.v_event_descriptor(core_event[511:0]),
.completed(a_completed),.rejected(a_rejected),.source_faults(a_faults),.source_commits(a_commits),.source_drops(a_drops),
.source_malformed(a_malformed),.last_frame_id(),.last_sum32(),.last_fnv(),.last_status());
c2_vendor_attachment #(.TIME_CLOCK_HZ(10000000),.TIME_INITIAL_MS(32'hfffffffc),.REQUIRE_SOURCE_COMPLETION(1),.SHARED_BASE(0),.VIDEO_BASE(32'h20000),.VIDEO_BYTES(32'h1000000)) dut(
.arst_n(rst_n),.mem_clk(clk),.video_clk(vclk),.pclk(pclk),.map_enable(1'b1),
.external_protocol_error(cpu_adapter_error || cpu_rejected),.shared_video_ms(shared_ms),.shared_video_valid(sample_time_valid),

.v_source_valid(source_valid && verdict_allow),.v_source_ready(core_source_ready),.v_source_error(source_error),
.v_source_frame_id(source_frame_id),.v_source_fnv(source_fnv),
.paddr(paddr),.psel(psel),.penable(penable),.pwrite(pwrite),.pwdata(pwdata),
.pready(pready),.prdata(prdata),.pslverror(pslverror),.irq(irq),
.v_frame_valid(req_valid),.v_frame_ready(req_ready),.v_descriptor(req_payload[511:0]),
.v_grant_valid(grant_valid),.v_grant_ready(grant_ready),.v_grant_frame_id(grant_frame_id),
.v_word_valid(image_valid),.v_word_ready(image_ready),.v_word_data(image_words),
.v_event_valid(core_event_valid),.v_event_ready(core_event_ready),
.v_event_status(core_event[547:545]),.v_event_slot(core_event[544]),
.v_event_generation(core_event[543:512]),.v_event_descriptor(core_event[511:0]),
.video_awid(4'he),.video_arid(4'h7),.video_bid(),.video_rid(),
.video_awsize(3'd4),.video_arsize(3'd4),
.video_awburst(2'b01),.video_arburst(2'b01),.video_awlock(1'b0),.video_arlock(1'b0),
.video_awvalid(s_awvalid[2+:1]),
.video_awready(s_awready[2+:1]),
.video_awaddr(s_awaddr[64+:32]),
.video_awlen(s_awlen[16+:8]),
.video_wvalid(s_wvalid[2+:1]),
.video_wready(s_wready[2+:1]),
.video_wdata(s_wdata[256+:128]),
.video_wstrb(s_wstrb[32+:16]),
.video_wlast(s_wlast[2+:1]),
.video_bvalid(s_bvalid[2+:1]),
.video_bready(s_bready[2+:1]),
.video_bresp(s_bresp[4+:2]),
.video_arvalid(s_arvalid[2+:1]),
.video_arready(s_arready[2+:1]),
.video_araddr(s_araddr[64+:32]),
.video_arlen(s_arlen[16+:8]),
.video_rvalid(s_rvalid[2+:1]),
.video_rready(s_rready[2+:1]),
.video_rdata(s_rdata[256+:128]),
.video_rlast(s_rlast[2+:1]),
.video_rresp(s_rresp[4+:2]),
.m_awvalid(u_awvalid[1+:1]),
.m_awready(u_awready[1+:1]),
.m_awaddr(u_awaddr[32+:32]),
.m_awlen(u_awlen[8+:8]),
.m_awsize(),
.m_awburst(),
.m_wvalid(u_wvalid[1+:1]),
.m_wready(u_wready[1+:1]),
.m_wdata(u_wdata[128+:128]),
.m_wstrb(u_wstrb[16+:16]),
.m_wlast(u_wlast[1+:1]),
.m_bvalid(u_bvalid[1+:1]),
.m_bready(u_bready[1+:1]),
.m_bresp(u_bresp[2+:2]),
.m_arvalid(u_arvalid[1+:1]),
.m_arready(u_arready[1+:1]),
.m_araddr(u_araddr[32+:32]),
.m_arlen(u_arlen[8+:8]),
.m_arsize(),
.m_arburst(),
.m_rvalid(u_rvalid[1+:1]),
.m_rready(u_rready[1+:1]),
.m_rdata(u_rdata[128+:128]),
.m_rlast(u_rlast[1+:1]),
.m_rresp(u_rresp[2+:2]),
.protocol_error(core_protocol_error));
c2_axi_to_vendor #(.ALLOW_NARROW(1),.WINDOW_BYTES(32'h40000)) cpu_adapter(
.clk(clk),.rst_n(rst_n),.enable(1'b1),
.s_awid(8'hc7),.s_arid(8'hd9),.s_bid(cpu_bid),.s_rid(cpu_rid),
.s_awsize(3'd4),.s_arsize(3'd4),.s_awburst(2'b01),.s_arburst(2'b01),.s_awlock(1'b0),.s_arlock(1'b0),
.s_awvalid(s_awvalid[0+:1]),
.s_awready(s_awready[0+:1]),
.s_awaddr(s_awaddr[0+:32]),
.s_awlen(s_awlen[0+:8]),
.s_wvalid(s_wvalid[0+:1]),
.s_wready(s_wready[0+:1]),
.s_wdata(s_wdata[0+:128]),
.s_wstrb(s_wstrb[0+:16]),
.s_wlast(s_wlast[0+:1]),
.s_bvalid(s_bvalid[0+:1]),
.s_bready(s_bready[0+:1]),
.s_bresp(s_bresp[0+:2]),
.s_arvalid(s_arvalid[0+:1]),
.s_arready(s_arready[0+:1]),
.s_araddr(s_araddr[0+:32]),
.s_arlen(s_arlen[0+:8]),
.s_rvalid(s_rvalid[0+:1]),
.s_rready(s_rready[0+:1]),
.s_rdata(s_rdata[0+:128]),
.s_rlast(s_rlast[0+:1]),
.s_rresp(s_rresp[0+:2]),
.m_awvalid(u_awvalid[0+:1]),
.m_awready(u_awready[0+:1]),
.m_awaddr(u_awaddr[0+:32]),
.m_awlen(u_awlen[0+:8]),
.m_wvalid(u_wvalid[0+:1]),
.m_wready(u_wready[0+:1]),
.m_wdata(u_wdata[0+:128]),
.m_wstrb(u_wstrb[0+:16]),
.m_wlast(u_wlast[0+:1]),
.m_bvalid(u_bvalid[0+:1]),
.m_bready(u_bready[0+:1]),
.m_bresp(u_bresp[0+:2]),
.m_arvalid(u_arvalid[0+:1]),
.m_arready(u_arready[0+:1]),
.m_araddr(u_araddr[0+:32]),
.m_arlen(u_arlen[0+:8]),
.m_rvalid(u_rvalid[0+:1]),
.m_rready(u_rready[0+:1]),
.m_rdata(u_rdata[0+:128]),
.m_rlast(u_rlast[0+:1]),
.m_rresp(u_rresp[0+:2]),
.rejected(cpu_rejected),.protocol_error(cpu_adapter_error));
assign u_awvalid[2+:1]=s_awvalid[1+:1];
assign s_awready[1+:1]=u_awready[2+:1];
assign u_awaddr[64+:32]=s_awaddr[32+:32];
assign u_awlen[16+:8]=s_awlen[8+:8];
assign u_wvalid[2+:1]=s_wvalid[1+:1];
assign s_wready[1+:1]=u_wready[2+:1];
assign u_wdata[256+:128]=s_wdata[128+:128];
assign u_wstrb[32+:16]=s_wstrb[16+:16];
assign u_wlast[2+:1]=s_wlast[1+:1];
assign s_bvalid[1+:1]=u_bvalid[2+:1];
assign u_bready[2+:1]=s_bready[1+:1];
assign s_bresp[2+:2]=u_bresp[4+:2];
assign u_arvalid[2+:1]=s_arvalid[1+:1];
assign s_arready[1+:1]=u_arready[2+:1];
assign u_araddr[64+:32]=s_araddr[32+:32];
assign u_arlen[16+:8]=s_arlen[8+:8];
assign s_rvalid[1+:1]=u_rvalid[2+:1];
assign u_rready[2+:1]=s_rready[1+:1];
assign s_rdata[128+:128]=u_rdata[256+:128];
assign s_rlast[1+:1]=u_rlast[2+:1];
assign s_rresp[2+:2]=u_rresp[4+:2];
c2_axi_arbiter #(.N(3)) vendor_interface_model(.clk(clk),.rst_n(rst_n),
.s_awvalid(u_awvalid),
.s_awready(u_awready),
.s_awaddr(u_awaddr),
.s_awlen(u_awlen),
.s_wvalid(u_wvalid),
.s_wready(u_wready),
.s_wdata(u_wdata),
.s_wstrb(u_wstrb),
.s_wlast(u_wlast),
.s_bvalid(u_bvalid),
.s_bready(u_bready),
.s_bresp(u_bresp),
.s_arvalid(u_arvalid),
.s_arready(u_arready),
.s_araddr(u_araddr),
.s_arlen(u_arlen),
.s_rvalid(u_rvalid),
.s_rready(u_rready),
.s_rdata(u_rdata),
.s_rlast(u_rlast),
.s_rresp(u_rresp),
.m_awvalid(m_awvalid),
.m_awready(m_awready),
.m_awaddr(m_awaddr),
.m_awlen(m_awlen),
.m_awsize(m_awsize),
.m_awburst(m_awburst),
.m_wvalid(m_wvalid),
.m_wready(m_wready),
.m_wdata(m_wdata),
.m_wstrb(m_wstrb),
.m_wlast(m_wlast),
.m_bvalid(m_bvalid),
.m_bready(m_bready),
.m_bresp(m_bresp),
.m_arvalid(m_arvalid),
.m_arready(m_arready),
.m_araddr(m_araddr),
.m_arlen(m_arlen),
.m_arsize(m_arsize),
.m_arburst(m_arburst),
.m_rvalid(m_rvalid),
.m_rready(m_rready),
.m_rdata(m_rdata),
.m_rlast(m_rlast),
.m_rresp(m_rresp),
.protocol_error(protocol_error));
assign image_start_valid=dut.core.image_start_valid;assign image_start_ready=dut.core.image_start_ready;
assign image_done_valid=dut.core.image_done_valid;assign image_done_ready=dut.core.image_done_ready;
assign image_error=dut.core.image_error;assign frame_valid=dut.core.frame_valid;assign frame_ready=dut.core.frame_ready;
assign states=dut.core.slot_states;
always @(posedge clk) if(rst_n) begin
 if(s_bvalid[0] && cpu_bid!==8'hc7) $fatal(1,"CPU BID lost");
 if(s_rvalid[0] && cpu_rid!==8'hd9) $fatal(1,"CPU RID lost");
end
c2_video_pipeline #(.WIDTH(FRAME_WIDTH),.HEIGHT(FRAME_HEIGHT)) fbpipe(
.arst_n(rst_n),.mem_clk(clk),.video_clk(vclk),.display_clk(dclk),.enable(1'b1),.time_valid(sample_time_valid),
.pixel_vs(pixel_vs),.pixel_de(pixel_de),.pixel_gray(pixel_gray),.now_ms(shared_ms),.source_frames(capture_source_frames),
.record_valid(capture_record_valid),.record_complete(capture_record_complete),.record_id(capture_record_frame_id),.record_ms(capture_record_timestamp_ms),
.display_vs(display_vs),.display_de(display_de),.display_hs(1'b0),.display_rgb(out_rgb),.out_vs(),.out_de(out_de),.out_hs(),
.display_busy(fb_busy),.display_available(fb_available),.display_failed(fb_failed),
.display_frame_id(fb_display_id),.display_timestamp_ms(fb_display_ms),
.published(fb_published),.dropped(fb_dropped),.overflow_frames(fb_overflow),.write_errors(fb_write_errors),.read_errors(fb_read_errors),
.repeated(fb_repeated),.empty_scans(fb_empty),.underflows(fb_underflows),.missed_scans(fb_missed),.completed_scans(fb_completed),.max_aw_wait(fb_max_aw),.max_ar_wait(fb_max_ar),
.awvalid(s_awvalid[2+:1]),
.awready(s_awready[2+:1]),
.awaddr(s_awaddr[64+:32]),
.awlen(s_awlen[16+:8]),
.wvalid(s_wvalid[2+:1]),
.wready(s_wready[2+:1]),
.wdata(s_wdata[256+:128]),
.wstrb(s_wstrb[32+:16]),
.wlast(s_wlast[2+:1]),
.bvalid(s_bvalid[2+:1]),
.bready(s_bready[2+:1]),
.bresp(s_bresp[4+:2]),
.arvalid(s_arvalid[2+:1]),
.arready(s_arready[2+:1]),
.araddr(s_araddr[64+:32]),
.arlen(s_arlen[16+:8]),
.rvalid(s_rvalid[2+:1]),
.rready(s_rready[2+:1]),
.rdata(s_rdata[256+:128]),
.rlast(s_rlast[2+:1]),
.rresp(s_rresp[4+:2]));
c2_ddr_model #(.WORDS((32'h20000+PITCH*3)/16+16)) memory_model(.clk(clk),.rst_n(rst_n),.inject_b_error(inject_b_error),.inject_r_error(inject_r_error),
.awvalid(m_awvalid && !pause_ddr),
.awready(raw_awready),
.awaddr(m_awaddr),
.awlen(m_awlen),
.awsize(m_awsize),
.awburst(m_awburst),
.wvalid(m_wvalid),
.wready(m_wready),
.wdata(m_wdata),
.wstrb(m_wstrb),
.wlast(m_wlast),
.bvalid(m_bvalid),
.bready(m_bready),
.bresp(m_bresp),
.arvalid(m_arvalid && !pause_ddr),
.arready(raw_arready),
.araddr(m_araddr),
.arlen(m_arlen),
.arsize(m_arsize),
.arburst(m_arburst),
.rvalid(m_rvalid),
.rready(m_rready),
.rdata(m_rdata),
.rlast(m_rlast),
.rresp(m_rresp),
.completed_writes(completed_writes),
.completed_reads(completed_reads));
assign m_awready=raw_awready && !pause_ddr;
assign m_arready=raw_arready && !pause_ddr;
integer checks=0,write_transactions=0,read_transactions=0;
function [127:0] pattern(input integer tag,input integer beat);
 integer lane;begin for(lane=0;lane<4;lane=lane+1) pattern[lane*32+:32]=tag*65536+beat*4+lane;end
endfunction
function [127:0] masked_pattern(input integer tag,input integer beat);
 reg [127:0] p;reg [15:0] mask;integer b;
 begin
   p=pattern(tag,beat);mask=16'hffff<<(beat%4);
   for(b=0;b<16;b=b+1) if(!mask[b]) p[b*8+:8]=0;
   masked_pattern=p;
 end
endfunction
task automatic write_burst(input integer p,input integer addr,input integer count,
                           input integer tag,input [1:0] response);
 integer b;
 begin
   @(negedge clk);drive_awvalid[p]=1;drive_awaddr[p*32+:32]=addr;drive_awlen[p*8+:8]=count-1;
   do @(posedge clk);while(!s_awready[p]);
   @(negedge clk);drive_awvalid[p]=0;
   for(b=0;b<count;b=b+1) begin
     repeat((b+p)%3) @(negedge clk);
     drive_wvalid[p]=1;drive_wdata[p*128+:128]=pattern(tag,b);
     drive_wstrb[p*16+:16]=16'hffff<<(b%4);drive_wlast[p]=(b==count-1);
     do @(posedge clk);while(!s_wready[p]);
     @(negedge clk);drive_wvalid[p]=0;drive_wlast[p]=0;
   end
   repeat(p+2) @(negedge clk);
   drive_bready[p]=1;
   do @(posedge clk);while(!s_bvalid[p]);
   if(s_bresp[p*2+:2]!==response) $fatal(1,"B response misrouted p=%d",p);
   checks=checks+1;write_transactions=write_transactions+1;
   @(negedge clk);drive_bready[p]=0;
 end
endtask
task automatic read_burst(input integer p,input integer addr,input integer count,
                          input integer tag,input [1:0] response);
 integer b;
 begin
   @(negedge clk);drive_arvalid[p]=1;drive_araddr[p*32+:32]=addr;drive_arlen[p*8+:8]=count-1;
   do @(posedge clk);while(!s_arready[p]);
   @(negedge clk);drive_arvalid[p]=0;
   for(b=0;b<count;b=b+1) begin
     repeat((b+2*p)%4) @(negedge clk);
     drive_rready[p]=1;
     do @(posedge clk);while(!s_rvalid[p]);
     if(s_rresp[p*2+:2]!==response || s_rlast[p]!=(b==count-1) ||
        s_rdata[p*128+:128]!==masked_pattern(tag,b))
        $fatal(1,"Read mismatch p=%d beat=%d got=%h expected=%h",p,b,s_rdata[p*128+:128],masked_pattern(tag,b));
     checks=checks+1;
     @(negedge clk);drive_rready[p]=0;
   end
   read_transactions=read_transactions+1;
 end
endtask
integer word_index=0,active_frame=0,frame_w=0,frame_b=0;
integer images_ok=0,images_error=0,t0,t1,t2,ctrl_calls=0;
reg active=0,consumed=0,fence_seen=0;
reg [31:0] random_bits=32'h613acb27;
function [7:0] pixel_value(input integer frame,input integer index);
 begin pixel_value=(index<2016 || index>=7200)?0:((index-2016)*17+frame+1);end
endfunction
function [127:0] image_pattern(input integer frame,input integer word_index);
 integer b;begin for(b=0;b<16;b=b+1) image_pattern[b*8+:8]=pixel_value(frame,word_index*16+b);end
endfunction
function [31:0] checksum(input integer frame);
 reg [31:0] value;integer n;
 begin value=32'd2166136261;
   for(n=0;n<9216;n=n+1) value=(value^pixel_value(frame,n))*32'd16777619;
   checksum=value;
 end
endfunction
always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin frame_w<=0;frame_b<=0;fence_seen<=0;end
 else begin
   if(frame_valid && frame_ready) fence_seen<=0;
   if(image_start_valid && image_start_ready) begin frame_w<=0;frame_b<=0;end
   if(dut.core.hub.f_wvalid[3] && dut.core.hub.f_wready[3]) frame_w<=frame_w+1;
   if(dut.core.hub.f_bvalid[3] && dut.core.hub.f_bready[3]) frame_b<=frame_b+1;
   if(image_done_valid && image_done_ready && !image_error) begin
     if(frame_w!=576 || frame_b!=36) $fatal(1,"Writer completion before all 576 beats/36 responses");
     fence_seen<=1;
   end
   if(dut.core.publisher.choose_internal && dut.core.publisher.manager_ready && dut.core.publisher.internal_cmd==1 && !fence_seen)
     $fatal(1,"COMMIT before final write response");
 end
end
integer source_stalls=0;
reg burst_reserved=0;
always @(posedge clk or negedge rst_n) begin
 if(!rst_n) burst_reserved<=0;
 else begin
  if(dut.core.hub.f_awvalid[3] && dut.core.hub.f_awready[3]) burst_reserved<=1;
  if(burst_reserved && !dut.core.hub.f_wvalid[3]) $fatal(1,"DDR burst reserved while waiting for A pixels/hash");
  if(dut.core.hub.f_wvalid[3] && dut.core.hub.f_wready[3] && dut.core.hub.f_wlast[3]) burst_reserved<=0;
 end
end
always @(posedge vclk) if(rst_n) begin
 if(image_valid && !image_ready) source_stalls=source_stalls+1;
 if(image_valid && !a_source.image.active) $fatal(1,"A lease released before transfer finished");
end

integer record_checks=0,bad_records=0,sof_checks=0,eof_checks=0,stamp_edges=0,time_wraps=0;
integer traffic_during_image=0;reg transferring=0;
reg [31:0] previous_ms=32'hfffffffc;
reg [31:0] grid_clock[0:31],eof_clock[0:31];
reg [31:0] last_record_id=0;reg last_record_complete=0;
always @(posedge pclk or negedge rst_n) begin
 if(!rst_n) previous_ms=32'hfffffffc;
 else begin
  if(dut.control.clock_service.cpu_ms<previous_ms &&
     (dut.control.clock_service.cpu_ms-previous_ms)<32'h80000000) time_wraps=time_wraps+1;
  previous_ms=dut.control.clock_service.cpu_ms;
 end
end
always @(posedge clk or negedge rst_n) begin
 if(!rst_n) transferring<=0;
 else begin
  if(image_start_valid && image_start_ready) transferring<=1;
  if(image_done_valid && image_done_ready) transferring<=0;
  if(transferring && ((|(s_awvalid&s_awready)) || (|(s_arvalid&s_arready))))
   traffic_during_image=traffic_during_image+1;
 end
end
always @(posedge vclk) if(rst_n && a_source.capture_rst_n) begin
 if(capture_record_valid) begin
  record_checks=record_checks+1;last_record_id=capture_record_frame_id;
  last_record_complete=capture_record_complete;
  if(capture_record_timestamp_ms!==expected_stamp[capture_record_frame_id])
   $fatal(1,"First-DE timestamp lost in source record");
  if(capture_record_complete) begin
   if(capture_record_width!=FRAME_WIDTH || capture_record_height!=FRAME_HEIGHT)
    $fatal(1,"Source geometry record mismatch");
  end else bad_records=bad_records+1;
 end
 if(a_source.sample_valid && a_source.sample_sof) begin
  sof_checks=sof_checks+1;grid_clock[a_source.sample_frame_id]=shared_ms;
  if(a_source.sample_timestamp_ms!==expected_stamp[a_source.sample_frame_id])
   $fatal(1,"Grid SOF overwrote first-DE timestamp");
  if(shared_ms!=a_source.sample_timestamp_ms) stamp_edges=stamp_edges+1;
 end
 if(a_source.sample_valid && a_source.sample_eof) begin
  eof_checks=eof_checks+1;eof_clock[a_source.sample_frame_id]=shared_ms;
  if(!capture_record_valid || !capture_record_complete ||
     capture_record_frame_id!==a_source.sample_frame_id ||
     a_source.sample_timestamp_ms!==expected_stamp[a_source.sample_frame_id])
    $fatal(1,"Delayed EOF used new VS frame metadata or an invalid source frame");
 end
end
task pixels(input integer seq,input integer mode);
 integer x,y,width,height;
 begin
  // At this edge the next clock consumes a DIFFERENT coherent time snapshot.
  // Capture must use the old first-DE time; grid SOF observes the new time.
  if(seq==0) begin
   @(negedge vclk);
   while(!(dut.control.clock_service.snap_valid &&
           dut.control.clock_service.snapshot!=shared_ms)) @(negedge vclk);
  end else @(negedge vclk);
  height=FRAME_HEIGHT+(mode==2?-1:(mode==3?1:0));
  for(y=0;y<height;y=y+1) begin
   width=FRAME_WIDTH-((mode==1 && y==0)?1:0);
   for(x=0;x<width;x=x+1) begin
    pixel_de=1;
    // Sampled coordinates produce the exact C24 self-test when source ID=0.
    // Unsampled pixels differ so a wrong sampling position cannot pass.
    if(x%STEP_X==0 && y%STEP_Y==0)
     pixel_gray=8'((y/STEP_Y*96+x/STEP_X)*17+seq+1);
    else pixel_gray=8'(x*3+y*5+seq+73);
    if(x==0 && y==0) expected_stamp[seq]=shared_ms;
    @(negedge vclk);
   end
   pixel_de=0;repeat(3) @(negedge vclk);
  end
  pixel_de=0;repeat(4) @(negedge vclk);
  if(mode==0 && rst_n && !a_source.capture.sampler.pending_last)
   $fatal(1,"Valid physical frame did not retain its final grid pixel until VS");
 end
endtask
task boundary;
 begin
  @(negedge vclk);pixel_vs=1;pixel_de=0;
  repeat(4) @(negedge vclk);pixel_vs=0;
  repeat(3) @(negedge vclk);
 end
endtask
task malformed(input integer seq,input integer mode);
 integer before_commits;
 begin
  before_commits=a_commits;pixels(seq,mode);boundary();
  repeat(100) @(negedge vclk);
  if(event_write!=event_read || a_commits!=before_commits ||
     last_record_id!=seq || last_record_complete)
   $fatal(1,"Malformed source frame reached DDR or complete record");
 end
endtask

task collect(input integer seq,input [2:0] expected,
             output reg id,output reg [31:0] gen);
 reg [547:0] saved;reg [31:0] addr;
 reg [7:0] observed;integer n,fd,meta;
 begin
   event_ready=0;
   while(!delivered_valid) @(negedge vclk);
   saved=delivered;
   repeat(7) begin @(negedge vclk);
     if(!delivered_valid || delivered!==saved) $fatal(1,"Event payload not held");
   end
   if(delivered[547:545]!==expected || delivered[63:32]!=seq)
      $fatal(1,"Image event seq=%d got_frame=%h status=%d expected=%d payload=%h",seq,delivered[63:32],delivered[547:545],expected,delivered);
   id=delivered[544];gen=delivered[543:512];
   if(expected==0) begin
     addr=delivered[159:128];
     if(seq==0) fd=$fopen("a_c2_video_frame0.gray","wb");
     for(n=0;n<9216;n=n+1) begin
       observed=memory_model.memory[(addr+n)/16][((addr+n)%16)*8+:8];
       if(seq==0) $fwrite(fd,"%c",observed);
       if(observed!==pixel_value(seq,n)) $fatal(1,"Image byte corrupted frame=%d offset=%d got=%h expected=%h",seq,n,observed,pixel_value(seq,n));
     end
     if(seq==0) begin
      $fclose(fd);meta=$fopen("a_c2_video_frame0.json","w");
      $fwrite(meta,"{\"synthetic\":true,\"source\":\"GRAY8_VS_DE_simulation\",\"source_frame_id\":0,\"width\":%0d,\"height\":%0d,\"step_x\":%0d,\"step_y\":%0d,\"timestamp_ms\":%0d,\"grid_sof_observed_ms\":%0d,\"completion_shared_ms\":%0d,\"timestamp_origin\":\"first_source_DE\",\"raw_fnv\":\"%08x\"}\n",FRAME_WIDTH,FRAME_HEIGHT,STEP_X,STEP_Y,delivered[95:64],grid_clock[0],eof_clock[0],checksum(0));
      $fclose(meta);
     end
     if(delivered[95:64]!==expected_stamp[seq]) $fatal(1,"Shared SOF timestamp lost");
     if(delivered[287:256]!==checksum(seq)) $fatal(1,"Image FNV mismatch got=%h expected=%h",delivered[287:256],checksum(seq));
     images_ok=images_ok+1;
   end else images_error=images_error+1;
   event_ready=1;@(negedge vclk);event_ready=0;
 end
endtask
reg [31:0] apb_value;
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
task read_image(input integer seq,input integer addr);
 integer burst,b,n;reg [127:0] expected;
 begin
   for(burst=0;burst<36;burst=burst+1) begin
     @(negedge clk);drive_arvalid[0]=1;drive_araddr[31:0]=addr+burst*256;drive_arlen[7:0]=15;
     do @(posedge clk);while(!s_arready[0]);
     @(negedge clk);drive_arvalid[0]=0;
     for(b=0;b<16;b=b+1) begin
       repeat(b%3) @(negedge clk);drive_rready[0]=1;
       do @(posedge clk);while(!s_rvalid[0]);
       expected=image_pattern(seq,burst*16+b);
       if(s_rdata[127:0]!==expected || s_rresp[1:0]!=0 || s_rlast[0]!=(b==15))
         $fatal(1,"CPU shared-image read mismatch");
       checks=checks+1;
       @(negedge clk);drive_rready[0]=0;
     end
   end
 end
endtask


reg bg_run=0,bg_busy0=0,bg_busy1=0;integer bg0=0,bg1=0,display_checks=0,full_checks=0;
integer simultaneous=0,overlap_ai=0,overlap_display=0;
integer peak_aw=0,peak_ar=0,cpu_aw_wait=0,cpu_ar_wait=0,ml_aw_wait=0,ml_ar_wait=0;
integer video_arb_aw_wait=0,video_arb_ar_wait=0;
integer cpu_max_wait=0,ml_max_wait=0;
reg video_write_outstanding=0;reg [31:0] last_published=0;
always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin video_write_outstanding<=0;last_published<=0;end
 else begin
  if(fbpipe.awvalid && fbpipe.awready) video_write_outstanding<=1;
  if(fbpipe.bvalid && fbpipe.bready) video_write_outstanding<=0;
  if(fb_published!=last_published &&
     (video_write_outstanding || !fbpipe.framebuffer.ended || fbpipe.framebuffer.wbad ||
      fbpipe.framebuffer.w_offset!=STRIDE*FRAME_HEIGHT/16)) $fatal(1,"READY before source/final BRESP fence");
  last_published<=fb_published;
 end
end
always @(posedge clk) if(rst_n) begin
 // Measure AFTER request serializers, at real arbitration inputs.
 video_arb_aw_wait=dut.q_awvalid&&!dut.q_awready?video_arb_aw_wait+1:0;
 video_arb_ar_wait=dut.q_arvalid&&!dut.q_arready?video_arb_ar_wait+1:0;
 if(video_arb_aw_wait>peak_aw) peak_aw=video_arb_aw_wait;
 if(video_arb_ar_wait>peak_ar) peak_ar=video_arb_ar_wait;
 cpu_aw_wait=u_awvalid[0]&&!u_awready[0]?cpu_aw_wait+1:0;
 cpu_ar_wait=u_arvalid[0]&&!u_arready[0]?cpu_ar_wait+1:0;
 ml_aw_wait=u_awvalid[2]&&!u_awready[2]?ml_aw_wait+1:0;
 ml_ar_wait=u_arvalid[2]&&!u_arready[2]?ml_ar_wait+1:0;
 if(cpu_aw_wait>cpu_max_wait) cpu_max_wait=cpu_aw_wait;
 if(cpu_ar_wait>cpu_max_wait) cpu_max_wait=cpu_ar_wait;
 if(ml_aw_wait>ml_max_wait) ml_max_wait=ml_aw_wait;
 if(ml_ar_wait>ml_max_wait) ml_max_wait=ml_ar_wait;
 if(fbpipe.awvalid && fbpipe.arvalid) simultaneous=simultaneous+1;
 if(transferring && (fbpipe.awvalid || fbpipe.arvalid)) overlap_ai=overlap_ai+1;
 if(fbpipe.framebuffer.rs!=0 && fbpipe.framebuffer.ws!=0 && bg_run) overlap_display=overlap_display+1;
 if(fbpipe.framebuffer.ws==3 && !fbpipe.wvalid) $fatal(1,"Video DDR writer reserved a burst without all data");
end
initial forever begin
 wait(bg_run);bg_busy0=1;write_burst(0,32'h10000+(bg0%16)*256,4,bg0,0);
 read_burst(0,32'h10000+(bg0%16)*256,4,bg0,0);bg0=bg0+1;bg_busy0=0;
end
initial forever begin
 wait(bg_run);bg_busy1=1;write_burst(1,32'h18000+(bg1%16)*256,4,100+bg1,0);
 read_burst(1,32'h18000+(bg1%16)*256,4,100+bg1,0);bg1=bg1+1;bg_busy1=0;
end
function [7:0] source_pixel(input integer seq,input integer x,input integer y);
 begin
  if(x%STEP_X==0 && y%STEP_Y==0) source_pixel=8'((y/STEP_Y*96+x/STEP_X)*17+seq+1);
  else source_pixel=8'(x*3+y*5+seq+73);
 end
endfunction
task check_bank(input integer seq);
 integer bank,x,y,off;reg found;reg [7:0] expected,observed;
 begin
  found=0;
  for(bank=0;bank<3;bank=bank+1) if(fbpipe.framebuffer.banks[bank]>=2 && fbpipe.framebuffer.ids[bank]==seq) begin
   found=1;
   if(fbpipe.framebuffer.stamps[bank]!==expected_stamp[seq]) $fatal(1,"Full-frame first-DE timestamp changed");
   for(y=0;y<FRAME_HEIGHT;y=y+1) for(x=0;x<STRIDE;x=x+1) begin
    off=32'h20000+bank*PITCH+y*STRIDE+x;
    observed=memory_model.memory[off/16][(off%16)*8+:8];
    expected=x<FRAME_WIDTH?source_pixel(seq,x,y):8'd0;
    if(observed!==expected) $fatal(1,"Video bank corruption seq=%0d bank=%0d x=%0d y=%0d got=%h expected=%h",seq,bank,x,y,observed,expected);
    full_checks=full_checks+1;
   end
  end
  if(!found) $fatal(1,"Published frame absent from banks seq=%0d",seq);
 end
endtask
task scan(input integer seq,input integer force_underflow);
 integer x,y,prior;reg [7:0] expected;
 begin
  prior=fb_underflows;
  @(negedge dclk);display_vs=1;display_de=0;
  repeat(4) @(negedge dclk);display_vs=0;
  if(force_underflow!=1) repeat(2000) @(negedge dclk);
  for(y=0;y<FRAME_HEIGHT;y=y+1) begin
   for(x=0;x<FRAME_WIDTH;x=x+1) begin
    display_de=1;@(posedge dclk);#1;
    if(force_underflow==0 && seq>=0) begin
     expected=source_pixel(seq,x,y);
     if(out_rgb!=={3{expected}} || !out_de || fb_display_id!=seq || fb_display_ms!==expected_stamp[seq] || fb_failed)
      $fatal(1,"Display tearing/underflow seq=%0d id=%0d x=%0d y=%0d rgb=%h exp=%h fail=%b",seq,fb_display_id,x,y,out_rgb,expected,fb_failed);
     display_checks=display_checks+1;
    end
    if(force_underflow==1 && out_rgb!==0) $fatal(1,"Starved scan shifted/stale pixels instead of black");
    @(negedge dclk);
   end
   display_de=0;repeat(10) @(negedge dclk);
  end
  display_de=0;wait(!fb_busy);repeat(30) @(negedge dclk);
  if(force_underflow==1 && fb_underflows<=prior) $fatal(1,"Starvation was not detected");
 end
endtask
task release_image(input integer seq);
 reg slot;reg [31:0] generation;
 begin collect(seq,0,slot,generation);control(3,slot,generation,0);control(4,slot,generation,0);end
endtask
reg tmp_slot;reg [31:0] tmp_generation;reg [2:0] tmp_status;integer count_before;
initial begin
 #1;rst_n=0;#53;rst_n=1;wait(a_source.capture_rst_n);repeat(12) @(negedge vclk);boundary();bg_run=1;
 // Source frame0 writes while CPU/TinyML traffic is live. No READY before A's next VS.
 pixels(0,0);
 if(fb_published!=0) $fatal(1,"Full frame published before physical source verdict");
 boundary();wait(fb_published==1);check_bank(0);release_image(0);$display("CHECK framebuffer frame0 + AI readback");
 if(!EXTENDED) begin
  scan(0,0);
  if(fb_failed || fb_overflow || fb_completed!=1 || !bg0 || !bg1) $fatal(1,"Full-HD scan coverage/error");
  $display("PASS tb_c2_framebuffer geometry=%0dx%0d full_HD=1 stride=%0d bank_pitch=%0d full_bytes=%0d display_bytes=%0d cpu_bursts=%0d tinyml_bursts=%0d max_aw_wait=%0d max_ar_wait=%0d actual_full_frame_write_read final_B_fence single_DDR synthetic_masters",FRAME_WIDTH,FRAME_HEIGHT,STRIDE,PITCH,full_checks,display_checks,bg0,bg1,peak_aw,peak_ar);
  $finish;
 end
 fork
  begin scan(0,0);end
  begin pixels(1,0);boundary();wait(fb_published==2);check_bank(1);release_image(1);end
 join
 $display("CHECK simultaneous source/display/AI/CPU/TinyML");scan(1,0);scan(1,0);
 if(fb_repeated==0) $fatal(1,"No repeat of held DISPLAY bank");
 // Keep DISPLAY frame1 and fill the other banks; newest whole source frame must drop.
 pixels(2,0);boundary();wait(fb_published==3);release_image(2);
 pixels(3,0);boundary();wait(fb_published==4);release_image(3);
 count_before=fb_dropped;pixels(4,0);boundary();release_image(4);
 wait(fb_dropped>count_before);
 if(fb_published!=4) $fatal(1,"No-free-bank frame incorrectly published");
 $display("CHECK no-free-bank drop");scan(2,0);scan(3,0);
 // Invalid geometry is drained, does not become READY, next valid frame recovers.
 count_before=fb_dropped;pixels(5,1);boundary();wait(fb_dropped>count_before);
 pixels(6,0);boundary();wait(fb_published==5);check_bank(6);release_image(6);
 $display("CHECK malformed recovery");scan(6,1);scan(6,0);$display("CHECK underflow recovery");
 // Stop background traffic before injecting bus faults, to target only video.
 bg_run=0;wait(!bg_busy0 && !bg_busy1);repeat(500) @(negedge clk);
 inject_b_error=1;count_before=fb_write_errors;
 pixels(7,0);boundary();wait(fb_write_errors>count_before);inject_b_error=0;
 // AI DMA used the same injected error; explicitly collect error if it failed.
 wait(delivered_valid);
 tmp_status=delivered[547:545];collect(7,tmp_status,tmp_slot,tmp_generation);
 if(tmp_status==0) begin control(3,tmp_slot,tmp_generation,0);control(4,tmp_slot,tmp_generation,0);end
 if(fb_published!=5) $fatal(1,"BRESP-failed video became READY");
 inject_r_error=1;count_before=fb_read_errors;
 scan(6,-1);wait(fb_read_errors>count_before);inject_r_error=0;
 if(!fb_failed) $fatal(1,"RRESP error failed to invalidate scan");
 // Stall new DDR bursts while real source pixels continue: overflow must poison
 // the whole video frame, then drain/recover without publishing partial pixels.
 count_before=fb_dropped;
 fork
  begin pixels(8,0);boundary();end
  begin repeat(500) @(negedge vclk);pause_ddr=1;wait(capture_record_valid);repeat(30) @(negedge vclk);pause_ddr=0;end
 join
 wait(fb_dropped>count_before);release_image(8);
 if(fb_overflow!=1 || fb_published!=5) $fatal(1,"Source overflow did not discard exactly one full frame");
 pixels(9,0);boundary();wait(fb_published==6);check_bank(9);release_image(9);scan(9,0);
 $display("CHECK BRESP/RRESP and source-overflow recovery");
 // Reset while source, display and AXI are active. Memory content alone must not create READY.
 fork
  begin pixels(10,0);end
  begin wait(fbpipe.wvalid && fbpipe.wready);@(negedge clk);rst_n=0;end
 join
 pixel_de=0;pixel_vs=0;display_de=0;display_vs=0;repeat(8) @(negedge clk);rst_n=1;
 wait(a_source.capture_rst_n);repeat(10) @(negedge vclk);
 if(fb_published || fb_busy || fbpipe.framebuffer.bank_states || states) $fatal(1,"Ghost frame after common reset");
 boundary();pixels(0,0);boundary();wait(fb_published==1);check_bank(0);release_image(0);scan(0,0);
 if(core_protocol_error || cpu_adapter_error || cpu_rejected || protocol_error || fb_overflow)
  $fatal(1,"Unexpected fabric/capture error");
 if(!overlap_ai || !overlap_display || bg0<2 || bg1<2 || !display_checks || !peak_aw || !peak_ar || !cpu_max_wait || !ml_max_wait)
  $fatal(1,"Missing concurrent/wait coverage ai=%0d rw=%0d cpu=%0d ml=%0d aw=%0d ar=%0d",overlap_ai,overlap_display,bg0,bg1,fb_max_aw,fb_max_ar);
 $display("PASS tb_c2_framebuffer geometry=%0dx%0d stride=%0d bank_pitch=%0d full_bytes=%0d display_bytes=%0d cpu_bursts=%0d tinyml_bursts=%0d overlap_ai=%0d overlap_rw=%0d max_aw_wait=%0d max_ar_wait=%0d cpu_max_wait=%0d tinyml_max_wait=%0d source_verdict final_B_fence triple_buffer repeat drop malformed underflow BRESP RRESP source_overflow common_reset single_DDR synthetic_masters",FRAME_WIDTH,FRAME_HEIGHT,STRIDE,PITCH,full_checks,display_checks,bg0,bg1,overlap_ai,overlap_display,peak_aw,peak_ar,cpu_max_wait,ml_max_wait);
 $finish;
end
initial begin #150000000;$fatal(1,"Concurrent framebuffer timeout ws=%0d rs=%0d pub=%0d drop=%0d ingress_active=%b ingress_bad=%b source_records=%0d busy=%b underflows=%0d",fbpipe.framebuffer.ws,fbpipe.framebuffer.rs,fb_published,fb_dropped,fbpipe.ingress.active,fbpipe.ingress.bad,record_checks,fb_busy,fb_underflows);end
endmodule
