`timescale 1ns/1ps
// A's single-clock byte-read lease -> C2's 576-word stream and source verdict.
// A BRAM lease and C2 DDR generation are deliberately independent owners.
module c2_a_mailbox_bridge #(parameter READ_TIMEOUT=32)(
 input wire clk,rst_n,enable,
 input wire a_ready,a_active,input wire [31:0] a_frame_id,a_timestamp_ms,a_sum32,
 output wire a_take,a_release,a_read_req,output wire [15:0] a_read_address,
 input wire a_read_valid,a_read_error,input wire [7:0] a_read_data,
 output wire v_frame_valid,input wire v_frame_ready,output wire [511:0] v_descriptor,
 input wire v_grant_valid,output wire v_grant_ready,input wire [31:0] v_grant_frame_id,
 output wire v_word_valid,input wire v_word_ready,output wire [127:0] v_word_data,
 output wire v_source_valid,input wire v_source_ready,output wire v_source_error,
 output wire [31:0] v_source_frame_id,v_source_fnv,
 input wire v_event_valid,output wire v_event_ready,input wire [2:0] v_event_status,
 input wire [511:0] v_event_descriptor,
 output reg [31:0] completed,rejected,source_faults,
 output reg [31:0] last_frame_id,last_sum32,last_fnv,output reg [2:0] last_status
);
 localparam IDLE=0,TAKE=1,LEASE=2,REQUEST=3,GRANT=4,READ=5,WAIT_BYTE=6,PACK=7,
            WORD=8,VERDICT=9,EVENT=10,RELEASE=11;
 reg [3:0] state;
 reg [31:0] frame_id,stamp,expected_sum,sum,hash;
 reg [15:0] pixel;
 reg [3:0] lane;
 reg [127:0] packed_word;
 reg [7:0] value;
 reg bad,drain;
 integer waited;
 assign a_take=state==TAKE;assign a_release=state==RELEASE;
 assign a_read_req=state==READ;assign a_read_address=pixel;
 assign v_frame_valid=state==REQUEST;
 assign v_grant_ready=state==GRANT;
 assign v_word_valid=state==WORD;assign v_word_data=packed_word;
 assign v_source_valid=state==VERDICT;
 assign v_source_error=bad || sum!=expected_sum || pixel!=9216;
 assign v_source_frame_id=frame_id;assign v_source_fnv=hash;
 assign v_event_ready=state==GRANT || state==EVENT;
 // Only frame identity/time/format are submitted. C2 assigns its own slot/token
 // and computes the DDR checksum; A's SUM32 is never labelled as FNV.
 assign v_descriptor={192'b0,32'd1,32'b0,32'd96,32'd1,32'd9216,32'b0,32'b0,stamp,frame_id,32'h10000};
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin
     state<=IDLE;frame_id<=0;stamp<=0;expected_sum<=0;sum<=0;hash<=0;pixel<=0;lane<=0;
     packed_word<=0;value<=0;bad<=0;drain<=0;waited<=0;completed<=0;rejected<=0;source_faults<=0;
     last_frame_id<=0;last_sum32<=0;last_fnv<=0;last_status<=0;
   end else case(state)
     IDLE: if(enable && a_ready && !a_active) state<=TAKE;
     TAKE: begin state<=LEASE;waited<=0;end
     LEASE: if(a_active) begin
       frame_id<=a_frame_id;stamp<=a_timestamp_ms;expected_sum<=a_sum32;
       pixel<=0;lane<=0;sum<=0;hash<=32'd2166136261;bad<=0;drain<=0;state<=REQUEST;
     end else if(waited>=READ_TIMEOUT) begin source_faults<=source_faults+32'd1;state<=RELEASE;end
     else waited<=waited+1;
     REQUEST: if(v_frame_ready) state<=GRANT;
     GRANT: if(v_event_valid) begin
       last_status<=v_event_status;last_frame_id<=frame_id;rejected<=rejected+32'd1;state<=RELEASE;
     end else if(v_grant_valid) begin
       bad<=v_grant_frame_id!=frame_id;state<=READ;
     end
     READ: begin waited<=0;state<=WAIT_BYTE;end
     WAIT_BYTE: if(a_read_valid) begin
       if(a_read_error || !a_active) begin bad<=1;drain<=1;value<=0;end
       else value<=a_read_data;
       state<=PACK;
     end else if(waited>=READ_TIMEOUT) begin bad<=1;drain<=1;value<=0;state<=PACK;end
     else waited<=waited+1;
     PACK: begin
       packed_word[lane*8+:8]<=drain?8'b0:value;
       sum<=sum+{24'b0,(drain?8'b0:value)};
       hash<=(hash^{24'b0,(drain?8'b0:value)})*32'd16777619;
       // This adapter transports A's current PAD54 candidate, not an approved
       // model preprocessing policy. Corrupt virtual padding fails the verdict.
       if((pixel<2016 || pixel>=7200) && value!=0) bad<=1;
       pixel<=pixel+16'd1;
       if(lane==15) begin lane<=0;state<=WORD;end
       else begin lane<=lane+4'd1;state<=drain?PACK:READ;end
     end
     WORD: if(v_word_ready) begin
       if(pixel==9216) state<=VERDICT;else state<=drain?PACK:READ;
     end
     VERDICT: if(v_source_ready) begin
       last_sum32<=sum;last_fnv<=hash;
       if(v_source_error) source_faults<=source_faults+32'd1;
       state<=EVENT;
     end
     EVENT: if(v_event_valid) begin
       last_frame_id<=frame_id;last_status<=v_event_status;
       if(v_event_status==0 && v_event_descriptor[63:32]==frame_id && !bad && sum==expected_sum)
         completed<=completed+32'd1;
       else rejected<=rejected+32'd1;
       state<=RELEASE;
     end
     RELEASE: state<=IDLE;
   endcase
 end
endmodule
