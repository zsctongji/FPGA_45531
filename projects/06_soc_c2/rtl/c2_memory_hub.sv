`timescale 1ns/1ps
// Prototype memory hub: external slots CPU=0, TinyML=1, video framebuffer=2;
// internal image writer=3. One DDR transaction boundary, no PHY instantiated.
module c2_memory_hub(
input wire clk,rst_n,
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
input wire image_start_valid,output wire image_start_ready,input wire [31:0] image_address,
input wire [127:0] image_words,input wire image_valid,output wire image_ready,
output wire image_done_valid,input wire image_done_ready,output wire image_error,
output wire [31:0] image_checksum,
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
wire [4*1-1:0] f_awvalid;
wire [4*1-1:0] f_awready;
wire [4*32-1:0] f_awaddr;
wire [4*8-1:0] f_awlen;
wire [4*1-1:0] f_wvalid;
wire [4*1-1:0] f_wready;
wire [4*128-1:0] f_wdata;
wire [4*16-1:0] f_wstrb;
wire [4*1-1:0] f_wlast;
wire [4*1-1:0] f_bvalid;
wire [4*1-1:0] f_bready;
wire [4*2-1:0] f_bresp;
wire [4*1-1:0] f_arvalid;
wire [4*1-1:0] f_arready;
wire [4*32-1:0] f_araddr;
wire [4*8-1:0] f_arlen;
wire [4*1-1:0] f_rvalid;
wire [4*1-1:0] f_rready;
wire [4*128-1:0] f_rdata;
wire [4*1-1:0] f_rlast;
wire [4*2-1:0] f_rresp;
assign s_awready=f_awready[2:0];
assign s_wready=f_wready[2:0];
assign s_bvalid=f_bvalid[2:0];
assign s_bresp=f_bresp[5:0];
assign s_arready=f_arready[2:0];
assign s_rvalid=f_rvalid[2:0];
assign s_rdata=f_rdata[383:0];
assign s_rlast=f_rlast[2:0];
assign s_rresp=f_rresp[5:0];
wire t_awvalid,t_wvalid,t_wlast,t_bready;
wire [31:0] t_awaddr;wire [7:0] t_awlen;wire [127:0] t_wdata;wire [15:0] t_wstrb;
assign f_awvalid={t_awvalid,s_awvalid};
assign f_awaddr={t_awaddr,s_awaddr};
assign f_awlen={t_awlen,s_awlen};
assign f_wvalid={t_wvalid,s_wvalid};
assign f_wdata={t_wdata,s_wdata};
assign f_wstrb={t_wstrb,s_wstrb};
assign f_wlast={t_wlast,s_wlast};
assign f_bready={t_bready,s_bready};
assign f_arvalid={1'b0,s_arvalid};
assign f_araddr={32'b0,s_araddr};
assign f_arlen={8'b0,s_arlen};
assign f_rready={1'b0,s_rready};
c2_image_writer writer(.clk(clk),.rst_n(rst_n),.start_valid(image_start_valid),.start_ready(image_start_ready),.start_address(image_address),
.pixel_words(image_words),.pixel_valid(image_valid),.pixel_ready(image_ready),
.awvalid(t_awvalid),.awready(f_awready[3]),.awaddr(t_awaddr),.awlen(t_awlen),
.wvalid(t_wvalid),.wready(f_wready[3]),.wdata(t_wdata),.wstrb(t_wstrb),.wlast(t_wlast),
.bvalid(f_bvalid[3]),.bready(t_bready),.bresp(f_bresp[6+:2]),
.done_valid(image_done_valid),.done_ready(image_done_ready),.done_error(image_error),.done_checksum(image_checksum));
c2_axi_arbiter #(.N(4)) arb(.clk(clk),.rst_n(rst_n),
.s_awvalid(f_awvalid),
.s_awready(f_awready),
.s_awaddr(f_awaddr),
.s_awlen(f_awlen),
.s_wvalid(f_wvalid),
.s_wready(f_wready),
.s_wdata(f_wdata),
.s_wstrb(f_wstrb),
.s_wlast(f_wlast),
.s_bvalid(f_bvalid),
.s_bready(f_bready),
.s_bresp(f_bresp),
.s_arvalid(f_arvalid),
.s_arready(f_arready),
.s_araddr(f_araddr),
.s_arlen(f_arlen),
.s_rvalid(f_rvalid),
.s_rready(f_rready),
.s_rdata(f_rdata),
.s_rlast(f_rlast),
.s_rresp(f_rresp),
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
endmodule

