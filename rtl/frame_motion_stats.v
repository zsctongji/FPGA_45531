`timescale 1ns / 1ps
// Ordered, fixed-size grayscale frames. SOF/EOF qualify valid pixels.
// Read-before-write RAM stores one previous frame; reset never clears the RAM.
// A malformed frame invalidates the baseline until a complete new frame arrives.
module frame_motion_stats #(
    parameter integer WIDTH = 96,
    parameter integer HEIGHT = 54,
    parameter integer DIFF_THRESHOLD = 24,
    parameter integer MIN_CHANGED = 32
) (
    input wire clk, rst_n,
    input wire in_valid, in_sof, in_eof, in_abort,
    input wire [7:0] in_gray,
    output reg out_valid, comparison_valid, motion, frame_error,
    output reg [31:0] changed_count, absolute_difference_sum,
    output reg bbox_valid,
    output reg [15:0] min_x, min_y, max_x, max_y
);
    localparam integer PIXELS = WIDTH * HEIGHT;
    localparam integer AW = (PIXELS < 2) ? 1 : $clog2(PIXELS);
    reg [7:0] previous [0:PIXELS-1];
    reg active, baseline_valid, frame_compare;
    reg [AW-1:0] next_address;
    reg [15:0] next_x, next_y;
    wire accept_pixel = in_valid && !in_abort && (in_sof || active);
    wire [AW-1:0] address = in_sof ? {AW{1'b0}} : next_address;
    wire [15:0] x = in_sof ? 16'd0 : next_x;
    wire [15:0] y = in_sof ? 16'd0 : next_y;
    wire last_pixel = (address == PIXELS-1);
    wire compare_pixel = in_sof ? (baseline_valid && !active) : frame_compare;
    reg [7:0] old_gray, pixel_gray;
    reg pixel_valid, pixel_sof, pixel_last, pixel_compare;
    reg [15:0] pixel_x, pixel_y;

    // Separate from reset logic so this can infer embedded RAM.
    always @(posedge clk) begin
        if (rst_n && accept_pixel) begin
            old_gray <= previous[address];
            previous[address] <= in_gray;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 0; baseline_valid <= 0; frame_compare <= 0;
            next_address <= 0; next_x <= 0; next_y <= 0;
            pixel_valid <= 0; pixel_sof <= 0; pixel_last <= 0;
            pixel_compare <= 0; pixel_gray <= 0; pixel_x <= 0; pixel_y <= 0;
            frame_error <= 0;
        end else begin
            frame_error <= 0;
            pixel_valid <= accept_pixel;
            pixel_sof <= in_sof;
            pixel_last <= last_pixel && in_eof;
            pixel_compare <= compare_pixel;
            pixel_gray <= in_gray; pixel_x <= x; pixel_y <= y;
            if (in_valid) begin
                if (accept_pixel) begin
                    if (in_sof) begin
                        frame_compare <= baseline_valid && !active;
                        if (active) begin
                            frame_error <= 1;
                            baseline_valid <= 0;
                        end
                    end
                    next_address <= address + 1'b1;
                    if (x == WIDTH-1) begin next_x <= 0; next_y <= y + 1'b1; end
                    else begin next_x <= x + 1'b1; next_y <= y; end
                    active <= !last_pixel && !in_eof;
                    if (in_eof != last_pixel) begin
                        frame_error <= 1; baseline_valid <= 0; active <= 0;
                    end else if (last_pixel) baseline_valid <= 1;
                end else begin
                    frame_error <= 1; baseline_valid <= 0;
                end
            end
            if (in_abort) begin
                active <= 0; baseline_valid <= 0; frame_compare <= 0;
                pixel_valid <= 0; frame_error <= 1;
            end
        end
    end

    reg [31:0] count_acc, sum_acc;
    reg [15:0] xmin_acc, ymin_acc, xmax_acc, ymax_acc;
    wire [7:0] difference = pixel_gray >= old_gray ? pixel_gray-old_gray : old_gray-pixel_gray;
    wire changed = pixel_compare && (difference >= DIFF_THRESHOLD);
    wire [31:0] count_next = (pixel_sof ? 32'd0 : count_acc) + (changed ? 32'd1 : 32'd0);
    wire [31:0] sum_next = (pixel_sof ? 32'd0 : sum_acc) + (pixel_compare ? {24'd0,difference} : 32'd0);
    wire [15:0] xmin_next = changed && (pixel_sof || pixel_x < xmin_acc) ? pixel_x : (pixel_sof ? 16'hffff : xmin_acc);
    wire [15:0] ymin_next = changed && (pixel_sof || pixel_y < ymin_acc) ? pixel_y : (pixel_sof ? 16'hffff : ymin_acc);
    wire [15:0] xmax_next = changed && (pixel_sof || pixel_x > xmax_acc) ? pixel_x : (pixel_sof ? 16'd0 : xmax_acc);
    wire [15:0] ymax_next = changed && (pixel_sof || pixel_y > ymax_acc) ? pixel_y : (pixel_sof ? 16'd0 : ymax_acc);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 0; comparison_valid <= 0; motion <= 0;
            changed_count <= 0; absolute_difference_sum <= 0; bbox_valid <= 0;
            min_x <= 0; min_y <= 0; max_x <= 0; max_y <= 0;
            count_acc <= 0; sum_acc <= 0;
            xmin_acc <= 16'hffff; ymin_acc <= 16'hffff; xmax_acc <= 0; ymax_acc <= 0;
        end else begin
            out_valid <= 0;
            if (pixel_valid && !in_abort) begin
                count_acc <= count_next; sum_acc <= sum_next;
                xmin_acc <= xmin_next; ymin_acc <= ymin_next;
                xmax_acc <= xmax_next; ymax_acc <= ymax_next;
                if (pixel_last) begin
                    out_valid <= 1; comparison_valid <= pixel_compare;
                    changed_count <= count_next; absolute_difference_sum <= sum_next;
                    motion <= pixel_compare && (count_next >= MIN_CHANGED);
                    bbox_valid <= (count_next != 0);
                    min_x <= count_next != 0 ? xmin_next : 16'd0;
                    min_y <= count_next != 0 ? ymin_next : 16'd0;
                    max_x <= count_next != 0 ? xmax_next : 16'd0;
                    max_y <= count_next != 0 ? ymax_next : 16'd0;
                end
            end
        end
    end
endmodule
