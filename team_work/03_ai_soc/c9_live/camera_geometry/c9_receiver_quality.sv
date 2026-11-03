`timescale 1ns/1ps
// No payload is released while PHY status is unqualified. A byte-clock error
// status may outlive the transaction when that clock stops. Require 32 clean
// native cycles after natural frame arm; any later PHY error remains fatal.
module c9_receiver_quality(input wire clk,arst_n,enable,frame_armed,de,
 input wire [31:0] debug,output wire transport_fault,output wire release_ok,
 output wire [3:0] flags);
 reg [5:0] clean_count;reg clean,pre_error,active_error,level_in_data;
 wire phy_bad=|debug[18:16];
 always @(posedge clk or negedge arst_n)
  if(!arst_n)begin clean_count<=0;clean<=0;pre_error<=0;active_error<=0;level_in_data<=0;end
  else if(!enable)begin clean_count<=0;clean<=0;pre_error<=0;active_error<=0;level_in_data<=0;end
  else begin
   if(phy_bad && !clean)pre_error<=1;
   if(phy_bad && clean)active_error<=1;
   if(phy_bad && de)level_in_data<=1;
   if(!clean)begin
    if(!frame_armed || phy_bad)clean_count<=0;
    else if(clean_count==31)clean<=1;
    else clean_count<=clean_count+1'b1;
   end
  end
 assign release_ok=enable && clean;
 assign transport_fault=!debug[15] || |(debug & 32'h0000447d) || (clean && phy_bad) || active_error;
 assign flags={level_in_data,clean,active_error,pre_error};
endmodule
