`timescale 1ns/1ps
// APB3 (16-bit byte address, 32-bit data), posted doorbell + explicit ACK.
// One outstanding command; complete response snapshot crosses via mailbox.
module c2_apb_control #(parameter REQUIRE_SOURCE_COMPLETION=0,
 parameter integer TIME_CLOCK_HZ=100000000, parameter [31:0] TIME_INITIAL_MS=0,
 parameter [31:0] SHARED_BASE=32'h09010000,VIDEO_BASE=32'h08010000,VIDEO_BYTES=32'h01000000
)(
 input wire arst_n,pclk,mem_clk,video_clk,
 output wire [31:0] shared_video_ms,output wire shared_video_valid,
 input wire [15:0] paddr,input wire psel,penable,pwrite,input wire [31:0] pwdata,
 output wire pready,output reg [31:0] prdata,output reg pslverror,output wire irq,
 input wire map_enable,
 output wire cpu_valid,input wire cpu_ready,output wire [2:0] cpu_cmd,
 output wire cpu_slot,output wire [31:0] cpu_generation,
 input wire cpu_rsp_valid,output wire cpu_rsp_ready,input wire [1:0] cpu_rsp_status,
 input wire cpu_rsp_slot,input wire [31:0] cpu_rsp_generation,input wire [511:0] cpu_descriptor,
 input wire [3:0] slot_states,input wire [31:0] dropped,input wire protocol_error
);
 wire [31:0] shared_ms;wire shared_valid;
 c2_shared_time #(.CLOCK_HZ(TIME_CLOCK_HZ),.INITIAL_MS(TIME_INITIAL_MS)) clock_service(
 .arst_n(arst_n),.pclk(pclk),.video_clk(video_clk),.cpu_ms(shared_ms),.cpu_valid(shared_valid),
 .video_ms(shared_video_ms),.video_valid(shared_video_valid));
 reg [1:0] released;
 reg busy,done,request_valid;
 reg [31:0] generation;
 reg [35:0] request;
 wire request_ready,response_valid;wire [583:0] response;
 reg [583:0] saved;
 wire access=psel && penable;
 wire aligned=paddr[1:0]==0;
 wire allowed_cmd=(pwdata[2:0]==3 || pwdata[2:0]==4 || pwdata[2:0]==5) && (pwdata&32'hfffffef8)==0;
 wire [35:0] received_command;
 always @(posedge pclk or negedge arst_n)
   if(!arst_n) released<=0;else released<={released[0],1'b1};
 assign pready=released[1];assign irq=done;
 c2_cdc_mailbox #(.WIDTH(36)) command_cdc(.arst_n(arst_n),.s_clk(pclk),
   .s_valid(request_valid),.s_ready(request_ready),.s_data(request),.d_clk(mem_clk),
   .d_valid(cpu_valid),.d_ready(cpu_ready),.d_data(received_command));
 assign {cpu_generation,cpu_slot,cpu_cmd}=received_command;
 c2_cdc_mailbox #(.WIDTH(584)) response_cdc(.arst_n(arst_n),.s_clk(mem_clk),
   .s_valid(cpu_rsp_valid),.s_ready(cpu_rsp_ready),
   .s_data({protocol_error,dropped,slot_states,cpu_rsp_generation,cpu_rsp_slot,cpu_rsp_status,cpu_descriptor}),
   .d_clk(pclk),.d_valid(response_valid),.d_ready(busy && !done),.d_data(response));
 always @* begin
   prdata=0;pslverror=0;
   if(!aligned) pslverror=1;
   else if(pwrite) case(paddr)
     16'h000c: if(busy || done || !allowed_cmd || !map_enable) pslverror=1;
     16'h0010: if(busy || done) pslverror=1;
     16'h0014: if(pwdata!=1 || !done) pslverror=1;
     default: pslverror=1;
   endcase
   else case(paddr)
     16'h0000: prdata=32'h43325332;
     16'h0004: prdata=32'h00020002;
     16'h0008: prdata={30'b0,done,busy};
     16'h0010: prdata=generation;
     16'h0018: prdata={23'b0,saved[514],6'b0,saved[513:512]};
     16'h001c: prdata=saved[546:515];
     16'h0020: prdata={28'b0,saved[550:547]};
     16'h0024: prdata=saved[582:551];
     16'h0028: prdata={31'b0,saved[583]};
     16'h002c: prdata={31'b0,map_enable};
     16'h0030: prdata=SHARED_BASE;
     16'h0034: prdata=32'h00010000;
     16'h0038: prdata=VIDEO_BASE;
     16'h003c: prdata=VIDEO_BYTES;
     16'h0080: prdata=REQUIRE_SOURCE_COMPLETION?32'd7:32'd5;
     16'h0084: prdata=shared_ms;
     16'h0088: prdata={31'b0,shared_valid};
     16'h008c: prdata=32'(TIME_CLOCK_HZ);
     16'h0090: prdata=32'd1;
     default: if(paddr>=16'h0040 && paddr<=16'h007c) prdata=saved[(paddr[5:2])*32+:32];
              else pslverror=1;
   endcase
   if(!access) pslverror=0;
 end
 always @(posedge pclk or negedge arst_n) begin
   if(!arst_n) begin busy<=0;done<=0;request_valid<=0;request<=0;generation<=0;saved<=0;end
   else begin
     if(request_valid && request_ready) request_valid<=0;
     if(response_valid && busy && !done) begin saved<=response;busy<=0;done<=1;end
     if(access && pready && pwrite && !pslverror) case(paddr)
       16'h000c: begin request<={generation,pwdata[8],pwdata[2:0]};request_valid<=1;busy<=1;end
       16'h0010: generation<=pwdata;
       16'h0014: done<=0;
     endcase
   end
 end
endmodule
