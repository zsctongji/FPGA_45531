`timescale 1ns / 1ps
// Motion-only camera bring-up display. This does not instantiate AI or sensors.
// Gray input, single pixel clock; output controls and RGB have one register latency.
module video_motion_display #(
    parameter integer FRAME_WIDTH = 1920,
    parameter integer FRAME_HEIGHT = 1080,
    parameter integer STEP_X = 20,
    parameter integer STEP_Y = 20,
    parameter integer DIFF_THRESHOLD = 24,
    parameter integer MIN_CHANGED = 32,
    parameter integer HOLD_FRAMES = 15,
    parameter integer BORDER = 4
) (
    input wire clk, rst_n,
    input wire in_hs, in_vs, in_de,
    input wire [7:0] in_gray,
    output reg out_hs, out_vs, out_de,
    output reg [7:0] out_r, out_g, out_b,
    output wire stats_valid, comparison_valid, motion_detected, frame_error,
    output wire [31:0] changed_count,
    output wire motion_alarm
);
    wire sv, ss, se, sa;
    wire [7:0] sg;
    video_grid_sampler #(.FRAME_WIDTH(FRAME_WIDTH),.FRAME_HEIGHT(FRAME_HEIGHT),.STEP_X(STEP_X),.STEP_Y(STEP_Y)) sampler(
        .clk(clk),.rst_n(rst_n),.in_vs(in_vs),.in_de(in_de),.in_gray(in_gray),
        .sample_valid(sv),.sample_sof(ss),.sample_eof(se),.sample_abort(sa),.sample_gray(sg));
    frame_motion_stats #(.WIDTH((FRAME_WIDTH+STEP_X-1)/STEP_X),.HEIGHT((FRAME_HEIGHT+STEP_Y-1)/STEP_Y),
        .DIFF_THRESHOLD(DIFF_THRESHOLD),.MIN_CHANGED(MIN_CHANGED)) statistics(
        .clk(clk),.rst_n(rst_n),.in_valid(sv),.in_sof(ss),.in_eof(se),.in_abort(sa),.in_gray(sg),
        .out_valid(stats_valid),.comparison_valid(comparison_valid),.motion(motion_detected),.frame_error(frame_error),
        .changed_count(changed_count),.absolute_difference_sum(),.bbox_valid(),.min_x(),.min_y(),.max_x(),.max_y());
    reg vs_d, de_d;
    reg [15:0] x, y, hold_frames;
    wire new_vs = in_vs && !vs_d;
    assign motion_alarm = (hold_frames != 0);
    wire edge_pixel = x < BORDER || x >= FRAME_WIDTH-BORDER || y < BORDER || y >= FRAME_HEIGHT-BORDER;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vs_d <= 0; de_d <= 0; x <= 0; y <= 0; hold_frames <= 0;
            out_hs <= 0; out_vs <= 0; out_de <= 0; out_r <= 0; out_g <= 0; out_b <= 0;
        end else begin
            vs_d <= in_vs; de_d <= in_de;
            out_hs <= in_hs; out_vs <= in_vs; out_de <= in_de;
            if (in_de && motion_alarm && edge_pixel) begin out_r <= 255; out_g <= 0; out_b <= 0; end
            else begin out_r <= in_gray; out_g <= in_gray; out_b <= in_gray; end
            if (new_vs) begin x <= 0; y <= 0; end
            else if (in_de) x <= x + 1'b1;
            else if (de_d) begin x <= 0; y <= y + 1'b1; end
            if (new_vs && hold_frames != 0) hold_frames <= hold_frames - 1'b1;
            if (stats_valid && comparison_valid && motion_detected) hold_frames <= HOLD_FRAMES;
        end
    end
endmodule
