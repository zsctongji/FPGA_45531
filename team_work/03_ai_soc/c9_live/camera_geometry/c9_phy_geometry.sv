`timescale 1ns/1ps
// Count actual CSI payload groups and valid runs inside HS. No data/control output.
module c9_phy_geometry(input wire clk,arst_n,hs,de,camera_fault,output wire [31:0] flags);
 reg hs_d,de_d,seen,outside_hs,clipped,last_clip;
 reg [9:0] groups,runs,last_groups,last_runs;
 always @(posedge clk or negedge arst_n) begin
  if(!arst_n)begin
   hs_d<=0;de_d<=0;seen<=0;outside_hs<=0;clipped<=0;last_clip<=0;
   groups<=0;runs<=0;last_groups<=0;last_runs<=0;
  end else begin
   hs_d<=hs;de_d<=de;
   if(de&&!hs)outside_hs<=1;
   if(hs&&!hs_d)begin groups<=de?1:0;runs<=de?1:0;clipped<=0;end
   else if(hs&&de)begin
    if(groups!=1023)groups<=groups+1'b1;else clipped<=1;
    if(!de_d)begin if(runs!=1023)runs<=runs+1'b1;else clipped<=1;end
   end
   if(!hs&&hs_d&&groups!=0)begin seen<=1;last_groups<=groups;last_runs<=runs;last_clip<=clipped;end
  end
 end
 assign flags={last_groups,last_runs,seen,last_clip,outside_hs,8'b0,camera_fault};
endmodule
