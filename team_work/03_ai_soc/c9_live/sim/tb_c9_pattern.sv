`timescale 1ns/1ps
module tb_c9_pattern;
 reg clk=0,rst=0,valid=0;always #5 clk=~clk;
 reg [7:0] seed=8'h3c;wire ready,vs,de,busy;wire [7:0] gray;wire [31:0] completed;
 c9_pattern_source #(.WIDTH(192),.HEIGHT(108),.HTOTAL(224)) gen(.clk(clk),.arst_n(rst),.command_valid(valid),.command_ready(ready),.command_gray(seed),.vs(vs),.de(de),.gray(gray),.completed(completed),.busy(busy));
 wire sv,sof,eof,abort,rv,rc;wire [7:0] sg;wire [31:0] source_frames,errors;wire [15:0] rw,rh;
 video_a_capture #(.FRAME_WIDTH(192),.FRAME_HEIGHT(108),.STEP_X(2),.STEP_Y(2)) capture(.clk(clk),.rst_n(rst),.in_vs(vs),.in_de(de),.in_gray(gray),.now_ms(32'd123),.sample_valid(sv),.sample_sof(sof),.sample_eof(eof),.sample_abort(abort),.sample_gray(sg),.sample_frame_id(),.sample_timestamp_ms(),.record_valid(rv),.record_complete(rc),.record_frame_id(),.record_timestamp_ms(),.record_width(rw),.record_height(rh),.source_frames(source_frames),.format_errors(errors));
 integer pixels=0,samples=0,records=0,ends=0;
 always @(posedge clk)if(rst)begin
  if(de)pixels=pixels+1;
  if(abort)$fatal(1,"Synthetic source aborted real A sampler");
  if(sv)begin samples=samples+1;if(sg!==seed)$fatal(1,"Wrong sample gray");end
  if(eof)ends=ends+1;
  if(rv)begin if(!rc || rw!=192 || rh!=108)$fatal(1,"Incomplete source record");records=records+1;end
 end
 task frame(input [7:0] value);
 begin @(negedge clk);seed=value;valid=1;while(!ready)@(negedge clk);@(negedge clk);valid=0;while(busy)@(negedge clk);repeat(20)@(negedge clk);end
 endtask
 initial begin
  #1;rst=0;repeat(4)@(negedge clk);rst=1;repeat(5)@(negedge clk);
  frame(8'h3c);frame(8'hc3);
  if(pixels!=2*192*108 || samples!=2*5184 || records!=2 || ends!=2 || errors!=0 || completed!=2)$fatal(1,"Counts pixels=%0d samples=%0d records=%0d ends=%0d errors=%0d",pixels,samples,records,ends,errors);
  $display("PASS c9_pattern real_A_capture frames=2 samples=10368 closing_VS seeds_3c_c3 no_empty_frame");$finish;
 end
 initial begin #2000000;$fatal(1,"Timeout");end
endmodule
