`timescale 1ns/1ps
// Attachment to vendor interconnect S1, not a replacement for CPU/TinyML S0/S2.
module c2_vendor_attachment #(
 parameter VIDEO_ID_WIDTH=4,REQUIRE_SOURCE_COMPLETION=0,
 parameter integer TIME_CLOCK_HZ=100000000,
 parameter [31:0] SHARED_BASE=32'h09010000,VIDEO_BASE=32'h08010000,VIDEO_BYTES=32'h01000000
)(
input wire arst_n,mem_clk,video_clk,pclk,map_enable,external_protocol_error,
output wire [31:0] shared_video_ms,output wire shared_video_valid,
input wire [15:0] paddr,input wire psel,penable,pwrite,input wire [31:0] pwdata,
output wire pready,output wire [31:0] prdata,output wire pslverror,irq,
input wire video_awvalid,
output wire video_awready,
input wire [31:0] video_awaddr,
input wire [7:0] video_awlen,
input wire video_wvalid,
output wire video_wready,
input wire [127:0] video_wdata,
input wire [15:0] video_wstrb,
input wire video_wlast,
output wire video_bvalid,
input wire video_bready,
output wire [1:0] video_bresp,
input wire video_arvalid,
output wire video_arready,
input wire [31:0] video_araddr,
input wire [7:0] video_arlen,
output wire video_rvalid,
input wire video_rready,
output wire [127:0] video_rdata,
output wire video_rlast,
output wire [1:0] video_rresp,
input wire [VIDEO_ID_WIDTH-1:0] video_awid,
input wire [2:0] video_awsize,
input wire [1:0] video_awburst,
input wire video_awlock,
input wire [VIDEO_ID_WIDTH-1:0] video_arid,
input wire [2:0] video_arsize,
input wire [1:0] video_arburst,
input wire video_arlock,
output wire [VIDEO_ID_WIDTH-1:0] video_bid,
output wire [VIDEO_ID_WIDTH-1:0] video_rid,
input wire v_frame_valid,output wire v_frame_ready,input wire [511:0] v_descriptor,
output wire v_grant_valid,input wire v_grant_ready,output wire [31:0] v_grant_frame_id,
input wire v_word_valid,output wire v_word_ready,input wire [127:0] v_word_data,
input wire v_source_valid,output wire v_source_ready,input wire v_source_error,
input wire [31:0] v_source_frame_id,v_source_fnv,
output wire v_event_valid,input wire v_event_ready,output wire [2:0] v_event_status,
output wire v_event_slot,output wire [31:0] v_event_generation,output wire [511:0] v_event_descriptor,
output wire m_awvalid,
input wire m_awready,
output wire [31:0] m_awaddr,
output wire [7:0] m_awlen,
output wire [2:0] m_awsize,
output wire [1:0] m_awburst,
output wire m_wvalid,
input wire m_wready,
output wire [127:0] m_wdata,
output wire [15:0] m_wstrb,
output wire m_wlast,
input wire m_bvalid,
output wire m_bready,
input wire [1:0] m_bresp,
output wire m_arvalid,
input wire m_arready,
output wire [31:0] m_araddr,
output wire [7:0] m_arlen,
output wire [2:0] m_arsize,
output wire [1:0] m_arburst,
input wire m_rvalid,
output wire m_rready,
input wire [127:0] m_rdata,
input wire m_rlast,
input wire [1:0] m_rresp,
output wire protocol_error
);
reg [1:0] reset_release;
wire rst_n=reset_release[1];
always @(posedge mem_clk or negedge arst_n)
 if(!arst_n) reset_release<=0;else reset_release<={reset_release[0],1'b1};
wire cpu_valid,cpu_ready,cpu_slot,cpu_rsp_valid,cpu_rsp_ready,cpu_rsp_slot;
wire [2:0] cpu_cmd;wire [1:0] cpu_rsp_status;
wire [31:0] cpu_generation,cpu_rsp_generation,dropped;
wire [511:0] cpu_descriptor;wire [3:0] slot_states;
wire core_error,video_rejected,video_error,frame_ready;
assign protocol_error=core_error || video_rejected || video_error || external_protocol_error;
wire q_awvalid;
wire q_awready;
wire [31:0] q_awaddr;
wire [7:0] q_awlen;
wire q_wvalid;
wire q_wready;
wire [127:0] q_wdata;
wire [15:0] q_wstrb;
wire q_wlast;
wire q_bvalid;
wire q_bready;
wire [1:0] q_bresp;
wire q_arvalid;
wire q_arready;
wire [31:0] q_araddr;
wire [7:0] q_arlen;
wire q_rvalid;
wire q_rready;
wire [127:0] q_rdata;
wire q_rlast;
wire [1:0] q_rresp;
c2_axi_to_vendor #(.ID_WIDTH(VIDEO_ID_WIDTH),.ALLOW_NARROW(0),
 .SOURCE_BASE(0),.TARGET_BASE(VIDEO_BASE),.WINDOW_BYTES(VIDEO_BYTES)) video_adapter(
.clk(mem_clk),.rst_n(rst_n),.enable(map_enable),
.s_awvalid(video_awvalid),
.s_awready(video_awready),
.s_awaddr(video_awaddr),
.s_awlen(video_awlen),
.s_wvalid(video_wvalid),
.s_wready(video_wready),
.s_wdata(video_wdata),
.s_wstrb(video_wstrb),
.s_wlast(video_wlast),
.s_bvalid(video_bvalid),
.s_bready(video_bready),
.s_bresp(video_bresp),
.s_arvalid(video_arvalid),
.s_arready(video_arready),
.s_araddr(video_araddr),
.s_arlen(video_arlen),
.s_rvalid(video_rvalid),
.s_rready(video_rready),
.s_rdata(video_rdata),
.s_rlast(video_rlast),
.s_rresp(video_rresp),
.s_awid(video_awid),
.s_awsize(video_awsize),
.s_awburst(video_awburst),
.s_awlock(video_awlock),
.s_arid(video_arid),
.s_arsize(video_arsize),
.s_arburst(video_arburst),
.s_arlock(video_arlock),
.s_bid(video_bid),
.s_rid(video_rid),
.m_awvalid(q_awvalid),
.m_awready(q_awready),
.m_awaddr(q_awaddr),
.m_awlen(q_awlen),
.m_wvalid(q_wvalid),
.m_wready(q_wready),
.m_wdata(q_wdata),
.m_wstrb(q_wstrb),
.m_wlast(q_wlast),
.m_bvalid(q_bvalid),
.m_bready(q_bready),
.m_bresp(q_bresp),
.m_arvalid(q_arvalid),
.m_arready(q_arready),
.m_araddr(q_araddr),
.m_arlen(q_arlen),
.m_rvalid(q_rvalid),
.m_rready(q_rready),
.m_rdata(q_rdata),
.m_rlast(q_rlast),
.m_rresp(q_rresp),
.rejected(video_rejected),.protocol_error(video_error));
c2_apb_control #(.TIME_CLOCK_HZ(TIME_CLOCK_HZ),.REQUIRE_SOURCE_COMPLETION(REQUIRE_SOURCE_COMPLETION),.SHARED_BASE(SHARED_BASE),.VIDEO_BASE(VIDEO_BASE),.VIDEO_BYTES(VIDEO_BYTES)) control(
.arst_n(arst_n),.pclk(pclk),.mem_clk(mem_clk),.video_clk(video_clk),.map_enable(map_enable),
.shared_video_ms(shared_video_ms),.shared_video_valid(shared_video_valid),
.paddr(paddr),.psel(psel),.penable(penable),.pwrite(pwrite),.pwdata(pwdata),
.pready(pready),.prdata(prdata),.pslverror(pslverror),.irq(irq),
.cpu_valid(cpu_valid),
.cpu_ready(cpu_ready),
.cpu_cmd(cpu_cmd),
.cpu_slot(cpu_slot),
.cpu_generation(cpu_generation),
.cpu_rsp_valid(cpu_rsp_valid),
.cpu_rsp_ready(cpu_rsp_ready),
.cpu_rsp_status(cpu_rsp_status),
.cpu_rsp_slot(cpu_rsp_slot),
.cpu_rsp_generation(cpu_rsp_generation),
.cpu_descriptor(cpu_descriptor),
.slot_states(slot_states),.dropped(dropped),.protocol_error(protocol_error));
wire [2:0] c_awready;
assign q_awready=c_awready[0:0];
wire [2:0] c_wready;
assign q_wready=c_wready[0:0];
wire [2:0] c_bvalid;
assign q_bvalid=c_bvalid[0:0];
wire [5:0] c_bresp;
assign q_bresp=c_bresp[1:0];
wire [2:0] c_arready;
assign q_arready=c_arready[0:0];
wire [2:0] c_rvalid;
assign q_rvalid=c_rvalid[0:0];
wire [383:0] c_rdata;
assign q_rdata=c_rdata[127:0];
wire [2:0] c_rlast;
assign q_rlast=c_rlast[0:0];
wire [5:0] c_rresp;
assign q_rresp=c_rresp[1:0];
c2_system_boundary #(.REQUIRE_SOURCE_COMPLETION(REQUIRE_SOURCE_COMPLETION)) core(.arst_n(arst_n),.mem_clk(mem_clk),.video_clk(video_clk),
.v_source_valid(v_source_valid),.v_source_ready(v_source_ready),.v_source_error(v_source_error),
.v_source_frame_id(v_source_frame_id),.v_source_fnv(v_source_fnv),
.s_awvalid({2'b0,q_awvalid}),
.s_awready(c_awready),
.s_awaddr({64'b0,q_awaddr}),
.s_awlen({16'b0,q_awlen}),
.s_wvalid({2'b0,q_wvalid}),
.s_wready(c_wready),
.s_wdata({256'b0,q_wdata}),
.s_wstrb({32'b0,q_wstrb}),
.s_wlast({2'b0,q_wlast}),
.s_bvalid(c_bvalid),
.s_bready({2'b0,q_bready}),
.s_bresp(c_bresp),
.s_arvalid({2'b0,q_arvalid}),
.s_arready(c_arready),
.s_araddr({64'b0,q_araddr}),
.s_arlen({16'b0,q_arlen}),
.s_rvalid(c_rvalid),
.s_rready({2'b0,q_rready}),
.s_rdata(c_rdata),
.s_rlast(c_rlast),
.s_rresp(c_rresp),
.cpu_valid(cpu_valid),
.cpu_ready(cpu_ready),
.cpu_cmd(cpu_cmd),
.cpu_slot(cpu_slot),
.cpu_generation(cpu_generation),
.cpu_rsp_valid(cpu_rsp_valid),
.cpu_rsp_ready(cpu_rsp_ready),
.cpu_rsp_status(cpu_rsp_status),
.cpu_rsp_slot(cpu_rsp_slot),
.cpu_rsp_generation(cpu_rsp_generation),
.cpu_descriptor(cpu_descriptor),
.slot_states(slot_states),.dropped(dropped),
.v_frame_valid(v_frame_valid && map_enable),.v_frame_ready(frame_ready),
.v_descriptor(v_descriptor),.shared_base(SHARED_BASE),
.v_grant_valid(v_grant_valid),
.v_grant_ready(v_grant_ready),
.v_grant_frame_id(v_grant_frame_id),
.v_word_valid(v_word_valid),
.v_word_ready(v_word_ready),
.v_word_data(v_word_data),
.v_event_valid(v_event_valid),
.v_event_ready(v_event_ready),
.v_event_status(v_event_status),
.v_event_slot(v_event_slot),
.v_event_generation(v_event_generation),
.v_event_descriptor(v_event_descriptor),
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
.protocol_error(core_error));
assign v_frame_ready=frame_ready && map_enable;
endmodule

