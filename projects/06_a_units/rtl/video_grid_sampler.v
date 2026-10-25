`timescale 1ns / 1ps
// Uniform nearest-neighbour grid, with VS rising during blanking as the boundary.
// Delay the final grid sample until the next VS: only a full, correctly sized
// physical frame can be committed to motion history. No frame RAM here.
module video_grid_sampler #(
    parameter integer FRAME_WIDTH = 1920,
    parameter integer FRAME_HEIGHT = 1080,
    parameter integer STEP_X = 20,
    parameter integer STEP_Y = 20
) (
    input wire clk, rst_n,
    input wire in_vs, in_de,
    input wire [7:0] in_gray,
    output reg sample_valid, sample_sof, sample_eof, sample_abort,
    output reg [7:0] sample_gray
);
    localparam integer GRID_WIDTH = (FRAME_WIDTH+STEP_X-1)/STEP_X;
    localparam integer GRID_HEIGHT = (FRAME_HEIGHT+STEP_Y-1)/STEP_Y;
    localparam integer GRID_PIXELS = GRID_WIDTH*GRID_HEIGHT;
    reg vs_d, de_d, ready, started, format_ok, complete, pending_last;
    reg [15:0] x_count, y_count, x_skip, y_skip;
    reg [31:0] sample_count;
    reg [7:0] last_gray;
    wire new_vs = in_vs && !vs_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vs_d <= 0; de_d <= 0; ready <= 0; started <= 0;
            format_ok <= 1; complete <= 0; pending_last <= 0;
            x_count <= 0; y_count <= 0; x_skip <= 0; y_skip <= 0;
            sample_count <= 0; last_gray <= 0;
            sample_valid <= 0; sample_sof <= 0; sample_eof <= 0;
            sample_abort <= 0; sample_gray <= 0;
        end else begin
            vs_d <= in_vs; de_d <= in_de;
            sample_valid <= 0; sample_sof <= 0; sample_eof <= 0; sample_abort <= 0;
            if (new_vs) begin
                if (ready) begin
                    if (started && format_ok && complete && pending_last && !in_de) begin
                        sample_valid <= 1; sample_sof <= (GRID_PIXELS == 1);
                        sample_eof <= 1; sample_gray <= last_gray;
                    end else sample_abort <= 1;
                end
                ready <= 1; started <= 0; format_ok <= !in_de;
                complete <= 0; pending_last <= 0;
                x_count <= 0; y_count <= 0; x_skip <= 0; y_skip <= 0; sample_count <= 0;
            end else if (ready) begin
                if (in_de) begin
                    started <= 1;
                    x_count <= x_count + 1'b1;
                    if (x_count >= FRAME_WIDTH || y_count >= FRAME_HEIGHT) begin
                        format_ok <= 0; sample_abort <= 1;
                    end
                    if (format_ok && x_count < FRAME_WIDTH && y_count < FRAME_HEIGHT && x_skip == 0 && y_skip == 0) begin
                        sample_count <= sample_count + 1'b1;
                        if (sample_count == GRID_PIXELS-1) begin
                            pending_last <= 1; last_gray <= in_gray;
                        end else begin
                            sample_valid <= 1; sample_sof <= (sample_count == 0);
                            sample_gray <= in_gray;
                        end
                    end
                    if (x_skip == 0) x_skip <= STEP_X-1;
                    else x_skip <= x_skip - 1'b1;
                end else if (de_d) begin
                    if (x_count != FRAME_WIDTH) begin format_ok <= 0; sample_abort <= 1; end
                    if (y_count == FRAME_HEIGHT-1) complete <= 1;
                    y_count <= y_count + 1'b1; x_count <= 0; x_skip <= 0;
                    if (y_skip == 0) y_skip <= STEP_Y-1;
                    else y_skip <= y_skip - 1'b1;
                end
            end
        end
    end
endmodule
