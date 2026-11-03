`timescale 1ns/1ps
module tb_phy_geometry;
 reg clk=0,rst=0,hs=0,de=0,fault=0;wire [31:0] flags;
 always #5 clk=~clk;
 c9_phy_geometry dut(clk,rst,hs,de,fault,flags);
 task verify(input integer groups,runs,clip,outside);begin
  repeat(2)@(negedge clk);
  if(flags[31:22]!=groups || flags[21:12]!=runs || flags[11]!=1 || flags[10]!=clip || flags[9]!=outside || flags[8:1]!=0 || flags[0]!=fault)
   $fatal(1,"phy geometry flags=%h groups=%0d runs=%0d",flags,groups,runs);
 end endtask
 integer i;
 initial begin
  #1;rst=0;repeat(3)@(negedge clk);rst=1;repeat(3)@(negedge clk);
  if(flags!==0)$fatal(1,"reset");
  hs=1;de=1;repeat(480)@(negedge clk);hs=0;de=0;verify(480,1,0,0);
  hs=1;repeat(2)@(negedge clk);
  for(i=0;i<60;i=i+1)begin de=1;repeat(8)@(negedge clk);de=0;repeat(3)@(negedge clk);end
  hs=0;verify(480,60,0,0);
  // A zero-payload HS does not erase the last real payload-line measurement.
  hs=1;repeat(5)@(negedge clk);hs=0;verify(480,60,0,0);
  hs=1;de=1;repeat(1030)@(negedge clk);de=0;hs=0;verify(1023,1,1,0);
  de=1;@(negedge clk);de=0;fault=1;verify(1023,1,1,1);
  rst=0;#1;if(flags!==1)$fatal(1,"reset status");
  $display("PASS tb_phy_geometry continuous bursty first_cycle empty_hs saturation outside_hs fault_passthrough reset");$finish;
 end
endmodule
