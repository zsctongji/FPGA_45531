`timescale 1ns/1ps
module tb_stage_counter;
 reg clk=0,rst=0,run=0,de=0;always #5 clk=~clk;
 wire [23:0] value;c9_stage_counter counter(clk,rst,run,de,value);
 initial begin
  repeat(3)@(negedge clk);rst=1;de=1;
  repeat(5)@(negedge clk);if(value!=0)$fatal(1,"Counted before RUN");
  run=1;repeat(2100)@(negedge clk);
  if(value[22:12]!=2047 || value[11:0]!=1)$fatal(1,"Run saturation failed");
  de=0;@(negedge clk);
  repeat(4100)begin de=1;@(negedge clk);de=0;@(negedge clk);end
  if(value[11:0]!=4095 || value[22:12]!=2047)$fatal(1,"Segment saturation/wrap");
  run=0;@(negedge clk);if(value!=0)$fatal(1,"RUN clear failed");
  run=1;de=1;repeat(4)@(negedge clk);if(value[22:12]!=4 || value[11:0]!=1)$fatal(1,"Restart failed");
  rst=0;#1;if(value!=0)$fatal(1,"Async reset failed");
  $display("PASS tb_stage_counter run_qualification saturation_no_wrap restart async_reset");$finish;
 end
endmodule
