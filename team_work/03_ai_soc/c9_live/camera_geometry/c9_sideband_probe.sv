`timescale 1ns/1ps
// Only pixel-clock-domain sideband enters this monitor. RUN is a single-bit CDC.
module c9_sideband_probe(input wire clk,arst_n,run_async,hs,de,fault,
 input wire [15:0] pixel_wordcount,input wire [5:0] pixel_datatype,
 input wire [3:0] pixel_per_clk,input wire [1:0] pixel_vc,
 output wire [63:0] observation);
 (* async_reg="true" *) reg run1,run2;
 reg seen,other_seen,outside_hs;reg [15:0] ppc_mask;
 reg [19:0] last_image; // PPC + byte count; type/VC are checked before capture.
 always @(posedge clk or negedge arst_n)begin
  if(!arst_n)begin run1<=0;run2<=0;end
  else begin run1<=run_async;run2<=run1;end
 end
 always @(posedge clk or negedge arst_n)begin
  if(!arst_n)begin seen<=0;other_seen<=0;outside_hs<=0;ppc_mask<=0;last_image<=0;end
  else if(!run2)begin seen<=0;other_seen<=0;outside_hs<=0;ppc_mask<=0;last_image<=0;end
  else if(de)begin
   if(pixel_datatype==6'h2b && pixel_vc==0)begin
    seen<=1;last_image<={pixel_per_clk,pixel_wordcount};
    ppc_mask[pixel_per_clk]<=1'b1;
    if(!hs)outside_hs<=1;
   end else other_seen<=1;
  end
 end
 assign observation={16'hc9d1,ppc_mask,seen,other_seen,outside_hs,fault,
                     2'b0,last_image[19:16],6'h2b,last_image[15:0]};
endmodule
