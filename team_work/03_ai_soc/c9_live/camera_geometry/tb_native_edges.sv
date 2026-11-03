`timescale 1ns/1ps
module tb_native_edges;
 reg clk=0,rst=0,enable=0,vs=1,hs=0,de=0;always #5 clk=~clk;
 wire [31:0] counts;wire [7:0] flags;
 c9_native_edges dut(clk,rst,enable,vs,hs,de,6'h2b,2'd0,4'd4,16'd2400,counts,flags);
 initial begin
  repeat(3)@(negedge clk);rst=1;repeat(3)@(negedge clk);enable=1;
  repeat(5)@(negedge clk);if(counts!=0 || !flags[7] || !flags[2])$fatal(1,"Invented edge on enabling high level");
  vs=0;@(negedge clk);vs=1;de=1;hs=1;@(negedge clk);
  if(counts!=32'h00010001 || flags[5:0]!=15)$fatal(1,"Edge/metadata evidence wrong %h %h",counts,flags);
  enable=0;@(negedge clk);if(counts || flags[5:0])$fatal(1,"Enable clear failed");
  rst=0;#1;if(counts)$fatal(1,"Reset failed");
  $display("PASS tb_native_edges exact_rises_falls no_fake_enable_edge metadata same_domain reset");$finish;
 end
endmodule
