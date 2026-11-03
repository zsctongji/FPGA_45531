`timescale 1ns/1ps
// Bundled-data one-entry CDC mailbox. Common asynchronous reset MUST flush both
// domains; a unilateral reset is not supported. Physical CDC constraints/review
// are still required: data is held from request until acknowledged consumption.
module c2_cdc_mailbox #(parameter WIDTH=512)(
 input wire arst_n, s_clk, input wire s_valid, output wire s_ready,
 input wire [WIDTH-1:0] s_data,
 input wire d_clk, output wire d_valid, input wire d_ready,
 output wire [WIDTH-1:0] d_data
);
 reg [1:0] sr,dr;
 reg req,ack;
 (* async_reg="true" *) reg [1:0] ack_sync,req_sync;
 reg [WIDTH-1:0] held;
 always @(posedge s_clk or negedge arst_n)
   if(!arst_n) sr<=0; else sr<={sr[0],1'b1};
 always @(posedge d_clk or negedge arst_n)
   if(!arst_n) dr<=0; else dr<={dr[0],1'b1};
 assign s_ready=sr[1] && req==ack_sync[1];
 assign d_valid=dr[1] && req_sync[1]!=ack;
 assign d_data=held;
 always @(posedge s_clk or negedge arst_n) begin
   if(!arst_n) begin req<=0;held<=0;ack_sync<=0;end
   else begin
     ack_sync<={ack_sync[0],ack};
     if(s_valid && s_ready) begin held<=s_data;req<=~req;end
   end
 end
 always @(posedge d_clk or negedge arst_n) begin
   if(!arst_n) begin ack<=0;req_sync<=0;end
   else begin
     req_sync<={req_sync[0],req};
     if(d_valid && d_ready) ack<=req_sync[1];
   end
 end
endmodule

