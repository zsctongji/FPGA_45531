`timescale 1ns / 1ps

// Inclusive threshold: gray >= THRESHOLD produces 255, otherwise 0.
module gray_threshold #(
    parameter integer THRESHOLD = 128
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       in_valid,
    input  wire       in_sof,
    input  wire       in_sol,
    input  wire       in_eol,
    input  wire       in_eof,
    input  wire [7:0] in_gray,
    output reg        out_valid,
    output reg        out_sof,
    output reg        out_sol,
    output reg        out_eol,
    output reg        out_eof,
    output reg  [7:0] out_mask
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            out_sof   <= 1'b0;
            out_sol   <= 1'b0;
            out_eol   <= 1'b0;
            out_eof   <= 1'b0;
            out_mask  <= 8'd0;
        end else begin
            out_valid <= in_valid;
            out_sof   <= in_valid && in_sof;
            out_sol   <= in_valid && in_sol;
            out_eol   <= in_valid && in_eol;
            out_eof   <= in_valid && in_eof;
            if (in_valid)
                out_mask <= (in_gray >= THRESHOLD) ? 8'hff : 8'h00;
        end
    end
endmodule
