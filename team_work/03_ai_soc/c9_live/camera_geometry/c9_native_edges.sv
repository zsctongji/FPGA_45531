`timescale 1ns/1ps
module c9_native_edges(input wire clk,arst_n,enable,vs,hs,de,
 input wire [5:0] datatype,input wire [1:0] vc,input wire [3:0] ppc,input wire [15:0] wc,
 output wire [31:0] counts,output wire [7:0] flags);
 reg vs_d;reg [15:0] rises,falls;reg [5:0] seen;
 always @(posedge clk or negedge arst_n)
  if(!arst_n)begin vs_d<=0;rises<=0;falls<=0;seen<=0;end
  else begin
   vs_d<=vs;
   if(!enable)begin rises<=0;falls<=0;seen<=0;end
   else begin
    if(vs && !vs_d && !(&rises))rises<=rises+1'b1;
    if(!vs && vs_d && !(&falls))falls<=falls+1'b1;
    if(de)seen[0]<=1;if(hs)seen[1]<=1;if(vs)seen[2]<=1;
    if(de && datatype==6'h2b && vc==0)begin
     seen[3]<=1;if(ppc!=4)seen[4]<=1;if(wc!=2400)seen[5]<=1;
    end
   end
  end
 assign counts={falls,rises};assign flags={vs,hs,seen};
endmodule
