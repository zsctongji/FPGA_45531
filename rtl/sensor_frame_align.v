`timescale 1ns / 1ps

// Single-clock environment sample / video frame timestamp association.
// Timestamps are a shared unsigned 32-bit millisecond counter.
// MAX_AGE_MS must be less than 2^31. Inputs must already be in clk's domain.
module sensor_frame_align #(
    parameter [31:0] MAX_AGE_MS = 32'd1000
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        sample_valid,
    input  wire [31:0] sample_timestamp_ms,
    input  wire [15:0] sample_temp,
    input  wire [15:0] sample_humidity,
    input  wire        frame_valid,
    input  wire [31:0] frame_timestamp_ms,
    output reg         pair_valid,
    output reg         stale,
    output reg  [31:0] pair_frame_timestamp_ms,
    output reg  [31:0] pair_sample_timestamp_ms,
    output reg  [31:0] pair_age_ms,
    output reg  [15:0] pair_temp,
    output reg  [15:0] pair_humidity
);
    reg         sample_seen;
    reg  [31:0] latest_timestamp_ms;
    reg  [15:0] latest_temp;
    reg  [15:0] latest_humidity;

    // An update accepted on this edge takes precedence over the stored sample.
    wire        selected_seen = sample_valid | sample_seen;
    wire [31:0] selected_timestamp_ms = sample_valid ? sample_timestamp_ms : latest_timestamp_ms;
    wire [15:0] selected_temp = sample_valid ? sample_temp : latest_temp;
    wire [15:0] selected_humidity = sample_valid ? sample_humidity : latest_humidity;
    wire [31:0] selected_age_ms = frame_timestamp_ms - selected_timestamp_ms;
    // Reject a future timestamp and the exactly-half-range ambiguous difference.
    wire        selected_in_range = selected_seen && !selected_age_ms[31] &&
                                    (selected_age_ms <= MAX_AGE_MS);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sample_seen <= 1'b0;
            latest_timestamp_ms <= 32'd0;
            latest_temp <= 16'd0;
            latest_humidity <= 16'd0;
            pair_valid <= 1'b0;
            stale <= 1'b0;
            pair_frame_timestamp_ms <= 32'd0;
            pair_sample_timestamp_ms <= 32'd0;
            pair_age_ms <= 32'd0;
            pair_temp <= 16'd0;
            pair_humidity <= 16'd0;
        end else begin
            pair_valid <= 1'b0;
            stale <= 1'b0;
            if (sample_valid) begin
                sample_seen <= 1'b1;
                latest_timestamp_ms <= sample_timestamp_ms;
                latest_temp <= sample_temp;
                latest_humidity <= sample_humidity;
            end
            if (frame_valid) begin
                pair_frame_timestamp_ms <= frame_timestamp_ms;
                pair_valid <= selected_in_range;
                stale <= !selected_in_range;
                // A stale snapshot is diagnostic only; consumers must gate on pair_valid.
                if (selected_seen) begin
                    pair_sample_timestamp_ms <= selected_timestamp_ms;
                    pair_age_ms <= selected_age_ms;
                    pair_temp <= selected_temp;
                    pair_humidity <= selected_humidity;
                end else begin
                    pair_sample_timestamp_ms <= 32'd0;
                    pair_age_ms <= 32'd0;
                    pair_temp <= 16'd0;
                    pair_humidity <= 16'd0;
                end
            end
        end
    end
endmodule
