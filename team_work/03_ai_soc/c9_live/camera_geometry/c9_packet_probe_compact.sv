`timescale 1ns/1ps
// Compact packet observer. Edge counters are modulo 16, not frame geometry.
module c9_packet_probe(input wire clk,arst_n,vs,hs,de,fault,
 input wire [15:0] word_count,input wire [5:0] datatype,
 input wire [3:0] pixel_per_clk,input wire [1:0] vc,output wire [63:0] observation);
 reg vd,hd,seen;reg [3:0] vcount,hcount;reg [27:0] metadata;
 always @(posedge clk or negedge arst_n)begin
  if(!arst_n)begin vd<=0;hd<=0;seen<=0;vcount<=0;hcount<=0;metadata<=0;end
  else begin
   vd<=vs;hd<=hs;
   if(vs&&!vd)vcount<=vcount+1'b1;
   if(hs&&!hd)hcount<=hcount+1'b1;
   if(de)begin metadata<={vc,pixel_per_clk,datatype,word_count};seen<=1;end
  end
 end
 assign observation={16'hc9c2,8'b0,vcount,hcount,seen,vs,hs,fault,metadata};
endmodule
