`timescale 1ns/1ps
module tb_packet_probe;
 reg clk=0,rst=0,vs=0,hs=0,de=0,fault=0;
 reg [15:0] wc=2400;reg [5:0] dt=6'h2b;reg [3:0] ppc=4;reg [1:0] vc=0;
 wire [63:0] o;always #5 clk=~clk;
 c9_packet_probe dut(clk,rst,vs,hs,de,fault,wc,dt,ppc,vc,o);
 task frame;begin vs=1;repeat(2)@(negedge clk);vs=0;repeat(2)@(negedge clk);end endtask
 task line;begin hs=1;de=1;repeat(3)@(negedge clk);de=0;hs=0;repeat(3)@(negedge clk);end endtask
 integer n;
 initial begin
  #1;rst=0;repeat(3)@(negedge clk);rst=1;repeat(3)@(negedge clk);
  if(o!==64'h0000000100000000)$fatal(1,"reset %h",o);
  frame();for(n=0;n<1080;n=n+1)line();frame();
  if(o[63:52]!=2 || o[51:40]!=1080 || !o[36] || o[34] || !o[31] || o[30] || o[27:0]!={vc,ppc,dt,wc})$fatal(1,"geometry/meta %h",o);
  // HS held across many sparse payloads counts as one edge, not many lines.
  hs=1;for(n=0;n<1200;n=n+1)begin de=1;@(negedge clk);de=0;@(negedge clk);end
  hs=0;repeat(2)@(negedge clk);frame();if(o[51:40]!=1)$fatal(1,"HS semantics");
  wc=100;de=1;fault=1;@(negedge clk);de=0;@(negedge clk);
  if(o[31:28]!=4'b1111 || o[15:0]!=100)$fatal(1,"metadata change/outside/fault");
  for(n=0;n<4100;n=n+1)begin hs=1;@(negedge clk);hs=0;@(negedge clk);end
  frame();if(o[51:40]!=4095 || !o[34])$fatal(1,"HS saturation");
  for(n=0;n<4100;n=n+1)frame();if(o[63:52]!=4095 || !o[35])$fatal(1,"VS saturation");
  rst=0;#1;if(o[63:32]!=1 || o[31:28]!=1)$fatal(1,"reset fault passthrough");
  $display("PASS tb_packet_probe 1080_lines held_HS metadata changes outside_HS saturation reset");$finish;
 end
endmodule
