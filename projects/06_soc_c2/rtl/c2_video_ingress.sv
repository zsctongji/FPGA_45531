`timescale 1ns/1ps
// Non-backpressurable GRAY8 source -> framed 128-bit stream. Tokens:
// START=1 {timestamp,id}, DATA=0 (little-endian pixels), END=2 {bad,id}.
// A's next-VS source record is the physical-frame completion authority.
module c2_video_ingress #(
 parameter integer WIDTH=1920,HEIGHT=1080,FIFO_BITS=6
)(
 input wire arst_n,video_clk,mem_clk,enable,time_valid,
 input wire vs,de,input wire [7:0] gray,input wire [31:0] now_ms,source_frames,
 input wire record_valid,record_complete,input wire [31:0] record_id,record_ms,
 output wire valid,input wire ready,output wire [129:0] data,
 output reg [31:0] overflow_frames
);
 reg vs_d,de_d,armed,active,bad,pending,end_pending;
 reg [31:0] id,stamp,x,y;
 reg [127:0] pack;
 reg [129:0] queued,end_token;
 wire room;
 wire slot=!pending || room;
 c2_async_fifo #(.WIDTH(130),.ADDR_BITS(FIFO_BITS)) crossing(
  .arst_n(arst_n),.s_clk(video_clk),.s_valid(pending),.s_ready(room),.s_data(queued),
  .d_clk(mem_clk),.d_valid(valid),.d_ready(ready),.d_data(data));
 always @(posedge video_clk or negedge arst_n) begin
  if(!arst_n) begin
   vs_d<=0;de_d<=0;armed<=0;active<=0;bad<=0;pending<=0;end_pending<=0;
   id<=0;stamp<=0;x<=0;y<=0;pack<=0;queued<=0;end_token<=0;overflow_frames<=0;
  end else begin
   vs_d<=vs;de_d<=de;
   if(pending && room) pending<=0;
   if(vs && !vs_d) armed<=enable && time_valid;
   if(de && !de_d && armed) armed<=0;
   if(end_pending && slot) begin queued<=end_token;pending<=1;end_pending<=0;end
   if(record_valid && active && record_id==id) begin
    end_pending<=1;active<=0;
    end_token<={2'd2,95'b0,(!record_complete || bad || stamp!=record_ms || x!=0 || y!=HEIGHT),id};
   end
   if(de && !de_d && !vs && armed && !active && !end_pending && !record_valid) begin
    // No backpressure to the sensor: if START cannot be queued, skip this frame.
    armed<=0;x<=1;y<=0;pack<={120'b0,gray};id<=source_frames-1'b1;stamp<=now_ms;bad<=0;
    if(slot && enable && time_valid) begin
     active<=1;queued<={2'd1,64'b0,now_ms,source_frames-1'b1};pending<=1;
    end else overflow_frames<=overflow_frames+1'b1;
   end else if(active && !record_valid && !(vs && !vs_d)) begin
    if(de) begin
     x<=x+1'b1;
     if(x>=WIDTH || y>=HEIGHT) bad<=1;
     if(!bad && x<WIDTH && y<HEIGHT) begin
      pack[x[3:0]*8+:8]<=gray;
      if(x[3:0]==15 || x==WIDTH-1) begin
       if(slot && !end_pending) begin
        queued<={2'd0,(pack & ~(128'hff << (x[3:0]*8))) | (128'(gray) << (x[3:0]*8))};
        pending<=1;pack<=0;
       end else begin bad<=1;overflow_frames<=overflow_frames+1'b1;end
      end
     end
    end else if(de_d) begin x<=0;y<=y+1'b1;if(x!=WIDTH) bad<=1;end
   end
  end
 end
endmodule
