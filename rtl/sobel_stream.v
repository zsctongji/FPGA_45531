`timescale 1ns / 1ps

// Streaming 3x3 Sobel with two line buffers, accepting valid gaps.
// Only interior pixels are emitted: output frame is (WIDTH-2)x(HEIGHT-2).
// WIDTH/HEIGHT must be >= 3. Input SOF marks the first active pixel.
module sobel_stream #(
    parameter integer WIDTH = 640,
    parameter integer HEIGHT = 480,
    parameter integer EDGE_THRESHOLD = 80
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       in_valid,
    input  wire       in_sof,
    input  wire [7:0] in_gray,
    output reg        out_valid,
    output reg        out_sof,
    output reg        out_sol,
    output reg        out_eol,
    output reg        out_eof,
    output reg  [7:0] out_magnitude,
    output reg  [7:0] out_edge
);
    function integer bits_for;
        input integer n;
        integer t;
        begin
            t = n - 1;
            bits_for = 0;
            while (t > 0) begin
                bits_for = bits_for + 1;
                t = t >> 1;
            end
            if (bits_for == 0) bits_for = 1;
        end
    endfunction

    localparam integer X_BITS = bits_for(WIDTH);
    localparam integer Y_BITS = bits_for(HEIGHT);
    reg [X_BITS-1:0] next_x;
    reg [Y_BITS-1:0] next_y;
    wire [X_BITS-1:0] x = in_sof ? {X_BITS{1'b0}} : next_x;
    wire [Y_BITS-1:0] y = in_sof ? {Y_BITS{1'b0}} : next_y;

    // No reset on line memories; outputs are suppressed until both are filled.
    // Asynchronous reads are intentional. Check memory mapping/timing in the
    // chosen device's synthesis report before increasing the pixel clock.
    reg [7:0] line_previous [0:WIDTH-1];
    reg [7:0] line_older [0:WIDTH-1];
    reg [7:0] top_left, top_middle;
    reg [7:0] mid_left, mid_middle;
    reg [7:0] bot_left, bot_middle;
    wire [7:0] top_right = line_older[x];
    wire [7:0] mid_right = line_previous[x];

    wire signed [11:0] t0 = $signed({4'b0, top_left});
    wire signed [11:0] t1 = $signed({4'b0, top_middle});
    wire signed [11:0] t2 = $signed({4'b0, top_right});
    wire signed [11:0] m0 = $signed({4'b0, mid_left});
    wire signed [11:0] m2 = $signed({4'b0, mid_right});
    wire signed [11:0] b0 = $signed({4'b0, bot_left});
    wire signed [11:0] b1 = $signed({4'b0, bot_middle});
    wire signed [11:0] b2 = $signed({4'b0, in_gray});
    wire signed [11:0] gx = (t2 + (m2 <<< 1) + b2) - (t0 + (m0 <<< 1) + b0);
    wire signed [11:0] gy = (b0 + (b1 <<< 1) + b2) - (t0 + (t1 <<< 1) + t2);
    wire [11:0] abs_gx = gx[11] ? (~gx + 12'd1) : gx;
    wire [11:0] abs_gy = gy[11] ? (~gy + 12'd1) : gy;
    wire [12:0] magnitude_sum = {1'b0, abs_gx} + {1'b0, abs_gy};
    wire [7:0] clipped_magnitude = (magnitude_sum > 13'd255) ? 8'hff : magnitude_sum[7:0];

    always @(posedge clk) begin
        if (rst_n && in_valid) begin
            line_older[x] <= line_previous[x];
            line_previous[x] <= in_gray;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            next_x <= {X_BITS{1'b0}};
            next_y <= {Y_BITS{1'b0}};
            top_left <= 8'd0;
            top_middle <= 8'd0;
            mid_left <= 8'd0;
            mid_middle <= 8'd0;
            bot_left <= 8'd0;
            bot_middle <= 8'd0;
            out_valid <= 1'b0;
            out_sof <= 1'b0;
            out_sol <= 1'b0;
            out_eol <= 1'b0;
            out_eof <= 1'b0;
            out_magnitude <= 8'd0;
            out_edge <= 8'd0;
        end else begin
            out_valid <= 1'b0;
            out_sof <= 1'b0;
            out_sol <= 1'b0;
            out_eol <= 1'b0;
            out_eof <= 1'b0;
            if (in_valid) begin
                if (x == WIDTH - 1) begin
                    next_x <= {X_BITS{1'b0}};
                    if (y == HEIGHT - 1)
                        next_y <= {Y_BITS{1'b0}};
                    else
                        next_y <= y + 1'b1;
                end else begin
                    next_x <= x + 1'b1;
                    next_y <= y;
                end
                if (x == 0) begin
                    top_left <= 8'd0;
                    top_middle <= top_right;
                    mid_left <= 8'd0;
                    mid_middle <= mid_right;
                    bot_left <= 8'd0;
                    bot_middle <= in_gray;
                end else begin
                    top_left <= top_middle;
                    top_middle <= top_right;
                    mid_left <= mid_middle;
                    mid_middle <= mid_right;
                    bot_left <= bot_middle;
                    bot_middle <= in_gray;
                end
                if (x >= 2 && y >= 2) begin
                    out_valid <= 1'b1;
                    out_sof <= (x == 2 && y == 2);
                    out_sol <= (x == 2);
                    out_eol <= (x == WIDTH - 1);
                    out_eof <= (x == WIDTH - 1 && y == HEIGHT - 1);
                    out_magnitude <= clipped_magnitude;
                    out_edge <= (clipped_magnitude >= EDGE_THRESHOLD) ? 8'hff : 8'h00;
                end
            end
        end
    end
endmodule
