`timescale 1ns/1ps
module c2_bus_fixture #(parameter N=4)(
input wire clk,rst_n,inject_b_error,inject_r_error,
input wire [N*1-1:0] s_awvalid,
output wire [N*1-1:0] s_awready,
input wire [N*32-1:0] s_awaddr,
input wire [N*8-1:0] s_awlen,
input wire [N*1-1:0] s_wvalid,
output wire [N*1-1:0] s_wready,
input wire [N*128-1:0] s_wdata,
input wire [N*16-1:0] s_wstrb,
input wire [N*1-1:0] s_wlast,
output wire [N*1-1:0] s_bvalid,
input wire [N*1-1:0] s_bready,
output wire [N*2-1:0] s_bresp,
input wire [N*1-1:0] s_arvalid,
output wire [N*1-1:0] s_arready,
input wire [N*32-1:0] s_araddr,
input wire [N*8-1:0] s_arlen,
output wire [N*1-1:0] s_rvalid,
input wire [N*1-1:0] s_rready,
output wire [N*128-1:0] s_rdata,
output wire [N*1-1:0] s_rlast,
output wire [N*2-1:0] s_rresp,
output wire protocol_error, output wire [31:0] completed_writes,completed_reads
);
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
c2_axi_arbiter #(.N(N)) arb(
.clk(clk),.rst_n(rst_n),
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
.protocol_error(protocol_error));
c2_ddr_model memory_model(.clk(clk),.rst_n(rst_n),.inject_b_error(inject_b_error),.inject_r_error(inject_r_error),
.awvalid(m_awvalid),
.awready(m_awready),
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
.arvalid(m_arvalid),
.arready(m_arready),
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
reg aw_held,w_held,ar_held,r_held,b_held;
reg [39:0] prev_aw,prev_ar;
reg [144:0] prev_w;
reg [130:0] prev_r;
reg [1:0] prev_b;
always @(posedge clk) begin
 if(!rst_n) begin aw_held=0;w_held=0;ar_held=0;r_held=0;b_held=0;end
 else begin
   if(aw_held && (!m_awvalid || {m_awaddr,m_awlen}!==prev_aw)) $fatal(1,"AW changed while stalled");
   if(w_held && (!m_wvalid || {m_wdata,m_wstrb,m_wlast}!==prev_w)) $fatal(1,"W changed while stalled");
   if(ar_held && (!m_arvalid || {m_araddr,m_arlen}!==prev_ar)) $fatal(1,"AR changed while stalled");
   if(r_held && (!m_rvalid || {m_rdata,m_rlast,m_rresp}!==prev_r)) $fatal(1,"R changed while stalled");
   if(b_held && (!m_bvalid || m_bresp!==prev_b)) $fatal(1,"B changed while stalled");
   aw_held=m_awvalid&&!m_awready;prev_aw={m_awaddr,m_awlen};
   w_held=m_wvalid&&!m_wready;prev_w={m_wdata,m_wstrb,m_wlast};
   ar_held=m_arvalid&&!m_arready;prev_ar={m_araddr,m_arlen};
   r_held=m_rvalid&&!m_rready;prev_r={m_rdata,m_rlast,m_rresp};
   b_held=m_bvalid&&!m_bready;prev_b=m_bresp;
 end
end
endmodule

