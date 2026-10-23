`timescale 1ns/1ps
module tb_sensor_smooth;
  reg clk=0, rst=1, sample_valid=0;
  reg signed [15:0] sample_data=0;
  wire out_valid, rejected;
  wire signed [15:0] mean_data;
  integer checks=0;
  always #5 clk=~clk;
  sensor_smooth dut(clk,rst,sample_valid,sample_data,out_valid,rejected,mean_data);
  task sample(input integer value, input integer expected, input bit reject_sample);
    begin
      @(negedge clk); sample_valid=1; sample_data=value;
      @(posedge clk); #1;
      if (rejected !== reject_sample || out_valid !== !reject_sample)
        $fatal(1,"FAIL smooth flags value=%0d",value);
      if (!reject_sample && $signed(mean_data) !== expected)
        $fatal(1,"FAIL smooth mean value=%0d expected=%0d actual=%0d",value,expected,$signed(mean_data));
      checks=checks+1;
      @(negedge clk); sample_valid=0;
      @(posedge clk); #1;
      if (out_valid || rejected) $fatal(1,"FAIL smooth bubble");
    end
  endtask
  initial begin
    repeat(3) @(posedge clk);
    @(negedge clk); rst=0;
    sample(2000,2000,0);
    sample(2200,2100,0);
    sample(2400,2200,0);
    sample(2600,2300,0);
    sample(2800,2500,0);
    sample(9000,0,1);
    sample(3000,2700,0);
    sample(-5000,0,1);
    sample(13000,0,1);
    // Reset flushes rejected/accepted state. Exercise signed division.
    @(negedge clk); rst=1;
    @(posedge clk); #1;
    if (out_valid || rejected || mean_data !== 0) $fatal(1,"FAIL smooth reset");
    @(negedge clk); rst=0;
    sample(-101,-101,0);
    sample(-100,-100,0);
    sample(100,-33,0);
    sample(101,0,0);
    sample(200,75,0);
    // Back-to-back accepted samples must produce each result.
    @(negedge clk); sample_valid=1; sample_data=300;
    @(posedge clk); #1;
    if (!out_valid || rejected || mean_data !== 175) $fatal(1,"FAIL smooth consecutive 1");
    @(negedge clk); sample_data=400;
    @(posedge clk); #1;
    if (!out_valid || rejected || mean_data !== 250) $fatal(1,"FAIL smooth consecutive 2");
    @(negedge clk); sample_valid=0;
    rst=1;
    @(posedge clk); #1;
    @(negedge clk); rst=0;
    sample(-4001,0,1);
    sample(-4000,-4000,0);
    sample(-2000,-3000,0);
    sample(0,-2000,0);
    sample(2001,0,1);
    sample(2000,-1000,0);
    sample(4000,1000,0);
    sample(6000,3000,0);
    sample(8000,5000,0);
    sample(10000,7000,0);
    sample(12000,9000,0);
    sample(12500,10625,0);
    sample(12501,0,1);
    $display("PASS tb_sensor_smooth checks=%0d plus consecutive cases",checks);
    $finish;
  end
  initial begin #100000; $fatal(1,"FAIL smooth timeout"); end
endmodule
