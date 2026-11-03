`timescale 1ns/1ps
// Synthesizable C2 functional boundary, not an Efinity board top.
// Three memory-domain clients: CPU, TinyML, vendor video frame-buffer AXI.
module c2_system_boundary #(parameter REQUIRE_SOURCE_COMPLETION=0)(
input wire arst_n,mem_clk,video_clk,
input wire [3*1-1:0] s_awvalid,
output wire [3*1-1:0] s_awready,
input wire [3*32-1:0] s_awaddr,
input wire [3*8-1:0] s_awlen,
input wire [3*1-1:0] s_wvalid,
output wire [3*1-1:0] s_wready,
input wire [3*128-1:0] s_wdata,
input wire [3*16-1:0] s_wstrb,
input wire [3*1-1:0] s_wlast,
output wire [3*1-1:0] s_bvalid,
input wire [3*1-1:0] s_bready,
output wire [3*2-1:0] s_bresp,
input wire [3*1-1:0] s_arvalid,
output wire [3*1-1:0] s_arready,
input wire [3*32-1:0] s_araddr,
input wire [3*8-1:0] s_arlen,
output wire [3*1-1:0] s_rvalid,
input wire [3*1-1:0] s_rready,
output wire [3*128-1:0] s_rdata,
output wire [3*1-1:0] s_rlast,
output wire [3*2-1:0] s_rresp,
input wire v_frame_valid,output wire v_frame_ready,
input wire [511:0] v_descriptor,input wire [31:0] shared_base,
output wire v_grant_valid,input wire v_grant_ready,output wire [31:0] v_grant_frame_id,
input wire v_word_valid,output wire v_word_ready,input wire [127:0] v_word_data,
input wire v_source_valid,output wire v_source_ready,input wire v_source_error,
input wire [31:0] v_source_frame_id,v_source_fnv,
output wire v_event_valid,input wire v_event_ready,output wire [2:0] v_event_status,
output wire v_event_slot,output wire [31:0] v_event_generation,output wire [511:0] v_event_descriptor,
input wire cpu_valid,output wire cpu_ready,input wire [2:0] cpu_cmd,
input wire cpu_slot,input wire [31:0] cpu_generation,
output wire cpu_rsp_valid,input wire cpu_rsp_ready,output wire [1:0] cpu_rsp_status,
output wire [511:0] cpu_descriptor,
output wire cpu_rsp_slot,output wire [31:0] cpu_rsp_generation,
output wire [3:0] slot_states,output wire [31:0] dropped,
output wire [0:0] m_awvalid,
input wire [0:0] m_awready,
output wire [31:0] m_awaddr,
output wire [7:0] m_awlen,
output wire [2:0] m_awsize,
output wire [1:0] m_awburst,
output wire [0:0] m_wvalid,
input wire [0:0] m_wready,
output wire [127:0] m_wdata,
output wire [15:0] m_wstrb,
output wire [0:0] m_wlast,
input wire [0:0] m_bvalid,
output wire [0:0] m_bready,
input wire [1:0] m_bresp,
output wire [0:0] m_arvalid,
input wire [0:0] m_arready,
output wire [31:0] m_araddr,
output wire [7:0] m_arlen,
output wire [2:0] m_arsize,
output wire [1:0] m_arburst,
input wire [0:0] m_rvalid,
output wire [0:0] m_rready,
input wire [127:0] m_rdata,
input wire [0:0] m_rlast,
input wire [1:0] m_rresp,
output wire protocol_error
);
reg [1:0] reset_release;
wire rst_n=reset_release[1];
always @(posedge mem_clk or negedge arst_n)
 if(!arst_n) reset_release<=0;else reset_release<={reset_release[0],1'b1};
wire frame_valid,frame_ready;
wire [543:0] frame_payload;
wire result_valid,result_ready,result_slot;
wire [2:0] result_status;
wire [31:0] result_generation;
wire [511:0] result_descriptor;
wire [547:0] result_payload;
wire write_request_valid,write_request_ready,image_start_valid,image_start_ready;
wire [31:0] image_address,image_checksum;
wire [127:0] image_words;
wire image_valid,image_ready,image_done_valid,image_done_ready,image_error,grant_ready;
wire publish_done_valid,publish_done_ready,publish_error;
wire [31:0] publish_checksum;
generate if(REQUIRE_SOURCE_COMPLETION) begin: source_fence
 wire verdict_valid,verdict_ready;wire [64:0] verdict;
 c2_cdc_mailbox #(.WIDTH(65)) verdict_cdc(.arst_n(arst_n),.s_clk(video_clk),
  .s_valid(v_source_valid),.s_ready(v_source_ready),.s_data({v_source_error,v_source_frame_id,v_source_fnv}),
  .d_clk(mem_clk),.d_valid(verdict_valid),.d_ready(verdict_ready),.d_data(verdict));
 c2_source_fence fence(.clk(mem_clk),.rst_n(rst_n),.start(image_start_valid && image_start_ready),
  .frame_id(result_descriptor[63:32]),.writer_valid(image_done_valid),.writer_ready(image_done_ready),
  .writer_error(image_error),.writer_fnv(image_checksum),.source_valid(verdict_valid),.source_ready(verdict_ready),
  .source_error(verdict[64]),.source_frame_id(verdict[63:32]),.source_fnv(verdict[31:0]),
  .done_valid(publish_done_valid),.done_ready(publish_done_ready),.done_error(publish_error),.done_fnv(publish_checksum));
end else begin: legacy_fence
 assign v_source_ready=0;
 assign publish_done_valid=image_done_valid;assign image_done_ready=publish_done_ready;
 assign publish_error=image_error;assign publish_checksum=image_checksum;
end endgenerate
c2_cdc_mailbox #(.WIDTH(544)) requests(.arst_n(arst_n),.s_clk(video_clk),
 .s_valid(v_frame_valid),.s_ready(v_frame_ready),.s_data({shared_base,v_descriptor}),
 .d_clk(mem_clk),.d_valid(frame_valid),.d_ready(frame_ready),.d_data(frame_payload));
c2_cdc_mailbox #(.WIDTH(548)) events(.arst_n(arst_n),.s_clk(mem_clk),
 .s_valid(result_valid),.s_ready(result_ready),
 .s_data({result_status,result_slot,result_generation,result_descriptor}),
 .d_clk(video_clk),.d_valid(v_event_valid),.d_ready(v_event_ready),.d_data(result_payload));
assign {v_event_status,v_event_slot,v_event_generation,v_event_descriptor}=result_payload;
// Grant must be queued atomically with writer start. Video supplies exactly 576
// words AFTER receiving the matching grant; on BUSY/error it supplies no words.
c2_cdc_mailbox #(.WIDTH(32)) grants(.arst_n(arst_n),.s_clk(mem_clk),
 .s_valid(write_request_valid && image_start_ready),.s_ready(grant_ready),
 .s_data(result_descriptor[63:32]),.d_clk(video_clk),
 .d_valid(v_grant_valid),.d_ready(v_grant_ready),.d_data(v_grant_frame_id));
assign image_start_valid=write_request_valid && grant_ready;
assign write_request_ready=image_start_ready && grant_ready;
c2_async_fifo #(.WIDTH(128),.ADDR_BITS(4)) pixels(.arst_n(arst_n),.s_clk(video_clk),
 .s_valid(v_word_valid),.s_ready(v_word_ready),.s_data(v_word_data),
 .d_clk(mem_clk),.d_valid(image_valid),.d_ready(image_ready),.d_data(image_words));
c2_frame_publisher publisher(.clk(mem_clk),.rst_n(rst_n),
 .frame_valid(frame_valid),.frame_ready(frame_ready),
 .frame_descriptor(frame_payload[511:0]),.shared_base(frame_payload[543:512]),
 .write_start_valid(write_request_valid),.write_start_ready(write_request_ready),.write_address(image_address),
 .write_done_valid(publish_done_valid),.write_done_ready(publish_done_ready),
 .write_done_error(publish_error),.write_checksum(publish_checksum),
 .event_valid(result_valid),.event_ready(result_ready),.event_status(result_status),
 .event_slot(result_slot),.event_generation(result_generation),.event_descriptor(result_descriptor),
 .cpu_valid(cpu_valid),.cpu_ready(cpu_ready),.cpu_cmd(cpu_cmd),.cpu_slot(cpu_slot),.cpu_generation(cpu_generation),
 .cpu_rsp_valid(cpu_rsp_valid),.cpu_rsp_ready(cpu_rsp_ready),.cpu_rsp_status(cpu_rsp_status),
 .cpu_descriptor(cpu_descriptor),.cpu_rsp_slot(cpu_rsp_slot),.cpu_rsp_generation(cpu_rsp_generation),
 .slot_states(slot_states),.dropped(dropped));
c2_memory_hub hub(.clk(mem_clk),.rst_n(rst_n),
.s_awvalid(s_awvalid),
.s_awready(s_awready),
.s_awaddr(s_awaddr),
.s_awlen(s_awlen),
.s_wvalid(s_wvalid),
.s_wready(s_wready),
.s_wdata(s_wdata),
.s_wstrb(s_wstrb),
.s_wlast(s_wlast),
.s_bvalid(s_bvalid),
.s_bready(s_bready),
.s_bresp(s_bresp),
.s_arvalid(s_arvalid),
.s_arready(s_arready),
.s_araddr(s_araddr),
.s_arlen(s_arlen),
.s_rvalid(s_rvalid),
.s_rready(s_rready),
.s_rdata(s_rdata),
.s_rlast(s_rlast),
.s_rresp(s_rresp),
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
.image_start_valid(image_start_valid),.image_start_ready(image_start_ready),.image_address(image_address),
.image_words(image_words),.image_valid(image_valid),.image_ready(image_ready),
.image_done_valid(image_done_valid),.image_done_ready(image_done_ready),.image_error(image_error),
.image_checksum(image_checksum),.protocol_error(protocol_error));
endmodule

