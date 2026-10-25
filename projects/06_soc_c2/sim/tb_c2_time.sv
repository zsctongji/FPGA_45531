`timescale 1ns/1ps
module tb_c2_time #(parameter P_HALF=5,VIDEO_HALF=7);
 reg arst_n=1,pclk=0,vclk=0;
 always #(P_HALF) pclk=~pclk;
 always #(VIDEO_HALF) vclk=~vclk;
 reg [15:0] paddr=0;reg psel=0,penable=0,pwrite=0;
 wire pready,pslverror,valid;wire [31:0] prdata,video_ms;
 c2_apb_control #(.TIME_CLOCK_HZ(10000),.TIME_INITIAL_MS(32'hfffffffc)) dut(
 .arst_n(arst_n),.pclk(pclk),.mem_clk(pclk),.video_clk(vclk),
 .shared_video_ms(video_ms),.shared_video_valid(valid),
 .paddr(paddr),.psel(psel),.penable(penable),.pwrite(pwrite),.pwdata(32'b0),
 .pready(pready),.prdata(prdata),.pslverror(pslverror),.irq(),.map_enable(1'b0),
 .cpu_valid(),.cpu_ready(1'b0),.cpu_cmd(),.cpu_slot(),.cpu_generation(),
 .cpu_rsp_valid(1'b0),.cpu_rsp_ready(),.cpu_rsp_status(2'b0),.cpu_rsp_slot(1'b0),
 .cpu_rsp_generation(32'b0),.cpu_descriptor(512'b0),.slot_states(4'b0),.dropped(32'b0),.protocol_error(1'b0));
 integer checks=0,video_checks=0,ticks=0,wraps=0,epochs=0;
 reg [31:0] expected=32'hfffffffc,last_video=32'hfffffffc,value;
 reg have_video=0;
 always @(posedge pclk or negedge arst_n) begin
  if(!arst_n) begin expected=32'hfffffffc;ticks=0;end
  else begin
   if(dut.clock_service.cpu_valid) begin
    ticks=ticks+1;
    if(ticks==10) begin ticks=0;if(expected==32'hffffffff) wraps=wraps+1;expected=expected+1'b1;end
   end
   #1;
   if(dut.clock_service.cpu_ms!==expected) $fatal(1,"Counter/divider/epoch mismatch");
   checks=checks+1;
  end
 end
 always @(negedge vclk or negedge arst_n) begin
  if(!arst_n) begin have_video=0;last_video=32'hfffffffc;end
  else if(valid) begin
   if(have_video && (video_ms-last_video)>=32'h80000000) $fatal(1,"Video time went backwards or tore");
   if((dut.clock_service.cpu_ms-video_ms)>32'(8+(VIDEO_HALF*8)/(P_HALF*10)))
    $fatal(1,"Video snapshot future/stale cpu=%h video=%h",dut.clock_service.cpu_ms,video_ms);
   have_video=1;last_video=video_ms;video_checks=video_checks+1;
  end
 end
 task apb(input bit wr,input [15:0] address,input bit error);
  begin
   @(negedge pclk);psel=1;penable=0;pwrite=wr;paddr=address;
   @(negedge pclk);penable=1;
   do @(posedge pclk);while(!pready);
   if(pslverror!==error) $fatal(1,"Time APB error response %h",address);
   value=prdata;
   if(!wr && address==16'h84 && value!==expected) $fatal(1,"APB CPU time differs from sole counter");
   @(negedge pclk);psel=0;penable=0;pwrite=0;
  end
 endtask
 task reset_epoch;
  begin
   @(negedge pclk);arst_n=0;#1;
   if(valid || dut.clock_service.cpu_valid) $fatal(1,"Reset did not invalidate both clocks");
   #(P_HALF*3+1);arst_n=1;epochs=epochs+1;
   wait(valid);repeat(4) @(negedge vclk);
  end
 endtask
 initial begin
  #1;arst_n=0;#23;arst_n=1;epochs=epochs+1;
  wait(valid);
  apb(0,16'h80,0);if(value!=5) $fatal(1,"Shared time capability missing");
  apb(0,16'h8c,0);if(value!=10000) $fatal(1,"Time clock frequency metadata");
  apb(0,16'h90,0);if(value!=1) $fatal(1,"Time source identity");
  apb(0,16'h88,0);if(value!=1) $fatal(1,"Time status invalid");
  repeat(20) apb(0,16'h84,0);
  apb(1,16'h84,1);apb(1,16'h88,1);apb(1,16'h8c,1);apb(1,16'h90,1);
  repeat(100) @(negedge vclk);
  // Reset while a snapshot is held/in flight; no old epoch survives.
  wait(dut.clock_service.snapshots.req!=dut.clock_service.snapshots.ack);
  reset_epoch();
  repeat(100) @(negedge vclk);
  apb(0,16'h84,0);
  if(wraps<2 || video_checks<20) $fatal(1,"Insufficient wrap/reset/CDC coverage");
  $display("PASS tb_c2_time checks=%0d video_snapshots=%0d wraps=%0d epochs=%0d APB_single_clock coherent_CDC readonly rollover common_reset",checks,video_checks,wraps,epochs);
  $finish;
 end
 initial begin #1000000;$fatal(1,"Time test timeout");end
endmodule
