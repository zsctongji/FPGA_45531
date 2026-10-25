`timescale 1ns/1ps
// A's pinned 96x54 sample output is the input boundary. Real MIPI packing and
// the shared now_ms source remain outside this module.
module c2_a_image_source(
 input wire arst_n,video_clk,enable,
 input wire sample_valid,sample_sof,sample_eof,sample_abort,input wire [7:0] sample_gray,
 input wire [31:0] sample_frame_id,sample_timestamp_ms,
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
 reg [1:0] release_reset;
 always @(posedge video_clk or negedge arst_n)
  if(!arst_n) release_reset<=0;else release_reset<={release_reset[0],1'b1};
 wire rst_n=release_reset[1];
 wire ready,active,bank,take,release_frame,read_req,read_valid,read_error;
 wire [15:0] address;wire [7:0] data;wire [31:0] frame_id,timestamp_ms,sum32;
 ai_frame_mailbox mailbox(.clk(video_clk),.rst_n(rst_n),
  .sample_valid(sample_valid),.sample_sof(sample_sof),.sample_eof(sample_eof),.sample_abort(sample_abort),
  .sample_gray(sample_gray),.source_frame_id(sample_frame_id),.source_timestamp_ms(sample_timestamp_ms),
  .reader_take(take),.reader_release(release_frame),.read_req(read_req),.read_address(address),
  .frame_ready(ready),.reader_active(active),.reader_buffer(bank),.reader_frame_id(frame_id),
  .reader_timestamp_ms(timestamp_ms),.reader_checksum(sum32),.read_valid(read_valid),.read_error(read_error),
  .read_data(data),.committed_frames(source_commits),.dropped_frames(source_drops),.malformed_frames(source_malformed));
 c2_a_mailbox_bridge bridge(.clk(video_clk),.rst_n(rst_n),.enable(enable),
  .a_ready(ready),.a_active(active),.a_frame_id(frame_id),.a_timestamp_ms(timestamp_ms),.a_sum32(sum32),
  .a_take(take),.a_release(release_frame),.a_read_req(read_req),.a_read_address(address),
  .a_read_valid(read_valid),.a_read_error(read_error),.a_read_data(data),
  .v_frame_valid(v_frame_valid),.v_frame_ready(v_frame_ready),.v_descriptor(v_descriptor),
  .v_grant_valid(v_grant_valid),.v_grant_ready(v_grant_ready),.v_grant_frame_id(v_grant_frame_id),
  .v_word_valid(v_word_valid),.v_word_ready(v_word_ready),.v_word_data(v_word_data),
  .v_source_valid(v_source_valid),.v_source_ready(v_source_ready),.v_source_error(v_source_error),
  .v_source_frame_id(v_source_frame_id),.v_source_fnv(v_source_fnv),
  .v_event_valid(v_event_valid),.v_event_ready(v_event_ready),.v_event_status(v_event_status),.v_event_descriptor(v_event_descriptor),
  .completed(completed),.rejected(rejected),.source_faults(source_faults),
  .last_frame_id(last_frame_id),.last_sum32(last_sum32),.last_fnv(last_fnv),.last_status(last_status));
endmodule
