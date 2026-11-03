`timescale 1ns/1ps
// Diagnostic-only extension of source_flags. All inputs share video_clk.
// Measurements are from the existing capture record, including rejected frames.
module c9_capture_geometry(
 input wire clk,arst_n,record_valid,record_complete,
 input wire [15:0] record_width,record_height,
 input wire [3:0] source_flags,
 output wire [31:0] flags
);
 reg seen;
 always @(posedge clk or negedge arst_n)
  if(!arst_n)seen<=0;else if(record_valid)seen<=1;
 wire width_clip=|record_width[15:12];
 wire height_clip=|record_height[15:12];
 assign flags={width_clip?12'hfff:record_width[11:0],
               height_clip?12'hfff:record_height[11:0],
               seen,record_complete,width_clip,height_clip,source_flags};
endmodule
