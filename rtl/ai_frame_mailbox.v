`timescale 1ns/1ps
// One clock domain ONLY. The bus/CDC adapter belongs outside this module.
// Store only active 96x54 bytes; expose virtual black letterbox rows on reads.
// reader_take/release/read_req are pulses; reader must wait for reader_active.
module ai_frame_mailbox #(
    parameter integer WIDTH=96, HEIGHT=54, PAD_TOP=21, PAD_BOTTOM=21
)(
    input wire clk, rst_n,
    input wire sample_valid, sample_sof, sample_eof, sample_abort,
    input wire [7:0] sample_gray,
    input wire [31:0] source_frame_id, source_timestamp_ms,
    input wire reader_take, reader_release, read_req,
    input wire [15:0] read_address,
    output wire frame_ready,
    output reg reader_active, reader_buffer,
    output reg [31:0] reader_frame_id, reader_timestamp_ms, reader_checksum,
    output reg read_valid, read_error,
    output wire [7:0] read_data,
    output reg [31:0] committed_frames, dropped_frames, malformed_frames
);
    localparam N=WIDTH*HEIGHT, FIRST=WIDTH*PAD_TOP;
    localparam TOTAL=WIDTH*(PAD_TOP+HEIGHT+PAD_BOTTOM);
    localparam FREE=0, WRITING=1, READY=2, READING=3;
    reg [1:0] state0, state1;
    reg [7:0] mem0[0:N-1], mem1[0:N-1];
    reg [7:0] ram_q0,ram_q1;
    reg read_pixel,read_bank;
    localparam ADDR_BITS=N>1?$clog2(N):1;
    wire [ADDR_BITS-1:0] ram_read_address=(read_address>=FIRST&&read_address<FIRST+N)?read_address-FIRST:0;
    assign read_data=read_pixel?(read_bank?ram_q1:ram_q0):8'd0;
    reg writer_active, writer_buffer, discard;
    reg [15:0] count;
    reg [31:0] sum, fid0, fid1, ts0, ts1, crc0, crc1;
    reg oldest;
    wire have_free = state0==FREE || state1==FREE;
    wire selected = state0!=FREE;
    assign frame_ready = state0==READY || state1==READY;
    wire chosen_ready = state0==READY && state1==READY ? oldest : state0!=READY;
    wire start_ok = sample_valid && sample_sof && have_free && !sample_abort;
    wire continuing = sample_valid && !sample_sof && writer_active && !sample_abort;
    wire write_enable = start_ok || continuing;
    wire write_bank = start_ok ? selected : writer_buffer;
    wire [15:0] write_index = start_ok ? 16'd0 : count;
    // Dedicated memory processes preserve synchronous RAM inference; no reset loop.
    always @(posedge clk) begin
        if(rst_n && write_enable && write_index<N) begin
            if(!write_bank) mem0[write_index] <= sample_gray;
            else mem1[write_index] <= sample_gray;
        end
        // Separate unconditional synchronous read ports, mux AFTER the RAM registers.
        ram_q0 <= mem0[ram_read_address];
        ram_q1 <= mem1[ram_read_address];
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state0<=FREE;state1<=FREE;writer_active<=0;writer_buffer<=0;discard<=0;
            count<=0;sum<=0;fid0<=0;fid1<=0;ts0<=0;ts1<=0;crc0<=0;crc1<=0;oldest<=0;
            reader_active<=0;reader_buffer<=0;reader_frame_id<=0;reader_timestamp_ms<=0;reader_checksum<=0;
            read_valid<=0;read_error<=0;read_pixel<=0;read_bank<=0;committed_frames<=0;dropped_frames<=0;malformed_frames<=0;
        end else begin
            read_valid<=read_req;
            read_pixel<=read_req&&reader_active&&!reader_release&&read_address>=FIRST&&read_address<FIRST+N;
            read_bank<=reader_buffer;
            read_error<=read_req && (!reader_active || reader_release || read_address>=TOTAL);
            if(reader_release && reader_active) begin
                if(!reader_buffer) state0<=FREE; else state1<=FREE;
                reader_active<=0;
            end else if(reader_take && !reader_active && frame_ready) begin
                reader_active<=1;reader_buffer<=chosen_ready;
                if(!chosen_ready) begin
                    state0<=READING;reader_frame_id<=fid0;reader_timestamp_ms<=ts0;reader_checksum<=crc0;
                end else begin
                    state1<=READING;reader_frame_id<=fid1;reader_timestamp_ms<=ts1;reader_checksum<=crc1;
                end
            end
            if(sample_abort) begin
                if(writer_active) begin
                    if(!writer_buffer) state0<=FREE;else state1<=FREE;
                    malformed_frames<=malformed_frames+1'b1;
                end
                writer_active<=0;discard<=0;
            end else if(sample_valid) begin
                if(sample_sof) begin
                    // Unexpected SOF discards the partial frame, never publishes it.
                    if(writer_active) begin
                        if(!writer_buffer) state0<=FREE;else state1<=FREE;
                        malformed_frames<=malformed_frames+1'b1;
                    end
                    writer_active<=0;count<=1;sum<=sample_gray;discard<=!have_free;
                    if(!have_free) dropped_frames<=dropped_frames+1'b1;
                    else begin
                        writer_buffer<=selected;
                        if(!selected) begin state0<=WRITING;fid0<=source_frame_id;ts0<=source_timestamp_ms;end
                        else begin state1<=WRITING;fid1<=source_frame_id;ts1<=source_timestamp_ms;end
                        if(sample_eof) begin
                            if(N==1) begin
                                if(!selected) begin state0<=READY;crc0<=sample_gray;end
                                else begin state1<=READY;crc1<=sample_gray;end
                                if(!frame_ready) oldest<=selected;
                                committed_frames<=committed_frames+1'b1;
                            end else begin
                                if(!selected) state0<=FREE;else state1<=FREE;
                                malformed_frames<=malformed_frames+1'b1;
                            end
                        end else writer_active<=1;
                    end
                end else if(writer_active) begin
                    count<=count+1'b1;sum<=sum+sample_gray;
                    if(sample_eof || count==N-1) begin
                        writer_active<=0;
                        if(sample_eof && count==N-1) begin
                            if(!writer_buffer) begin state0<=READY;crc0<=sum+sample_gray;end
                            else begin state1<=READY;crc1<=sum+sample_gray;end
                            if(!frame_ready) oldest<=writer_buffer;
                            committed_frames<=committed_frames+1'b1;
                        end else begin
                            if(!writer_buffer) state0<=FREE;else state1<=FREE;
                            malformed_frames<=malformed_frames+1'b1;
                        end
                    end
                end else if(sample_eof) discard<=0;
            end
            // When the oldest READY bank is acquired, the other becomes oldest.
            if(reader_take && !reader_active && frame_ready) oldest<=!chosen_ready;
        end
    end
endmodule
