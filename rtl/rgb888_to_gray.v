`timescale 1ns / 1ps

// Portable, one-register-stage RGB888 to 8-bit luma approximation.
// A pixel is accepted on each rising edge with in_valid = 1.
module rgb888_to_gray (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       in_valid,
    input  wire       in_sof,
    input  wire       in_sol,
    input  wire       in_eol,
    input  wire       in_eof,
    input  wire [7:0] in_r,
    input  wire [7:0] in_g,
    input  wire [7:0] in_b,
    output reg        out_valid,
    output reg        out_sof,
    output reg        out_sol,
    output reg        out_eol,
    output reg        out_eof,
    output reg  [7:0] out_gray
);
    // The shifts use 16-bit operands. The maximum rounded sum is 65408.
    wire [15:0] r16 = {8'b0, in_r};
    wire [15:0] g16 = {8'b0, in_g};
    wire [15:0] b16 = {8'b0, in_b};
    wire [15:0] r77 = (r16 << 6) + (r16 << 3) + (r16 << 2) + r16;
    wire [15:0] g150 = (g16 << 7) + (g16 << 4) + (g16 << 2) + (g16 << 1);
    wire [15:0] b29 = (b16 << 4) + (b16 << 3) + (b16 << 2) + b16;
    wire [15:0] rounded_sum = r77 + g150 + b29 + 16'd128;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            out_sof   <= 1'b0;
            out_sol   <= 1'b0;
            out_eol   <= 1'b0;
            out_eof   <= 1'b0;
            out_gray  <= 8'd0;
        end else begin
            out_valid <= in_valid;
            out_sof   <= in_valid && in_sof;
            out_sol   <= in_valid && in_sol;
            out_eol   <= in_valid && in_eol;
            out_eof   <= in_valid && in_eof;
            if (in_valid)
                out_gray <= rounded_sum[15:8];
        end
    end
endmodule
