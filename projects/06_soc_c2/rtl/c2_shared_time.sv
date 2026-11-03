`timescale 1ns/1ps
// One reset epoch, one 32-bit millisecond counter. Video receives held, coherent
// snapshots through the existing request/ack CDC, never a free-running binary bus.
// Continuous clocks and common reset are required; physical CDC review remains.
module c2_shared_time #(
 parameter integer CLOCK_HZ=100000000,
 parameter [31:0] INITIAL_MS=0
)(
 input wire arst_n,pclk,video_clk,
 output reg [31:0] cpu_ms,output wire cpu_valid,
 output reg [31:0] video_ms,output reg video_valid
);
 localparam integer CYCLES_PER_MS=CLOCK_HZ/1000;
 localparam integer DIV_BITS=CYCLES_PER_MS>1?$clog2(CYCLES_PER_MS):1;
 reg [DIV_BITS-1:0] divider;
 reg [1:0] released;
 wire snap_valid;wire [31:0] snapshot;
 assign cpu_valid=released[1];
 always @(posedge pclk or negedge arst_n) begin
  if(!arst_n) begin released<=0;divider<=0;cpu_ms<=INITIAL_MS;end
  else begin
   released<={released[0],1'b1};
   if(released[1]) begin
    if(divider==DIV_BITS'(CYCLES_PER_MS-1)) begin divider<=0;cpu_ms<=cpu_ms+1'b1;end
    else divider<=divider+1'b1;
   end
  end
 end
 c2_cdc_mailbox #(.WIDTH(32)) snapshots(
  .arst_n(arst_n),.s_clk(pclk),.s_valid(cpu_valid),.s_ready(),.s_data(cpu_ms),
  .d_clk(video_clk),.d_valid(snap_valid),.d_ready(1'b1),.d_data(snapshot));
 always @(posedge video_clk or negedge arst_n) begin
  if(!arst_n) begin video_ms<=INITIAL_MS;video_valid<=0;end
  else if(snap_valid) begin video_ms<=snapshot;video_valid<=1;end
 end
endmodule
