`timescale 1ns/1ps
// Source-clock GRAY8, one pixel/cycle, active-high VS rising in blanking.
// Physical MIPI unpacking/RGB-to-gray belongs upstream. Keep A's pinned capture
// and mailbox unchanged: timestamp is latched on the FIRST DE pixel, not on the
// registered grid SOF or the following VS which releases the delayed last pixel.
module c2_a_video_source #(
 parameter integer FRAME_WIDTH=1920,FRAME_HEIGHT=1080,STEP_X=20,STEP_Y=20
)(
 input wire arst_n,video_clk,enable,
 input wire pixel_vs,pixel_de,input wire [7:0] pixel_gray,
 input wire [31:0] shared_now_ms,input wire shared_time_valid,
 output wire capture_config_valid,
 output wire capture_record_valid,capture_record_complete,
 output wire [31:0] capture_record_frame_id,capture_record_timestamp_ms,
 output wire [15:0] capture_record_width,capture_record_height,
 output wire [31:0] capture_source_frames,capture_format_errors,
 output wire v_frame_valid,input wire v_frame_ready,output wire [511:0] v_descriptor,
 input wire v_grant_valid,output wire v_grant_ready,input wire [31:0] v_grant_frame_id,
 output wire v_word_valid,input wire v_word_ready,output wire [127:0] v_word_data,
 output wire v_source_valid,input wire v_source_ready,output wire v_source_error,
 output wire [31:0] v_source_frame_id,v_source_fnv,
 input wire v_event_valid,output wire v_event_ready,input wire [2:0] v_event_status,
 input wire [511:0] v_event_descriptor,
 output wire [31:0] completed,rejected,source_faults,source_commits,source_drops,source_malformed,
 output wire [31:0] last_frame_id,last_sum32,last_fnv,output wire [2:0] last_status
);
 localparam integer SAFE_STEP_X=STEP_X>0?STEP_X:1;
 localparam integer SAFE_STEP_Y=STEP_Y>0?STEP_Y:1;
 localparam CONFIG_OK=FRAME_WIDTH>0 && FRAME_WIDTH<=65535 && FRAME_HEIGHT>0 && FRAME_HEIGHT<=65535 &&
  STEP_X>0 && STEP_Y>0 && (FRAME_WIDTH+SAFE_STEP_X-1)/SAFE_STEP_X==96 &&
  (FRAME_HEIGHT+SAFE_STEP_Y-1)/SAFE_STEP_Y==54;
 assign capture_config_valid=CONFIG_OK;
 reg [1:0] released;
 always @(posedge video_clk or negedge arst_n)
  if(!arst_n) released<=0;else released<={released[0],1'b1};
 wire capture_rst_n=released[1] && shared_time_valid && CONFIG_OK;
 wire sample_valid,sample_sof,sample_eof,sample_abort;
 wire [7:0] sample_gray;wire [31:0] sample_frame_id,sample_timestamp_ms;
 video_a_capture #(.FRAME_WIDTH(FRAME_WIDTH),.FRAME_HEIGHT(FRAME_HEIGHT),
  .STEP_X(SAFE_STEP_X),.STEP_Y(SAFE_STEP_Y)) capture(
  .clk(video_clk),.rst_n(capture_rst_n),.in_vs(pixel_vs),.in_de(pixel_de),.in_gray(pixel_gray),
  .now_ms(shared_now_ms),.sample_valid(sample_valid),.sample_sof(sample_sof),
  .sample_eof(sample_eof),.sample_abort(sample_abort),.sample_gray(sample_gray),
  .sample_frame_id(sample_frame_id),.sample_timestamp_ms(sample_timestamp_ms),
  .record_valid(capture_record_valid),.record_complete(capture_record_complete),
  .record_frame_id(capture_record_frame_id),.record_timestamp_ms(capture_record_timestamp_ms),
  .record_width(capture_record_width),.record_height(capture_record_height),
  .source_frames(capture_source_frames),.format_errors(capture_format_errors));
 c2_a_image_source image(
  .arst_n(arst_n),.video_clk(video_clk),.enable(enable && shared_time_valid && CONFIG_OK),
  .sample_valid(sample_valid && capture_rst_n),.sample_sof(sample_sof),.sample_eof(sample_eof),
  .sample_abort(sample_abort || !capture_rst_n),.sample_gray(sample_gray),
  .sample_frame_id(sample_frame_id),.sample_timestamp_ms(sample_timestamp_ms),
  .v_frame_valid(v_frame_valid),.v_frame_ready(v_frame_ready),.v_descriptor(v_descriptor),
  .v_grant_valid(v_grant_valid),.v_grant_ready(v_grant_ready),.v_grant_frame_id(v_grant_frame_id),
  .v_word_valid(v_word_valid),.v_word_ready(v_word_ready),.v_word_data(v_word_data),
  .v_source_valid(v_source_valid),.v_source_ready(v_source_ready),.v_source_error(v_source_error),
  .v_source_frame_id(v_source_frame_id),.v_source_fnv(v_source_fnv),
  .v_event_valid(v_event_valid),.v_event_ready(v_event_ready),.v_event_status(v_event_status),
  .v_event_descriptor(v_event_descriptor),
  .completed(completed),.rejected(rejected),.source_faults(source_faults),
  .source_commits(source_commits),.source_drops(source_drops),.source_malformed(source_malformed),
  .last_frame_id(last_frame_id),.last_sum32(last_sum32),.last_fnv(last_fnv),.last_status(last_status));
endmodule
