`timescale 1ns/1ps
// A's integer-step sampler cannot make a 96x54 grid from arbitrary geometry.
// Reject that configuration at the capture boundary rather than committing a
// differently sized image under a 96x96 descriptor.
module tb_c2_video_config;
 reg clk=0,arst_n=1,vs=0,de=0;always #5 clk=~clk;
 wire cfg,frame,word_valid,source_valid,record_valid,record_complete;
 wire [31:0] frames,commits;
 c2_a_video_source #(.FRAME_WIDTH(1280),.FRAME_HEIGHT(720),.STEP_X(20),.STEP_Y(20)) dut(
 .arst_n(arst_n),.video_clk(clk),.enable(1'b1),
 .pixel_vs(vs),.pixel_de(de),.pixel_gray(8'hac),.shared_now_ms(32'd123),.shared_time_valid(1'b1),
 .capture_config_valid(cfg),.capture_record_valid(record_valid),.capture_record_complete(record_complete),
 .capture_record_frame_id(),.capture_record_timestamp_ms(),.capture_record_width(),.capture_record_height(),
 .capture_source_frames(frames),.capture_format_errors(),
 .v_frame_valid(frame),.v_frame_ready(1'b1),.v_descriptor(),
 .v_grant_valid(1'b0),.v_grant_ready(),.v_grant_frame_id(32'b0),
 .v_word_valid(word_valid),.v_word_ready(1'b1),.v_word_data(),
 .v_source_valid(source_valid),.v_source_ready(1'b1),.v_source_error(),.v_source_frame_id(),.v_source_fnv(),
 .v_event_valid(1'b0),.v_event_ready(),.v_event_status(3'b0),.v_event_descriptor(512'b0),
 .completed(),.rejected(),.source_faults(),.source_commits(commits),.source_drops(),.source_malformed(),
 .last_frame_id(),.last_sum32(),.last_fnv(),.last_status());
 integer n;
 initial begin
  #1;arst_n=0;#23;arst_n=1;
  for(n=0;n<1000;n=n+1) begin
   @(negedge clk);vs=(n%100)==0;de=(n%100)>3;
   if(cfg || frame || word_valid || source_valid || record_valid || record_complete || frames || commits)
    $fatal(1,"Unsupported source grid accepted");
  end
  $display("PASS tb_c2_video_config unsupported_geometry_held_in_reset no_false_frame_or_DDR_request");
  $finish;
 end
 initial begin #20000;$fatal(1,"Configuration guard timeout");end
endmodule
