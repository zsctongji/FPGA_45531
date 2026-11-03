`timescale 1ns/1ps
// Pixel-domain image PPC categories. Values above RAW10 maximum are flagged.
module c9_sideband_probe(input wire clk,arst_n,run_async,hs,de,fault,
 input wire [15:0] pixel_wordcount,input wire [5:0] pixel_datatype,
 input wire [3:0] pixel_per_clk,input wire [1:0] pixel_vc,output wire [63:0] observation);
 (* async_reg="true" *) reg run1,run2;
 reg other_seen,outside_hs,bad_ppc;reg [4:0] ppc_mask;reg [15:0] last_wc;
 always @(posedge clk or negedge arst_n)
  if(!arst_n)begin run1<=0;run2<=0;end else begin run1<=run_async;run2<=run1;end
 always @(posedge clk or negedge arst_n)begin
  if(!arst_n)begin other_seen<=0;outside_hs<=0;bad_ppc<=0;ppc_mask<=0;last_wc<=0;end
  else if(!run2)begin other_seen<=0;outside_hs<=0;bad_ppc<=0;ppc_mask<=0;last_wc<=0;end
  else if(de)begin
   if(pixel_datatype==6'h2b && pixel_vc==0)begin
    last_wc<=pixel_wordcount;if(!hs)outside_hs<=1;
    case(pixel_per_clk)
     0:ppc_mask[0]<=1;1:ppc_mask[1]<=1;2:ppc_mask[2]<=1;3:ppc_mask[3]<=1;4:ppc_mask[4]<=1;
     default:bad_ppc<=1;
    endcase
   end else other_seen<=1;
  end
 end
 assign observation={16'hc9d2,bad_ppc,10'b0,ppc_mask,(|ppc_mask)||bad_ppc,other_seen,outside_hs,fault,2'b0,4'b0,6'h2b,last_wc};
endmodule
