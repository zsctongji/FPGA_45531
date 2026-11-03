// Synthesis-only harness. All result ports are visible to retain useful logic.
module a_side_units(
    input wire clk,rst_n,vs,de,hs,
    input wire [7:0] gray,
    input wire [31:0] now_ms,
    input wire take,release_frame,read_req,
    input wire [15:0] address,
    input wire tv,ev,av,alarm,pv,
    input wire [7:0] person_score,event_score,event_type,heat_level,
    input wire signed [15:0] temperature_centi,
    input wire [15:0] humidity_centi,
    input wire [6:0] prediction_x,prediction_y,
    input wire [31:0] status_frame_id,display_frame_id,
    input wire heat_valid,
    output wire ready,active,bank,read_valid,read_error,
    output wire [7:0] data,
    output wire [31:0] frame_id,timestamp_ms,checksum,commits,drops,malformed,
    output wire record_valid,record_complete,
    output wire [31:0] source_frames,format_errors,record_frame_id,record_timestamp_ms,
    output wire [15:0] record_width,record_height,
    output wire oh,ov,od,heat_request,
    output wire [23:0] rgb,
    output wire [9:0] heat_address
);
    wire sv,ss,se,sa;
    wire [7:0] sample;
    wire [31:0] fid,stamp;
    video_a_capture capture(.clk(clk),.rst_n(rst_n),.in_vs(vs),.in_de(de),.in_gray(gray),.now_ms(now_ms),
        .sample_valid(sv),.sample_sof(ss),.sample_eof(se),.sample_abort(sa),.sample_gray(sample),
        .sample_frame_id(fid),.sample_timestamp_ms(stamp),.record_valid(record_valid),.record_complete(record_complete),
        .record_frame_id(record_frame_id),.record_timestamp_ms(record_timestamp_ms),.record_width(record_width),.record_height(record_height),
        .source_frames(source_frames),.format_errors(format_errors));
    ai_frame_mailbox mailbox(.clk(clk),.rst_n(rst_n),.sample_valid(sv),.sample_sof(ss),.sample_eof(se),.sample_abort(sa),.sample_gray(sample),
        .source_frame_id(fid),.source_timestamp_ms(stamp),.reader_take(take),.reader_release(release_frame),.read_req(read_req),.read_address(address),
        .frame_ready(ready),.reader_active(active),.reader_buffer(bank),.reader_frame_id(frame_id),.reader_timestamp_ms(timestamp_ms),.reader_checksum(checksum),
        .read_valid(read_valid),.read_error(read_error),.read_data(data),.committed_frames(commits),.dropped_frames(drops),.malformed_frames(malformed));
    video_status_overlay overlay(.clk(clk),.rst_n(rst_n),.in_hs(hs),.in_vs(vs),.in_de(de),.in_rgb({gray,gray,gray}),
        .thermal_valid(tv),.environment_valid(ev),.ai_valid(av),.alarm_active(alarm),.prediction_valid(pv),
        .person_score(person_score),.event_score(event_score),.event_type(event_type),.temperature_centi(temperature_centi),.humidity_centi(humidity_centi),
        .prediction_x(prediction_x),.prediction_y(prediction_y),.status_frame_id(status_frame_id),.display_frame_id(display_frame_id),
        .heat_pixel_valid(heat_valid),.heat_level(heat_level),.heat_address(heat_address),.heat_request(heat_request),
        .out_hs(oh),.out_vs(ov),.out_de(od),.out_rgb(rgb));
endmodule
