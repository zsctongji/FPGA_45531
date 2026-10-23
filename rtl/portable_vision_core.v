`timescale 1ns / 1ps

// Board-independent visual preprocessing example. This is not a camera,
// HDMI, memory-controller, AI inference, or complete contest implementation.
module portable_vision_core #(
    parameter integer WIDTH = 640,
    parameter integer HEIGHT = 480,
    parameter integer THRESHOLD = 128,
    parameter integer EDGE_THRESHOLD = 80
) (
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
    output wire       gray_valid,
    output wire       gray_sof,
    output wire       gray_sol,
    output wire       gray_eol,
    output wire       gray_eof,
    output wire [7:0] gray_pixel,
    output wire       binary_valid,
    output wire       binary_sof,
    output wire       binary_sol,
    output wire       binary_eol,
    output wire       binary_eof,
    output wire [7:0] binary_pixel,
    output wire       edge_valid,
    output wire       edge_sof,
    output wire       edge_sol,
    output wire       edge_eol,
    output wire       edge_eof,
    output wire [7:0] edge_magnitude,
    output wire [7:0] edge_pixel
);
    rgb888_to_gray u_gray (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid),
        .in_sof(in_sof), .in_sol(in_sol), .in_eol(in_eol), .in_eof(in_eof),
        .in_r(in_r), .in_g(in_g), .in_b(in_b),
        .out_valid(gray_valid), .out_sof(gray_sof), .out_sol(gray_sol),
        .out_eol(gray_eol), .out_eof(gray_eof), .out_gray(gray_pixel)
    );
    gray_threshold #(.THRESHOLD(THRESHOLD)) u_binary (
        .clk(clk), .rst_n(rst_n), .in_valid(gray_valid),
        .in_sof(gray_sof), .in_sol(gray_sol), .in_eol(gray_eol), .in_eof(gray_eof),
        .in_gray(gray_pixel), .out_valid(binary_valid),
        .out_sof(binary_sof), .out_sol(binary_sol),
        .out_eol(binary_eol), .out_eof(binary_eof), .out_mask(binary_pixel)
    );
    sobel_stream #(.WIDTH(WIDTH), .HEIGHT(HEIGHT), .EDGE_THRESHOLD(EDGE_THRESHOLD)) u_sobel (
        .clk(clk), .rst_n(rst_n), .in_valid(gray_valid),
        .in_sof(gray_sof), .in_gray(gray_pixel),
        .out_valid(edge_valid), .out_sof(edge_sof), .out_sol(edge_sol),
        .out_eol(edge_eol), .out_eof(edge_eof),
        .out_magnitude(edge_magnitude), .out_edge(edge_pixel)
    );
endmodule
