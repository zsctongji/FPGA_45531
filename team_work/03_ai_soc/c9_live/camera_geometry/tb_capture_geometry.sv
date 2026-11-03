`timescale 1ns/1ps
module tb_capture_geometry;
 reg clk=0,rst=0,vs=0,de=0;
 always #5 clk=~clk;
 wire rv,rc;wire [15:0] rw,rh;wire [31:0] errors,frames,flags;
 video_a_capture #(.FRAME_WIDTH(32),.FRAME_HEIGHT(8),.STEP_X(1),.STEP_Y(1)) capture(
  .clk(clk),.rst_n(rst),.in_vs(vs),.in_de(de),.in_gray(8'h80),.now_ms(32'd123),
  .sample_valid(),.sample_sof(),.sample_eof(),.sample_abort(),.sample_gray(),
  .sample_frame_id(),.sample_timestamp_ms(),.record_valid(rv),.record_complete(rc),
  .record_frame_id(),.record_timestamp_ms(),.record_width(rw),.record_height(rh),
  .source_frames(frames),.format_errors(errors));
 c9_capture_geometry obs(clk,rst,rv,rc,rw,rh,4'ha,flags);
 // Independent range test verifies that clipping cannot look like a real size.
 reg [15:0] wide=0,high=0;wire [31:0] clipped;
 c9_capture_geometry range_check(clk,rst,rv,rc,wide,high,4'h5,clipped);
 task boundary;begin vs=1;repeat(3)@(negedge clk);vs=0;repeat(3)@(negedge clk);end endtask
 task line(input integer width);begin de=1;repeat(width)@(negedge clk);de=0;repeat(4)@(negedge clk);end endtask
 task verify(input integer width,height,complete,errs);begin
  boundary();
  if(flags[31:20]!=width || flags[19:8]!=height || flags[7]!=1 || flags[6]!=complete || flags[5:4]!=0 || flags[3:0]!=10 || errors!=errs)
   $fatal(1,"geometry width=%0d height=%0d complete=%0d errors=%0d flags=%h",rw,rh,rc,errors,flags);
 end endtask
 integer y;
 initial begin
  #1;rst=0;repeat(4)@(negedge clk);rst=1;repeat(4)@(negedge clk);
  if(flags!==32'ha)$fatal(1,"reset flags");
  boundary();for(y=0;y<8;y=y+1)line(32);verify(32,8,1,0);
  // Same pixel count, but each physical line has a valid-data gap.
  for(y=0;y<8;y=y+1)begin line(16);line(16);end
  verify(16,16,0,1);
  for(y=0;y<8;y=y+1)line(24);verify(24,8,0,2);
  for(y=0;y<7;y=y+1)line(32);verify(32,7,0,3);
  wide=16'h1000;high=16'hffff;#1;
  if(clipped[31:20]!=4095 || clipped[19:8]!=4095 || clipped[5:4]!=3 || clipped[3:0]!=5)$fatal(1,"range clipping");
  rst=0;#1;if(flags[7]!==0)$fatal(1,"seen reset");
  $display("PASS tb_capture_geometry good fragmented cropped missing_line saturation reset low_flags_preserved");$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
