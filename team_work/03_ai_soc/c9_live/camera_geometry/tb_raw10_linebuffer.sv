`timescale 1ns/1ps
module tb_raw10_linebuffer #(parameter CASE=0);
 reg clk=0,rst=0,run=0,vs=0,de=0,transport=0;
 always #10 clk=~clk;
 reg [31:0] data=0;reg [15:0] wc=2400;reg [3:0] ppc=4;reg [1:0] vc=0;
 wire ov,oh,od,fault,armed;wire [31:0] outdata;wire [6:0] errors;
 wire [18:0] last_beats;wire [15:0] frames,lines;
 c9_raw10_linebuffer #(.HEIGHT(4),.GAP_LIMIT(64)) dut(clk,rst,run,vs,de,data,wc,6'h2b,vc,ppc,transport,
  ov,oh,od,outdata,fault,armed,errors,last_beats,frames,lines);
 reg [31:0] expected[0:9999];integer sent=0,got=0,vscount=0,current_run=0,maxrun=0;
 reg oldvs=0;integer y,x,k;
 always @(posedge clk)begin
  if(!rst)begin sent=0;got=0;vscount=0;current_run=0;maxrun=0;oldvs=0;end
  else begin
   if(dut.take)begin expected[sent]=data;sent=sent+1;end
   if(od)begin
    if(ov || !oh || got>=sent || outdata!==expected[got])$fatal(1,"Pixel/control/order mismatch %0d %h %h",got,outdata,expected[got]);
    got=got+1;current_run=current_run+1;if(current_run>maxrun)maxrun=current_run;
   end else begin
    if((CASE==0 || CASE==8 || CASE==9) && current_run!=0 && current_run!=480)$fatal(1,"Partial line escaped %0d",current_run);
    current_run=0;
   end
   if(ov && !oldvs)vscount=vscount+1;
   oldvs=ov;
  end
 end
 task boundary;
  begin vs=1;repeat(5)@(negedge clk);vs=0;repeat(40)@(negedge clk);end
 endtask
 task row(input integer length,input integer gapped);
  begin
   for(x=0;x<length;x=x+1)begin
    if(gapped && x>0 && x%18==0)begin de=0;repeat(1+x%3)@(negedge clk);end
    de=1;data=data+1;@(negedge clk);
   end
   de=0;if(gapped)repeat(20)@(negedge clk);
  end
 endtask
 task good;
  begin boundary();for(y=0;y<4;y=y+1)row(480,1);end
 endtask
 initial begin
  repeat(4)@(negedge clk);rst=1;repeat(4)@(negedge clk);run=1;repeat(10)@(negedge clk);
  if(CASE==9)begin de=1;repeat(23)@(negedge clk);de=0;if(armed || sent || od)$fatal(1,"Started mid-frame");end
  boundary();
  case(CASE)
   0,9:begin for(k=0;k<3;k=k+1)begin for(y=0;y<4;y=y+1)row(480,1);boundary();end end
   1:begin wc=2395;row(480,1);end
   2:begin ppc=2;row(480,1);end
   3:begin row(479,1);boundary();end
   4:begin for(y=0;y<4;y=y+1)row(480,1);row(1,1);end
   5:begin row(12,0);repeat(80)@(negedge clk);end
   6:begin for(y=0;y<4;y=y+1)row(480,0);end
   7:begin for(y=0;y<4;y=y+1)row(480,1);vs=1;@(negedge clk);vs=0;transport=1;end
   8:begin
    wc=2395;row(1,1);repeat(5)@(negedge clk);if(!fault)$fatal(1,"Missing initial fault");
    rst=0;run=0;repeat(3)@(negedge clk);rst=1;wc=2400;run=1;repeat(10)@(negedge clk);
    for(k=0;k<3;k=k+1)good();boundary();
   end
   10:begin vc=1;row(480,1);end
  endcase
  de=0;repeat(2000)@(negedge clk);
  if(CASE==0 || CASE==8 || CASE==9)begin
   if(fault || got!=5760 || vscount!=4 || maxrun!=480 || last_beats!=1920 || frames!=3 || lines!=12)
    $fatal(1,"Good completion fault=%h sent=%0d got=%0d vs=%0d max=%0d count=%0d frames=%0d lines=%0d",errors,sent,got,vscount,maxrun,last_beats,frames,lines);
  end else begin
   if(!fault || vscount>1)$fatal(1,"Bad frame released closing boundary errors=%h vs=%0d",errors,vscount);
   case(CASE)
    1,10:if(!errors[1])$fatal(1,"Missing metadata error");
    2:if(!errors[2])$fatal(1,"Missing PPC error");
    3,4:if(!errors[3])$fatal(1,"Missing frame size error");
    5:if(!errors[6])$fatal(1,"Missing timeout");
    6:if(!errors[0])$fatal(1,"Missing overflow");
    7:if(!errors[4])$fatal(1,"Missing transport error");
   endcase
  end
  $display("PASS tb_raw10_linebuffer case=%0d words=%0d vs=%0d errors=%h",CASE,got,vscount,errors);$finish;
 end
 initial begin #10000000;$fatal(1,"Linebuffer timeout");end
endmodule
