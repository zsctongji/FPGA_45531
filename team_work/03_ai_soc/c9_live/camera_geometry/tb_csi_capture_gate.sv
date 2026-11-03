`timescale 1ns/1ps
module tb_csi_capture_gate #(parameter MODE=0);
 reg clk=0,rst=0,run=0;always #5 clk=~clk;
 reg [31:0] debug=32'h0001c418,status=32'h00004418,wrdata=0,rd=0;
 wire [5:0] awa,ara;wire av,wv,br,ar,rr,enable,fault;wire [31:0] wd;
 reg bv=0,rv=0,aws=0,ws=0;
 integer cycles=0,aw_count=0,w_count=0,read_count=0;
 wire awr=MODE!=1 || cycles>12;wire wr=MODE!=0 || cycles>12;
 wire [159:0] observation;
 c9_csi_capture_gate #(.TIMEOUT(200)) gate(clk,rst,run,debug,awa,av,awr,wd,wv,wr,bv,br,ara,ar,1'b1,rd,rv,rr,enable,fault,observation);
 always @(posedge clk)begin
  if(!rst)begin status<=32'h4418;bv<=0;rv<=0;aws<=0;ws<=0;cycles<=0;aw_count<=0;w_count<=0;read_count<=0;end
  else begin
   cycles<=cycles+1;
   if(av && awr)begin aws<=1;aw_count<=aw_count+1;if(awa!=0)$fatal(1,"Wrong CSR address");end
   if(wv && wr)begin ws<=1;wrdata<=wd;w_count<=w_count+1;if(wd!=32'h7ffc)$fatal(1,"Wrong W1C mask");end
   if(aws && ws && !bv && MODE!=3)begin bv<=1;status<=MODE==2?32'h4418:status&~wrdata;end
   if(bv && br)begin bv<=0;aws<=0;ws<=0;end
   if(ar)begin rv<=1;rd<=status;read_count<=read_count+1;end
   if(rv && rr)rv<=0;
  end
 end
 initial begin
  repeat(3)@(negedge clk);rst=1;run=1;
  if(MODE==4)debug=0;
  repeat(240)@(negedge clk);
  if(MODE<2)begin
   if(!enable || fault || aw_count!=1 || w_count!=1 || read_count!=2 || gate.pre_status!=32'h4418 || gate.post_status!=0)$fatal(1,"Cleanup/AXI failed a=%0d w=%0d r=%0d state=%0d",aw_count,w_count,read_count,gate.state);
   debug[2]=1;status=4;repeat(10)@(negedge clk);
   if(!enable || av || wv || ar)$fatal(1,"Startup gate silently cleared fresh active error");
  end else if(!fault || enable)$fatal(1,"Timeout/persistent error accepted mode=%0d",MODE);
  $display("PASS tb_csi_capture_gate mode=%0d AXI_separate_handshakes_W1C_readback_no_fresh_error_masking",MODE);$finish;
 end
endmodule
