`timescale 1ns / 1ps

// RGB/gray/binary display path with identical two-register latency.
// HS/VS continue during blanking. Active image dimensions are preserved.
module video_display_preprocess #(
    parameter integer MODE = 1, // 0=RGB, 1=gray, 2=binary
    parameter integer THRESHOLD = 128
) (
    input wire clk,
    input wire rst_n,
    input wire in_hs, in_vs, in_de,
    input wire [7:0] in_r, in_g, in_b,
    output wire out_hs, out_vs, out_de,
    output wire [7:0] out_r, out_g, out_b
);
    reg [1:0] hs_pipe, vs_pipe, de_pipe;
    reg [23:0] rgb0, rgb1;
    reg [7:0] gray1;
    wire gray_valid;
    wire [7:0] gray0, mask1;
    rgb888_to_gray gray_stage (
        .clk(clk), .rst_n(rst_n), .in_valid(in_de),
        .in_sof(1'b0), .in_sol(1'b0), .in_eol(1'b0), .in_eof(1'b0),
        .in_r(in_r), .in_g(in_g), .in_b(in_b),
        .out_valid(gray_valid), .out_gray(gray0),
        .out_sof(), .out_sol(), .out_eol(), .out_eof()
    );
    gray_threshold #(.THRESHOLD(THRESHOLD)) binary_stage (
        .clk(clk), .rst_n(rst_n), .in_valid(gray_valid),
        .in_sof(1'b0), .in_sol(1'b0), .in_eol(1'b0), .in_eof(1'b0),
        .in_gray(gray0), .out_mask(mask1),
        .out_valid(), .out_sof(), .out_sol(), .out_eol(), .out_eof()
    );
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hs_pipe <= 0;
            vs_pipe <= 0;
            de_pipe <= 0;
            rgb0 <= 0;
            rgb1 <= 0;
            gray1 <= 0;
        end else begin
            hs_pipe <= {hs_pipe[0], in_hs};
            vs_pipe <= {vs_pipe[0], in_vs};
            de_pipe <= {de_pipe[0], in_de};
            rgb0 <= {in_r, in_g, in_b};
            rgb1 <= rgb0;
            gray1 <= gray0;
        end
    end
    assign out_hs = hs_pipe[1];
    assign out_vs = vs_pipe[1];
    assign out_de = de_pipe[1];
    generate
        if (MODE == 0) begin : rgb_mode
            assign {out_r, out_g, out_b} = rgb1;
        end else if (MODE == 1) begin : gray_mode
            assign {out_r, out_g, out_b} = {gray1, gray1, gray1};
        end else begin : binary_mode
            assign {out_r, out_g, out_b} = {mask1, mask1, mask1};
        end
    endgenerate
endmodule
