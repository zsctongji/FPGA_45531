`timescale 1ns/1ps
module tb_sideband_small;
 reg clk=0,rst=0,run=0,hs=0,de=0,fault=0;
 always #5 clk=~clk;
 reg [15:0] wc=2400;reg [5:0] dt=6'h2b;reg [3:0] ppc=4;reg [1:0] vc=0;
 wire [63:0] o;c9_sideband_probe dut(clk,rst,run,hs,de,fault,wc,dt,ppc,vc,o);
 task beat(input integer count);begin ppc=count;de=1;@(negedge clk);de=0;@(negedge clk);end endtask
 initial begin
  #1;rst=0;repeat(3)@(negedge clk);rst=1;
  beat(2);if(o[47:32]!=0 || o[31])$fatal(1,"pre-run data recorded");
  #2;run=1;repeat(4)@(negedge clk);hs=1;
  beat(4);beat(2);
  if(o[63:32]!=32'hc9d20014 || o[31:28]!=4'b1000 || o[25:22]!=0 || o[15:0]!=2400)$fatal(1,"valid image mask %h",o);
  dt=6'h12;beat(8);dt=6'h2b;vc=1;beat(1);vc=0;
  if(!o[30] || o[47:32]!=16'h14)$fatal(1,"other type/VC polluted image mask");
  hs=0;beat(4);if(!o[29])$fatal(1,"valid outside HS missing");
  beat(0);if(o[47:32]!=16'h15)$fatal(1,"zero PPC anomaly hidden");
  beat(7);if(o[47:32]!=16'h8015)$fatal(1,"out-of-range PPC hidden");
  de=0;ppc=15;wc=1;repeat(4)@(negedge clk);if(o[15:0]!=2400 || o[47:32]!=16'h8015)$fatal(1,"invalid cycles polluted record");
  fault=1;#1;if(!o[28])$fatal(1,"fault lost");
  run=0;repeat(4)@(negedge clk);if(o[31] || o[47:32]!=0)$fatal(1,"run reset");
  $display("PASS tb_sideband_small RUN_CDC image_PPC_set other_type_VC excluded outside_HS zero_PPC invalid_cycles reset");$finish;
 end
endmodule
