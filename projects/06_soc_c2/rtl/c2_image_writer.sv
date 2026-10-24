`timescale 1ns/1ps
// Memory-domain image writer: 9216 GRAY8 bytes in 576 full 128-bit words.
// One burst at a time (<=16 beats and never crosses 4 KiB). FNV is computed one
// byte per clock, intentionally sacrificing thumbnail throughput for a short
// combinational path. done_valid occurs only after the final write response.
module c2_image_writer(
 input wire clk,rst_n,
 input wire start_valid,output wire start_ready,input wire [31:0] start_address,
 input wire [127:0] pixel_words,input wire pixel_valid,output wire pixel_ready,
 output wire awvalid,input wire awready,output wire [31:0] awaddr,
 output wire [7:0] awlen,
 output wire wvalid,input wire wready,output wire [127:0] wdata,
 output wire [15:0] wstrb,output wire wlast,
 input wire bvalid,output wire bready,input wire [1:0] bresp,
 output reg done_valid,input wire done_ready,output reg done_error,
 output reg [31:0] done_checksum
);
 localparam IDLE=0,AW=1,CAPTURE=2,HASH=3,WRITE=4,RESPONSE=5,DONE=6,DRAIN=7;
 reg [2:0] state;
 reg [31:0] address,hash;
 reg [9:0] remaining;
 reg [4:0] burst_beats,beat;
 reg [3:0] hash_byte;
 reg [127:0] held;
 function [4:0] next_burst(input [9:0] rem_words,input [31:0] addr);
   integer page_words,n;
   begin
     page_words=(4096-(addr&4095))/16;
     n=(rem_words>16)?16:rem_words;
     if(n>page_words) n=page_words;
     next_burst=n[4:0];
   end
 endfunction
 assign start_ready=(state==IDLE);
 assign pixel_ready=(state==CAPTURE || state==DRAIN);
 assign awvalid=(state==AW);assign awaddr=address;assign awlen={3'b0,burst_beats}-8'd1;
 assign wvalid=(state==WRITE);assign wdata=held;assign wstrb=16'hffff;
 assign wlast=(beat==burst_beats-1);assign bready=(state==RESPONSE);
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin
     state<=IDLE;address<=0;hash<=0;remaining<=0;burst_beats<=0;
     beat<=0;hash_byte<=0;held<=0;done_valid<=0;done_error<=0;done_checksum<=0;
   end else case(state)
     IDLE: if(start_valid && start_ready) begin
       hash<=32'd2166136261;remaining<=576;address<=start_address;
       burst_beats<=next_burst(576,start_address);beat<=0;done_error<=0;
       if(start_address[3:0]!=0 || start_address>32'hffffdc00) begin
         done_error<=1;done_checksum<=0;state<=DRAIN;
       end else state<=AW;
     end
     AW: if(awvalid && awready) state<=CAPTURE;
     CAPTURE: if(pixel_valid && pixel_ready) begin held<=pixel_words;hash_byte<=0;state<=HASH;end
     HASH: begin
       hash<=(hash^{24'b0,held[hash_byte*8+:8]})*32'd16777619;
       if(hash_byte==15) state<=WRITE;else hash_byte<=hash_byte+4'd1;
     end
     WRITE: if(wvalid && wready) begin
       remaining<=remaining-10'd1;
       if(wlast) state<=RESPONSE;else begin beat<=beat+5'd1;state<=CAPTURE;end
     end
     RESPONSE: if(bvalid && bready) begin
       if(bresp!=0 && remaining!=0) begin
         // A granted source still owns an entire frame. Consume its remaining
         // words before reporting failure so the async FIFO cannot leak stale
         // pixels into the next frame. No more DDR writes are issued.
         done_error<=1;done_checksum<=0;state<=DRAIN;
       end else if(remaining==0) begin
         done_error<=(bresp!=0);done_checksum<=hash;done_valid<=1;state<=DONE;
       end else begin
         address<=address+burst_beats*16;
         burst_beats<=next_burst(remaining,address+burst_beats*16);beat<=0;state<=AW;
       end
     end
     DRAIN: if(pixel_valid && pixel_ready) begin
       remaining<=remaining-10'd1;
       if(remaining==1) begin done_valid<=1;state<=DONE;end
     end
     DONE: if(done_valid && done_ready) begin done_valid<=0;state<=IDLE;end
   endcase
 end
endmodule

