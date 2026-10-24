`timescale 1ns/1ps
module tb_c2_cache;
reg clk=0,reset=1,flush=0;wire ready,mem_valid;
always #5 clk=~clk;
DataCache_ba6762f3781649428952cf46a6343376 dut(
.io_cpu_execute_isValid(1'b0),
.io_cpu_execute_address(32'b0),
.io_cpu_execute_haltIt(),
.io_cpu_execute_args_wr(1'b0),
.io_cpu_execute_args_size(2'b0),
.io_cpu_execute_args_totalyConsistent(1'b0),
.io_cpu_execute_refilling(),
.io_cpu_memory_isValid(1'b0),
.io_cpu_memory_isStuck(1'b0),
.io_cpu_memory_isWrite(),
.io_cpu_memory_address(32'b0),
.io_cpu_memory_mmuRsp_physicalAddress(32'b0),
.io_cpu_memory_mmuRsp_isIoAccess(1'b0),
.io_cpu_memory_mmuRsp_isPaging(1'b0),
.io_cpu_memory_mmuRsp_allowRead(1'b0),
.io_cpu_memory_mmuRsp_allowWrite(1'b0),
.io_cpu_memory_mmuRsp_allowExecute(1'b0),
.io_cpu_memory_mmuRsp_exception(1'b0),
.io_cpu_memory_mmuRsp_refilling(1'b0),
.io_cpu_memory_mmuRsp_bypassTranslation(1'b0),
.io_cpu_writeBack_isValid(1'b0),
.io_cpu_writeBack_isStuck(1'b0),
.io_cpu_writeBack_isFiring(1'b0),
.io_cpu_writeBack_isUser(1'b0),
.io_cpu_writeBack_haltIt(),
.io_cpu_writeBack_isWrite(),
.io_cpu_writeBack_storeData(32'b0),
.io_cpu_writeBack_data(),
.io_cpu_writeBack_address(32'b0),
.io_cpu_writeBack_mmuException(),
.io_cpu_writeBack_unalignedAccess(),
.io_cpu_writeBack_accessError(),
.io_cpu_writeBack_keepMemRspData(),
.io_cpu_writeBack_fence_SW(1'b0),
.io_cpu_writeBack_fence_SR(1'b0),
.io_cpu_writeBack_fence_SO(1'b0),
.io_cpu_writeBack_fence_SI(1'b0),
.io_cpu_writeBack_fence_PW(1'b0),
.io_cpu_writeBack_fence_PR(1'b0),
.io_cpu_writeBack_fence_PO(1'b0),
.io_cpu_writeBack_fence_PI(1'b0),
.io_cpu_writeBack_fence_FM(4'b0),
.io_cpu_writeBack_exclusiveOk(),
.io_cpu_redo(),
.io_cpu_flush_valid(flush),
.io_cpu_flush_ready(ready),
.io_cpu_flush_payload_singleLine(1'b0),
.io_cpu_flush_payload_lineId(5'b0),
.io_cpu_writesPending(),
.io_mem_cmd_valid(mem_valid),
.io_mem_cmd_ready(1'b1),
.io_mem_cmd_payload_wr(),
.io_mem_cmd_payload_uncached(),
.io_mem_cmd_payload_address(),
.io_mem_cmd_payload_data(),
.io_mem_cmd_payload_mask(),
.io_mem_cmd_payload_size(),
.io_mem_cmd_payload_last(),
.io_mem_rsp_valid(1'b0),
.io_mem_rsp_payload_last(1'b0),
.io_mem_rsp_payload_data(32'b0),
.io_mem_rsp_payload_error(1'b0),
.io_systemClk(clk),
.systemCd_logic_outputReset(reset));
integer i,round,cycles;
initial begin
 repeat(5) @(negedge clk);reset=0;
 repeat(100) @(negedge clk);
 for(round=0;round<3;round=round+1) begin
  // Test fixture seeds valid tags; the unmodified vendor flusher clears them.
  for(i=0;i<32;i=i+1) begin dut.ways_0_tags[i]=23'h12345;dut.ways_1_tags[i]=23'h23457;end
  flush=1;cycles=0;
  do begin @(posedge clk);cycles=cycles+1;end while(!ready);
  @(negedge clk);flush=0;
  if(cycles<32) $fatal(1,"Whole-cache flush completed prematurely");
  for(i=0;i<32;i=i+1)
   if(dut.ways_0_tags[i][0]!==0 || dut.ways_1_tags[i][0]!==0) $fatal(1,"Vendor cache tag still valid");
  repeat(8) @(negedge clk);
 end
 $display("PASS tb_c2_cache vendor_DataCache ways=2 sets=32 rounds=3 invalidate_all_tags CPU_instruction_execution_not_simulated");
 $finish;
end
always @(posedge clk) if(!reset && mem_valid) $fatal(1,"Flush unexpectedly issued a DDR operation");
initial begin #100000;$fatal(1,"Cache flush timeout");end
endmodule
