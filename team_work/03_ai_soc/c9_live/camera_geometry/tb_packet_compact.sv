`timescale 1ns/1ps
module tb_packet_compact;
 reg clk=0,rst=0,vs=0,hs=0,de=0,fault=0;always #5 clk=~clk;
 reg [15:0] wc=2400;wire [63:0] o;integer n;
 c9_packet_probe dut(clk,rst,vs,hs,de,fault,wc,6'h2b,4'd4,2'd0,o);
 initial begin
  #1;rst=0;repeat(3)@(negedge clk);rst=1;
  for(n=0;n<17;n=n+1)begin vs=1;hs=1;de=1;@(negedge clk);vs=0;hs=0;de=0;@(negedge clk);end
  if(o[63:32]!=32'hc9c20011 || o[27:0]!={2'd0,4'd4,6'h2b,16'd2400} || !o[31])$fatal(1,"modulo/meta %h",o);
  hs=1;de=1;repeat(200)@(negedge clk);if(o[35:32]!=2 || !o[29])$fatal(1,"held HS");
  wc=3000;@(negedge clk);de=0;wc=0;@(negedge clk);if(o[15:0]!=3000)$fatal(1,"last valid metadata");
  fault=1;#1;if(!o[28])$fatal(1,"fault");
  rst=0;#1;if(o[63:32]!=32'hc9c20000 || o[31] || o[27:0]!=0)$fatal(1,"reset");
  $display("PASS tb_packet_compact modulo_16 held_HS last_valid_metadata fault reset");$finish;
 end
endmodule
