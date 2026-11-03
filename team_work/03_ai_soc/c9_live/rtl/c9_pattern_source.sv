`timescale 1ns/1ps
// One commanded 1920x1080 constant-gray frame, including a closing VS to flush
// A's delayed final sample/record. Command seed is explicit test provenance.
module c9_pattern_source #(parameter WIDTH=1920,HEIGHT=1080,HTOTAL=2048)(
 input wire clk,arst_n,command_valid,output wire command_ready,
 input wire [7:0] command_gray,output wire vs,de,output wire [7:0] gray,
 output reg [31:0] completed,output wire busy
);
 reg active,primed;reg [11:0] x,y;reg [7:0] seed;
 localparam LAST_LINE=HEIGHT+46;
 assign busy=active;assign command_ready=!active;
 assign vs=active && (y==0 || y==LAST_LINE);
 assign de=active && y>=2 && y<HEIGHT+2 && x<WIDTH;
 assign gray=seed;
 always @(posedge clk or negedge arst_n)
 if(!arst_n)begin active<=0;primed<=0;x<=0;y<=0;seed<=0;completed<=0;end
 else if(!active)begin
  // The previous closing VS already opened the next frame in A's sampler.
  // Do not emit a second opening VS around an empty inter-command interval.
  if(command_valid && command_ready)begin active<=1;primed<=1;x<=0;y<=primed?1:0;seed<=command_gray;end
 end else if(x==HTOTAL-1)begin
  x<=0;
  if(y==LAST_LINE)begin active<=0;y<=0;completed<=completed+1;end
  else y<=y+1'b1;
 end else x<=x+1'b1;
endmodule
