`timescale 1ns/1ps
// Native-pixel-clock AXI-Lite startup cleanup. ISR[14:2] is W1C; FIFO empty
// is informational. Read back after clearing; never silently mask fresh errors.
module c9_csi_capture_gate #(parameter TIMEOUT=1000000)(
 input wire clk,arst_n,run,input wire [31:0] debug,
 output wire [5:0] awaddr,output wire awvalid,input wire awready,
 output wire [31:0] wdata,output wire wvalid,input wire wready,
 input wire bvalid,output wire bready,
 output wire [5:0] araddr,output wire arvalid,input wire arready,
 input wire [31:0] rdata,input wire rvalid,output wire rready,
 output wire capture_enable,output wire fault,output wire [159:0] observation
);
 localparam INIT=0,PRE_ADDR=1,PRE_DATA=2,CLEAR=3,BRESP=4,POST_ADDR=5,POST_DATA=6,DONE=7,FAIL=8;
 reg [3:0] state;reg awsent,wsent,init_seen;
 reg [3:0] retries;reg [19:0] cycles;
 reg [31:0] pre_debug,pre_status,post_status;
 assign awaddr=0;assign araddr=0;assign wdata=32'h00007ffc;
 assign awvalid=state==CLEAR && !awsent && run;
 assign wvalid=state==CLEAR && !wsent && run;
 assign bready=state==BRESP && run;
 assign arvalid=(state==PRE_ADDR || state==POST_ADDR) && run;
 assign rready=(state==PRE_DATA || state==POST_DATA) && run;
 assign capture_enable=state==DONE && run;assign fault=state==FAIL;
 wire [31:0] info={4'b0,state,4'b0,retries,12'b0,fault,capture_enable,init_seen,run};
 assign observation={info,pre_debug,post_status,pre_status,32'hc9f20001};
 always @(posedge clk or negedge arst_n)
  if(!arst_n)begin state<=INIT;awsent<=0;wsent<=0;init_seen<=0;retries<=0;cycles<=0;pre_debug<=0;pre_status<=0;post_status<=0;end
  else if(!run)begin state<=INIT;awsent<=0;wsent<=0;init_seen<=0;retries<=0;cycles<=0;pre_debug<=0;pre_status<=0;post_status<=0;end
  else if(state!=DONE && state!=FAIL)begin
   cycles<=cycles+1'b1;
   if(cycles==TIMEOUT-1)state<=FAIL;
   else case(state)
    INIT:if(debug[15])begin init_seen<=1;pre_debug<=debug;state<=PRE_ADDR;end
    PRE_ADDR:if(arready)state<=PRE_DATA;
    PRE_DATA:if(rvalid)begin pre_status<=rdata;state<=CLEAR;awsent<=0;wsent<=0;end
    CLEAR:begin
     if(awready)awsent<=1;if(wready)wsent<=1;
     if((awsent || awready) && (wsent || wready))state<=BRESP;
    end
    BRESP:if(bvalid)state<=POST_ADDR;
    POST_ADDR:if(arready)state<=POST_DATA;
    POST_DATA:if(rvalid)begin
     post_status<=rdata;
     if((rdata & 32'h00007ffd)==0)state<=DONE;
     else if(retries==7)state<=FAIL;
     else begin retries<=retries+1'b1;awsent<=0;wsent<=0;state<=CLEAR;end
    end
    default:state<=FAIL;
   endcase
  end
endmodule
