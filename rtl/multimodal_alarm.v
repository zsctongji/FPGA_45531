`timescale 1ns / 1ps
// All inputs must be synchronized snapshots in this clock domain.
// Scores 0..255 are upstream evidence, NOT raw degrees, humidity or calibrated probabilities.
// Example policy: armed motion + person + thermal evidence, confirmed on distinct frames.
module multimodal_alarm #(
    parameter [31:0] VISUAL_MAX_AGE_MS = 1000,
    parameter [31:0] THERMAL_MAX_AGE_MS = 500,
    parameter [31:0] ENV_MAX_AGE_MS = 2000,
    parameter [31:0] HOLD_MS = 2000,
    parameter integer CONFIRM_FRAMES = 2,
    parameter integer SCORE_THRESHOLD = 160
) (
    input wire clk, rst_n,
    input wire [31:0] now_ms,
    input wire snapshot_valid, armed, acknowledge,
    input wire visual_valid, thermal_valid, environment_valid,
    input wire [31:0] visual_timestamp_ms, thermal_timestamp_ms, environment_timestamp_ms,
    input wire [7:0] visual_score, thermal_score, environment_score,
    input wire motion_detected, person_detected, thermal_presence,
    output reg result_valid, data_fault, duplicate_frame,
    output reg [7:0] fused_score,
    output reg alarm_active, event_valid,
    output wire [3:0] alarm_type,
    output reg [7:0] alarm_confidence,
    output reg [31:0] event_timestamp_ms,
    output wire led_request, buzzer_request, red_border_request
);
    wire [31:0] visual_age = now_ms - visual_timestamp_ms;
    wire [31:0] thermal_age = now_ms - thermal_timestamp_ms;
    wire [31:0] environment_age = now_ms - environment_timestamp_ms;
    wire fresh = visual_valid && thermal_valid && environment_valid &&
        !visual_age[31] && visual_age <= VISUAL_MAX_AGE_MS &&
        !thermal_age[31] && thermal_age <= THERMAL_MAX_AGE_MS &&
        !environment_age[31] && environment_age <= ENV_MAX_AGE_MS;
    reg seen_frame;
    reg [31:0] last_frame_ms, last_trigger_ms;
    reg [15:0] consecutive;
    wire [31:0] frame_delta = visual_timestamp_ms - last_frame_ms;
    wire ordered_frame = !seen_frame || (frame_delta != 0 && !frame_delta[31]);
    wire adjacent_frame = seen_frame && !frame_delta[31] && frame_delta <= VISUAL_MAX_AGE_MS;
    wire [15:0] weighted_score = 16'd60 * visual_score + 16'd25 * thermal_score + 16'd15 * environment_score;
    wire [7:0] score = weighted_score / 100;
    wire candidate = armed && motion_detected && person_detected && thermal_presence && (score >= SCORE_THRESHOLD);
    wire [31:0] hold_age = now_ms - last_trigger_ms;
    assign led_request = alarm_active;
    assign buzzer_request = alarm_active; // Enable request; board-specific tone PWM is separate.
    assign red_border_request = alarm_active;
    assign alarm_type = alarm_active ? 4'd1 : 4'd0; // 1 = armed motion/person/thermal presence.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            seen_frame <= 0; last_frame_ms <= 0; last_trigger_ms <= 0; consecutive <= 0;
            result_valid <= 0; data_fault <= 0; duplicate_frame <= 0; fused_score <= 0;
            alarm_active <= 0; event_valid <= 0;
            alarm_confidence <= 0; event_timestamp_ms <= 0;
        end else begin
            result_valid <= 0; data_fault <= 0; duplicate_frame <= 0; event_valid <= 0;
            if (alarm_active && !hold_age[31] && hold_age >= HOLD_MS) begin alarm_active <= 0; alarm_confidence <= 0; end
            if (!armed || acknowledge) begin
                alarm_active <= 0; consecutive <= 0; alarm_confidence <= 0;
                // Consume acknowledged snapshots so repeated cached data cannot re-arm.
                if (snapshot_valid && fresh && ordered_frame) begin
                    seen_frame <= 1; last_frame_ms <= visual_timestamp_ms;
                end
            end else if (snapshot_valid) begin
                if (!fresh) begin data_fault <= 1; consecutive <= 0; end
                else if (!ordered_frame) duplicate_frame <= 1;
                else begin
                    seen_frame <= 1; last_frame_ms <= visual_timestamp_ms;
                    result_valid <= 1; fused_score <= score;
                    if (candidate) begin
                        if (!adjacent_frame) consecutive <= 1;
                        else if (consecutive < CONFIRM_FRAMES) consecutive <= consecutive + 1'b1;
                        if (CONFIRM_FRAMES == 1 || (adjacent_frame && consecutive >= CONFIRM_FRAMES-1)) begin
                            alarm_active <= 1; last_trigger_ms <= now_ms;
                            alarm_confidence <= score;
                            if (!alarm_active || (!hold_age[31] && hold_age >= HOLD_MS)) begin
                                event_valid <= 1; event_timestamp_ms <= now_ms;
                            end
                        end
                    end else consecutive <= 0;
                end
            end
        end
    end
endmodule
