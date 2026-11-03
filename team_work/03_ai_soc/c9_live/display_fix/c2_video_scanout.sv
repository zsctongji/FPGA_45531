`timescale 1ns/1ps
// Raster comes from A's HDMI timing domain. One GRAY8 pixel per active DE.
// VS must rise in blanking. On starvation black the remainder of the scan,
// drain that frame, and only request a fresh frame on a later VS while idle.
module c2_video_scanout #(parameter integer WIDTH=1920,HEIGHT=1080)(
 input wire arst_n,clk,vs,de,hs,
 output reg scan_valid,input wire scan_ready,
 input wire in_valid,output wire in_ready,input wire [129:0] in_data,
 output reg [23:0] rgb,output reg out_vs,out_de,out_hs,
 output reg busy,frame_available,frame_failed,
 output reg [31:0] frame_id,timestamp_ms,underflows,missed_scans,completed_scans
);
 reg vs_d,have_word,drain,header;
 // Ignore reset-release VS until the request mailbox has initialized once.
 // After readiness has been observed, genuine busy/backpressure misses count.
 reg scan_initialized;
 reg [127:0] word_data;
 reg [3:0] lane;
 reg [31:0] x,y;
 wire [1:0] kind=in_data[129:128];
 wire bypass=in_valid && in_ready && kind==0;
 wire [127:0] pixels=have_word?word_data:in_data[127:0];
 wire [3:0] pixel_lane=have_word?lane:4'd0;
 assign in_ready=busy && (drain || !have_word);
 always @(posedge clk or negedge arst_n) begin
  if(!arst_n) begin
   scan_initialized<=0;vs_d<=0;have_word<=0;drain<=0;header<=0;word_data<=0;lane<=0;x<=0;y<=0;
   scan_valid<=0;rgb<=0;out_vs<=0;out_de<=0;out_hs<=0;busy<=0;frame_available<=0;frame_failed<=0;
   frame_id<=0;timestamp_ms<=0;underflows<=0;missed_scans<=0;completed_scans<=0;
  end else begin
   if(scan_ready) scan_initialized<=1;
   vs_d<=vs;rgb<=0;out_vs<=vs;out_de<=de;out_hs<=hs;
   if(scan_valid && scan_ready) scan_valid<=0;
   if((scan_initialized || scan_ready) && vs && !vs_d) begin
    if(!busy && !scan_valid && scan_ready) begin
     scan_valid<=1;busy<=1;drain<=0;header<=0;have_word<=0;lane<=0;x<=0;y<=0;
     frame_available<=0;frame_failed<=0;
    end else begin
     missed_scans<=missed_scans+1'b1;
     if(busy) begin frame_failed<=1;drain<=1;have_word<=0;end
    end
   end
   if(in_valid && in_ready) begin
    case(kind)
     1:begin header<=1;frame_available<=in_data[64];frame_id<=in_data[31:0];timestamp_ms<=in_data[63:32];end
     0:if(!drain) begin word_data<=in_data[127:0];have_word<=1;lane<=0;end
     3:begin frame_failed<=1;drain<=1;have_word<=0;end
     2:begin
      busy<=0;have_word<=0;
      if(in_data[0]) frame_failed<=1;
      if(frame_available && !frame_failed && !in_data[0] && y==HEIGHT) completed_scans<=completed_scans+1'b1;
     end
     default:begin end
    endcase
   end
   if(de && !vs && busy && !drain) begin
    if(header && !frame_available) begin drain<=1;have_word<=0;end
    else if(!header || (!have_word && !bypass) || y>=HEIGHT) begin
     underflows<=underflows+1'b1;frame_failed<=1;drain<=1;have_word<=0;
    end else begin
     rgb<={3{pixels[pixel_lane*8+:8]}};
     if(x==WIDTH-1) begin x<=0;y<=y+1'b1;have_word<=0;lane<=0;end
     else begin
      x<=x+1'b1;
      if(pixel_lane==15) begin lane<=0;have_word<=0;end else lane<=pixel_lane+1'b1;
     end
    end
   end
  end
 end
endmodule
