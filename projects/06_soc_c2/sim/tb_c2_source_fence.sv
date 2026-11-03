`timescale 1ns/1ps
module tb_c2_source_fence;
 reg clk=0,rst=0,start=0,wv=0,sv=0,we=0,se=0,dr=0;
 reg [31:0] id=0,sid=0,wh=0,sh=0;wire wr,sr,dv,de;wire [31:0] dh;
 always #5 clk=~clk;
 c2_source_fence dut(clk,rst,start,id,wv,wr,we,wh,sv,sr,se,sid,sh,dv,dr,de,dh);
 task writer;begin @(negedge clk);wv=1;do @(posedge clk);while(!wr);@(negedge clk);wv=0;end endtask
 task source;begin @(negedge clk);sv=1;do @(posedge clk);while(!sr);@(negedge clk);sv=0;end endtask
 integer i;
 initial begin
 #23;rst=1;
 for(i=0;i<8;i=i+1) begin
  @(negedge clk);id=i;sid=i;wh=32'h12340000+i;sh=wh;we=0;se=0;
  if(i==2) sid=i-1;if(i==3) sh=wh+1;if(i==4) we=1;if(i==5) se=1;
  start=1;@(negedge clk);start=0;
  if(i%2) source();else writer();
  repeat(12) begin @(negedge clk);if(dv) $fatal(1,"Published on only one completion");end
  if(i%2) writer();else source();
  repeat(8) begin @(negedge clk);
   if(!dv || de!==(i>=2 && i<=5) || dh!==wh) $fatal(1,"Fence payload/error/stall mismatch");
  end
  dr=1;@(negedge clk);dr=0;
 end
 // Reset cancels half a completion; it may never match the next frame.
 @(negedge clk);start=1;@(negedge clk);start=0;writer();
 rst=0;#19;rst=1;repeat(10) @(negedge clk);
 if(dv || wr || sr) $fatal(1,"Ghost source verdict after reset");
 $display("PASS tb_c2_source_fence cases=8 both_orders delayed_verdict frame_id FNV errors stable_response common_reset");$finish;
 end
 initial begin #100000;$fatal(1,"Fence timeout");end
endmodule
