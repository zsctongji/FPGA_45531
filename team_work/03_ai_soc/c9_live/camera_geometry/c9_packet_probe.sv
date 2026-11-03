`timescale 1ns/1ps
// All observations belong to the native CSI pixel clock; no pixel output.
module c9_packet_probe(input wire clk,arst_n,vs,hs,de,fault,
 input wire [15:0] word_count,input wire [5:0] datatype,
 input wire [3:0] pixel_per_clk,input wire [1:0] vc,
 output wire [63:0] observation);
 reg vd,hd,meta_seen,meta_changed,outside_hs,frame_seen;
 reg [27:0] metadata;
 reg [11:0] vs_count,hs_count,last_hs;
 reg vs_clip,hs_clip,last_clip;
 wire [27:0] current_meta={vc,pixel_per_clk,datatype,word_count};
 always @(posedge clk or negedge arst_n)begin
  if(!arst_n)begin
   vd<=0;hd<=0;meta_seen<=0;meta_changed<=0;outside_hs<=0;frame_seen<=0;metadata<=0;
   vs_count<=0;hs_count<=0;last_hs<=0;vs_clip<=0;hs_clip<=0;last_clip<=0;
  end else begin
   vd<=vs;hd<=hs;
   if(de)begin
    if(meta_seen&&metadata!=current_meta)meta_changed<=1;
    metadata<=current_meta;meta_seen<=1;if(!hs)outside_hs<=1;
   end
   if(vs&&!vd)begin
    if(vs_count!=4095)vs_count<=vs_count+1'b1;else vs_clip<=1;
    if(vs_count!=0)frame_seen<=1;
    // An HS rising on the VS boundary belongs to the new interval.
    last_hs<=hs_count;last_clip<=hs_clip;hs_count<=(hs&&!hd)?1:0;hs_clip<=0;
   end else if(hs&&!hd)begin
    if(hs_count!=4095)hs_count<=hs_count+1'b1;else hs_clip<=1;
   end
  end
 end
 wire [31:0] packet={meta_seen,meta_changed,outside_hs,fault,metadata};
 wire [31:0] edges={vs_count,last_hs,vs,hs,de,frame_seen,vs_clip,last_clip,1'b0,1'b1};
 assign observation={edges,packet};
endmodule
