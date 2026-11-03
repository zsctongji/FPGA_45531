`timescale 1ns/1ps
// Single serialized owner in memory clock domain. Commands from other domains
// must pass through CDC mailboxes. Descriptor fields match cooperation_v1.h.
module c2_buffer_manager(
 input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready, input wire [2:0] cmd,
 input wire slot, input wire [31:0] generation,
 input wire [511:0] descriptor,
 output reg rsp_valid, input wire rsp_ready,
 output reg [1:0] rsp_status, output reg rsp_slot,
 output reg [31:0] rsp_generation, output reg [511:0] rsp_descriptor,
 output wire [3:0] slot_states, output reg [31:0] dropped
);
 localparam FREE=0,WRITING=1,READY=2,READING=3;
 localparam ALLOC=0,COMMIT=1,ABORT=2,ACQUIRE=3,RELEASE=4,QUERY=5;
 localparam OK=0,BUSY=1,ESTATE=2,EINVAL=3;
 reg [1:0] state[0:1];
 reg [31:0] gen[0:1];
 reg [511:0] meta[0:1];
 integer i;
 reg selected;
 wire meta_ok=descriptor[31:0]==32'h10000 &&
   descriptor[127:96]=={31'b0,slot} &&
   descriptor[159:128]==(slot ? 32'h4000 : 32'h1000) &&
   descriptor[191:160]==9216 && descriptor[223:192]==1 &&
   descriptor[255:224]==96 && descriptor[288] &&
   (descriptor[319:288]&32'hfffffff8)==0 && descriptor[511:480]==0 &&
   descriptor[351:320]<=5184;
 // Separate slices below avoid assuming signed coordinates.
 wire bbox_ok=!descriptor[290] ||
   (descriptor[289] && descriptor[383:352]<=descriptor[447:416] &&
    descriptor[415:384]<=descriptor[479:448] &&
    descriptor[447:416]<96 && descriptor[479:448]<54);
 assign slot_states={state[1],state[0]};
 assign cmd_ready=!rsp_valid || rsp_ready;
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin
     rsp_valid<=0;rsp_status<=0;rsp_slot<=0;rsp_generation<=0;
     rsp_descriptor<=0;dropped<=0;
     for(i=0;i<2;i=i+1) begin state[i]<=FREE;gen[i]<=0;meta[i]<=0;end
   end else begin
     if(rsp_valid && rsp_ready) rsp_valid<=0;
     if(cmd_valid && cmd_ready) begin
       rsp_valid<=1;rsp_status<=OK;rsp_slot<=slot;
       rsp_generation<=gen[slot];rsp_descriptor<=meta[slot];
       case(cmd)
         ALLOC: begin
           if(state[0]==FREE || state[1]==FREE) begin
             selected=(state[0]==FREE)?0:1;
             state[selected]<=WRITING;gen[selected]<=gen[selected]+1;
             rsp_slot<=selected;rsp_generation<=gen[selected]+1;
             rsp_descriptor<=0;
           end else begin rsp_status<=BUSY;dropped<=dropped+1;end
         end
         COMMIT: begin
           if(state[slot]!=WRITING || gen[slot]!=generation) rsp_status<=ESTATE;
           else if(!meta_ok || !bbox_ok) rsp_status<=EINVAL;
           else begin state[slot]<=READY;meta[slot]<=descriptor;rsp_descriptor<=descriptor;end
         end
         ABORT: begin
           if(state[slot]!=WRITING || gen[slot]!=generation) rsp_status<=ESTATE;
           else state[slot]<=FREE;
         end
         ACQUIRE: begin
           if(state[slot]!=READY || gen[slot]!=generation) rsp_status<=ESTATE;
           else state[slot]<=READING;
         end
         RELEASE: begin
           if(state[slot]!=READING || gen[slot]!=generation) rsp_status<=ESTATE;
           else state[slot]<=FREE;
         end
         QUERY: begin end // Return current token and descriptor, no ownership change.
         default: rsp_status<=EINVAL;
       endcase
     end
   end
 end
endmodule

