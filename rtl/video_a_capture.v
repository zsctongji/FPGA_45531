`timescale 1ns/1ps
// Tap in the SOURCE pixel clock to measure capture, or label as display tap.
// Shared now_ms must already be transferred coherently into this clock domain.
// VS is active-high and rises in blanking, DE covers one whole active line.
module video_a_capture #(
    parameter integer FRAME_WIDTH=1920,FRAME_HEIGHT=1080,STEP_X=20,STEP_Y=20
)(
    input wire clk,rst_n,in_vs,in_de,
    input wire [7:0] in_gray,
    input wire [31:0] now_ms,
    output wire sample_valid,sample_sof,sample_eof,sample_abort,
    output wire [7:0] sample_gray,
    output reg [31:0] sample_frame_id,sample_timestamp_ms,
    output reg record_valid,record_complete,
    output reg [31:0] record_frame_id,record_timestamp_ms,
    output reg [15:0] record_width,record_height,
    output reg [31:0] source_frames,format_errors
);
    reg vs_d,de_d,started,opened,bad;
    reg [15:0] x,y,max_width;
    reg [31:0] frame_id,stamp;
    wire boundary=in_vs&&!vs_d;
    video_grid_sampler #(.FRAME_WIDTH(FRAME_WIDTH),.FRAME_HEIGHT(FRAME_HEIGHT),.STEP_X(STEP_X),.STEP_Y(STEP_Y)) sampler(
        .clk(clk),.rst_n(rst_n),.in_vs(in_vs),.in_de(in_de),.in_gray(in_gray),
        .sample_valid(sample_valid),.sample_sof(sample_sof),.sample_eof(sample_eof),.sample_abort(sample_abort),.sample_gray(sample_gray));
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            vs_d<=0;de_d<=0;started<=0;opened<=0;bad<=0;x<=0;y<=0;max_width<=0;
            frame_id<=0;stamp<=0;source_frames<=0;format_errors<=0;
            sample_frame_id<=0;sample_timestamp_ms<=0;record_valid<=0;record_complete<=0;
            record_frame_id<=0;record_timestamp_ms<=0;record_width<=0;record_height<=0;
        end else begin
            vs_d<=in_vs;de_d<=in_de;record_valid<=0;
            if(boundary) begin
                if(opened) begin
                    record_valid<=1;record_frame_id<=frame_id;record_timestamp_ms<=stamp;
                    record_width<=max_width;record_height<=y;
                    record_complete<=started&&!bad&&!in_de&&!de_d&&y==FRAME_HEIGHT&&max_width==FRAME_WIDTH;
                    if(!started||bad||in_de||de_d||y!=FRAME_HEIGHT||max_width!=FRAME_WIDTH)
                        format_errors<=format_errors+1'b1;
                    // Keep prior-frame metadata at the delayed EOF from sampler.
                    sample_frame_id<=frame_id;sample_timestamp_ms<=stamp;
                end
                frame_id<=source_frames;source_frames<=source_frames+1'b1;
                opened<=1;started<=0;bad<=in_de;x<=0;y<=0;max_width<=0;
            end else if(opened) begin
                if(in_de) begin
                    if(!started) begin
                        stamp<=now_ms;started<=1;
                        sample_frame_id<=frame_id;sample_timestamp_ms<=now_ms;
                    end
                    if(x<65535) x<=x+1'b1;else bad<=1;
                    if(x>=FRAME_WIDTH||y>=FRAME_HEIGHT) bad<=1;
                end else if(de_d) begin
                    if(x!=FRAME_WIDTH) bad<=1;
                    if(x>max_width) max_width<=x;
                    if(y<65535) y<=y+1'b1;else bad<=1;
                    x<=0;
                end
            end
        end
    end
endmodule
