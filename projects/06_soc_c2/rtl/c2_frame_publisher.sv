`timescale 1ns/1ps
// Allocation -> writer -> final B response -> COMMIT is enforced in hardware.
// CPU control is restricted to ACQUIRE/RELEASE/QUERY. All ports are memory-clock domain;
// cross-domain request/events require c2_cdc_mailbox and one common reset.
module c2_frame_publisher(
 input wire clk,rst_n,
 input wire frame_valid,output wire frame_ready,
 input wire [511:0] frame_descriptor,input wire [31:0] shared_base,
 output wire write_start_valid,input wire write_start_ready,output wire [31:0] write_address,
 input wire write_done_valid,output wire write_done_ready,
 input wire write_done_error,input wire [31:0] write_checksum,
 output wire event_valid,input wire event_ready,output wire [2:0] event_status,
 output wire event_slot,output wire [31:0] event_generation,output wire [511:0] event_descriptor,
 input wire cpu_valid,output wire cpu_ready,input wire [2:0] cpu_cmd,
 input wire cpu_slot,input wire [31:0] cpu_generation,
 output wire cpu_rsp_valid,input wire cpu_rsp_ready,output wire [1:0] cpu_rsp_status,
 output wire [511:0] cpu_descriptor,
 output wire cpu_rsp_slot,output wire [31:0] cpu_rsp_generation,
 output wire [3:0] slot_states,output wire [31:0] dropped
);
 localparam IDLE=0,ASEND=1,AWAIT=2,WSTART=3,WWAIT=4,CSEND=5,CWAIT=6,
            BSEND=7,BWAIT=8,EVENT=9;
 reg [3:0] state;
 reg [511:0] meta;
 reg [31:0] base,token_generation;
 reg token_slot;
 reg [2:0] status;
 reg route_cpu,prefer_cpu;
 wire internal_valid=state==ASEND || state==CSEND || state==BSEND;
 wire choose_cpu=cpu_valid && (!internal_valid || prefer_cpu);
 wire choose_internal=internal_valid && !choose_cpu;
 wire manager_ready,manager_rsp_valid;
 wire [1:0] manager_status;
 wire manager_slot;
 wire [31:0] manager_generation;
 wire [511:0] manager_descriptor;
 wire manager_rsp_ready=route_cpu ? cpu_rsp_ready : 1'b1;
 wire [2:0] internal_cmd=state==ASEND?0:(state==CSEND?1:2);
 wire [2:0] request_cmd=choose_cpu ? ((cpu_cmd==3 || cpu_cmd==4 || cpu_cmd==5)?cpu_cmd:3'd7) : internal_cmd;
 wire manager_valid=choose_cpu || choose_internal;
 assign cpu_ready=choose_cpu && manager_ready;
 assign cpu_rsp_valid=manager_rsp_valid && route_cpu;
 assign cpu_rsp_status=manager_status;
 assign cpu_descriptor=manager_descriptor;
 assign cpu_rsp_slot=manager_slot;assign cpu_rsp_generation=manager_generation;
 assign frame_ready=(state==IDLE);
 assign write_start_valid=(state==WSTART);
 assign write_address=base+(token_slot?32'h4000:32'h1000);
 assign write_done_ready=(state==WWAIT);
 assign event_valid=(state==EVENT);
 assign event_status=status;assign event_slot=token_slot;
 assign event_generation=token_generation;assign event_descriptor=meta;
 c2_buffer_manager manager(
 .clk(clk),.rst_n(rst_n),.cmd_valid(manager_valid),.cmd_ready(manager_ready),
 .cmd(request_cmd),.slot(choose_cpu?cpu_slot:token_slot),
 .generation(choose_cpu?cpu_generation:token_generation),
 .descriptor(meta),.rsp_valid(manager_rsp_valid),.rsp_ready(manager_rsp_ready),
 .rsp_status(manager_status),.rsp_slot(manager_slot),.rsp_generation(manager_generation),
 .rsp_descriptor(manager_descriptor),.slot_states(slot_states),.dropped(dropped));
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin state<=IDLE;meta<=0;base<=0;token_generation<=0;
     token_slot<=0;status<=0;route_cpu<=0;prefer_cpu<=0;
   end else begin
     if(manager_valid && manager_ready) begin
       route_cpu<=choose_cpu;prefer_cpu<=!choose_cpu;
       if(choose_internal) case(state)
         ASEND: state<=AWAIT;
         CSEND: state<=CWAIT;
         BSEND: state<=BWAIT;
       endcase
     end
     case(state)
       IDLE: if(frame_valid && frame_ready) begin
         meta<=frame_descriptor;base<=shared_base;status<=0;token_slot<=0;token_generation<=0;
         if(shared_base[15:0]!=0 || frame_descriptor[31:0]!=32'h10000) begin
           status<=3;state<=EVENT;
         end else state<=ASEND;
       end
       AWAIT: if(manager_rsp_valid && !route_cpu) begin
         if(manager_status!=0) begin status<={1'b0,manager_status};state<=EVENT;end
         else begin
           token_slot<=manager_slot;token_generation<=manager_generation;
           meta[127:96]<={31'b0,manager_slot};
           meta[159:128]<=manager_slot?32'h4000:32'h1000;
           meta[191:160]<=9216;meta[223:192]<=1;meta[255:224]<=96;
           state<=WSTART;
         end
       end
       WSTART: if(write_start_valid && write_start_ready) state<=WWAIT;
       WWAIT: if(write_done_valid && write_done_ready) begin
         if(write_done_error) begin status<=4;state<=BSEND;end
         else begin meta[287:256]<=write_checksum;meta[288]<=1;state<=CSEND;end
       end
       CWAIT: if(manager_rsp_valid && !route_cpu) begin
         if(manager_status==0) begin status<=0;state<=EVENT;end
         else begin status<={1'b0,manager_status};state<=BSEND;end
       end
       BWAIT: if(manager_rsp_valid && !route_cpu) begin
         if(manager_status!=0) status<={1'b0,manager_status};
         state<=EVENT;
       end
       EVENT: if(event_valid && event_ready) state<=IDLE;
     endcase
   end
 end
endmodule

