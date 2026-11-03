`timescale 1ns/1ps
module tb_c2_pool;
 reg clk=0,rst_n=0,cmd_valid=0,rsp_ready=0,slot=0;
 reg [2:0] cmd=0;reg [31:0] generation=0;reg [511:0] descriptor=0;
 wire cmd_ready,rsp_valid,rsp_slot;wire [1:0] rsp_status;
 wire [31:0] rsp_generation,dropped;wire [511:0] rsp_descriptor;wire [3:0] states;
 reg a,b;reg [31:0] ga,gb;integer i,calls=0;
 reg [511:0] hold_meta;
 c2_buffer_manager dut(clk,rst_n,cmd_valid,cmd_ready,cmd,slot,generation,descriptor,
  rsp_valid,rsp_ready,rsp_status,rsp_slot,rsp_generation,rsp_descriptor,states,dropped);
 always #5 clk=~clk;
 function [511:0] meta(input bit id,input integer frame);
   reg [511:0] f;begin
     f=0;f[31:0]=32'h10000;f[63:32]=frame;f[127:96]=id;
     f[159:128]=id?32'h4000:32'h1000;f[191:160]=9216;f[223:192]=1;
     f[255:224]=96;f[319:288]=1;meta=f;
   end
 endfunction
 task request(input [2:0] op,input bit id,input [31:0] gen,input [511:0] f,input [1:0] expected);
   begin
     @(negedge clk);cmd_valid=1;cmd=op;slot=id;generation=gen;descriptor=f;rsp_ready=0;
     do @(posedge clk);while(!cmd_ready);
     @(negedge clk);cmd_valid=0;
     while(!rsp_valid) @(negedge clk);
     if(rsp_status!==expected) $fatal(1,"Pool op=%d got=%d expected=%d",op,rsp_status,expected);
     calls=calls+1;
     if(op==0 && expected==0) begin
       if(!rsp_slot) begin a=rsp_slot;ga=rsp_generation;end
       else begin b=rsp_slot;gb=rsp_generation;end
     end
     hold_meta=rsp_descriptor;
     repeat(3) begin @(negedge clk);
       if(!rsp_valid || rsp_descriptor!==hold_meta || cmd_ready) $fatal(1,"Pool response not held");
     end
     rsp_ready=1;@(negedge clk);rsp_ready=0;
   end
 endtask
 initial begin
   #21;rst_n=1;
   request(0,0,0,0,0);request(0,0,0,0,0);
   request(0,0,0,0,1);
   request(1,a,ga,meta(a,10),0);
   request(3,a,ga,0,0);
   request(4,a,ga+1,0,2);
   if(states[1:0]!=3) $fatal(1,"Stale generation released current reader");
   request(0,0,0,0,1);
   request(1,b,gb,0,3);
   request(1,b,gb,meta(b,11),0);
   request(3,b,gb,0,0);
   request(4,b,gb,0,0);request(4,a,ga,0,0);
   for(i=0;i<100;i=i+1) begin
     request(0,0,0,0,0);request(1,a,ga,meta(a,i),0);
     request(3,a,ga,0,0);request(4,a,ga-1,0,2);request(4,a,ga,0,0);
   end
   request(0,0,0,0,0);request(2,a,ga,0,0);
   if(dropped!=2) $fatal(1,"Drop counter incorrect");
   @(negedge clk);rst_n=0;#13;rst_n=1;
   repeat(3) @(negedge clk);
   if(states!=0 || rsp_valid || dropped!=0) $fatal(1,"Pool reset failed");
   $display("PASS tb_c2_pool commands=%0d dual_slots generation ownership response_backpressure reset",calls);
   $finish;
 end
 initial begin #200000;$fatal(1,"Pool timeout");end
endmodule

