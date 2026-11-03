`timescale 1ns/1ps
// Real scanout and real request mailbox, with no framebuffer available at boot.
module tb_scanout_startup #(parameter START_MODE=0);
 reg clk=0,mem_clk=0;always #5 clk=~clk;always #7 mem_clk=~mem_clk;
 reg rst_n=0,vs=0,in_valid=0,consume_req=0;reg [129:0] in_data=0;
 wire scan_valid,scan_ready,req_valid,in_ready,busy,failed;
 wire [31:0] missed,underflows,completed;integer requests=0;
 c2_cdc_mailbox #(.WIDTH(1)) request(.arst_n(rst_n),.s_clk(clk),.s_valid(scan_valid),
  .s_ready(scan_ready),.s_data(1'b0),.d_clk(mem_clk),.d_valid(req_valid),.d_ready(consume_req),.d_data());
 c2_video_scanout #(.WIDTH(16),.HEIGHT(1)) dut(.arst_n(rst_n),.clk(clk),.vs(vs),.de(1'b0),.hs(1'b0),
  .scan_valid(scan_valid),.scan_ready(scan_ready),.in_valid(in_valid),.in_ready(in_ready),.in_data(in_data),
  .rgb(),.out_vs(),.out_de(),.out_hs(),.busy(busy),.frame_available(),.frame_failed(failed),
  .frame_id(),.timestamp_ms(),.underflows(underflows),.missed_scans(missed),.completed_scans(completed));
 always @(posedge clk) if(rst_n && scan_valid && scan_ready) requests=requests+1;
 task edge_vs;begin @(negedge clk);vs=1;@(negedge clk);vs=0;end endtask
 task empty_response;begin
  @(negedge clk);in_valid=1;in_data={2'd1,128'b0};
  @(negedge clk);in_data={2'd2,128'b0};
  @(negedge clk);in_valid=0;in_data=0;
 end endtask
 initial begin
  if(START_MODE==0)vs=1;
  repeat(3)@(negedge clk);rst_n=1;
  if(START_MODE==1)begin @(negedge clk);vs=1;end
  if(START_MODE==2)begin repeat(2)@(negedge clk);vs=1;end
  repeat(7)@(negedge clk);
  if(missed!==0)$fatal(1,"startup false missed_scans mode=%0d missed=%0d",START_MODE,missed);
  if(START_MODE!=2 && (requests!=0 || busy))$fatal(1,"startup VS consumed before initial readiness");
  if(START_MODE==2 && (requests!=1 || !busy))$fatal(1,"first ready VS was lost");
  vs=0;repeat(5)@(negedge clk);
  if(START_MODE!=2)edge_vs();
  repeat(8)@(negedge clk);
  if(requests!=1 || !busy || scan_ready)$fatal(1,"normal scan not accepted or mailbox not backpressured");
  edge_vs();repeat(3)@(negedge clk);
  if(missed!==1 || !failed)$fatal(1,"real busy scan must still count as missed");
  consume_req=1;empty_response();repeat(8)@(negedge clk);
  if(busy || underflows!=0 || completed!=0)$fatal(1,"empty response did not drain cleanly");
  edge_vs();repeat(8)@(negedge clk);
  if(requests!=2 || !busy || missed!=1)$fatal(1,"scan did not recover after real miss");
  empty_response();repeat(6)@(negedge clk);
  $display("PASS scanout startup mode=%0d; first-ready edge, real busy miss and recovery retained",START_MODE);$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
