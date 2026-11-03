`timescale 1ns/1ps
module tb_c9_control;
 reg p=0,m=0,v=0,d=0,c=0,h=0,reset_n=0,phy_running=1;
 always #5 p=~p;always #7 m=~m;always #3 v=~v;always #11 d=~d;always #29 c=~c;
 always #13 if(phy_running)h=~h;
 reg [31:0] mc=0,vc=0,dc=0,cc=0,hc=0;
 always @(posedge m)mc<=mc+1;always @(posedge v)vc<=vc+1;always @(posedge d)dc<=dc+1;always @(posedge c)cc<=cc+1;always @(posedge h)hc<=hc+1;
 reg [7:0] addr=0;reg sel=0,en=0,write=0;reg [31:0] wd=0;wire ready,err;wire [31:0] rd;
 wire run,mode,pvalid;wire [7:0] pg;integer commands=0;reg [7:0] last_gray;
 always @(posedge v)if(pvalid)begin commands<=commands+1;last_gray<=pg;end
 c9_live_control dut(.arst_n(reset_n),.pclk(p),.mem_clk(m),.video_clk(v),.display_clk(d),.camera_clk(c),.phy_clk(h),
 .paddr(addr),.psel(sel),.penable(en),.pwrite(write),.pwdata(wd),.pready(ready),.prdata(rd),.pslverror(err),
 .source_run(run),.pattern_mode(mode),.pattern_valid(pvalid),.pattern_ready(1'b1),.pattern_gray(pg),
 .mem_data({mc+32'h70000000,mc+32'h60000000,mc+32'h50000000,mc+32'h40000000,mc+32'h30000000,mc+32'h20000000,mc+32'h10000000,mc}),.video_data({8{vc}}),.display_data({6{dc}}),.camera_data({5{cc}}),.phy_data({2{hc}}));
 integer checks=0;
 task access(input bit wr,input [7:0] a,input [31:0] data,input bit expected_error,output reg [31:0] value);
 begin
  @(negedge p);sel=1;en=0;write=wr;addr=a;wd=data;
  @(negedge p);en=1;#1;
  while(!ready)begin @(negedge p);#1;end
  if(err!==expected_error)$fatal(1,"APB error address=%h expected=%b actual=%b",a,expected_error,err);
  value=rd;checks=checks+1;
  @(negedge p);sel=0;en=0;write=0;
 end
 endtask
 reg [31:0] result,first;
 integer i,n;
 initial begin
  #1;reset_n=0;repeat(5)@(negedge p);reset_n=1;repeat(5)@(negedge p);
  access(0,0,0,0,result);if(result!=32'h43394c34)$fatal(1,"ID");
  access(0,8'h40,0,1,result);
  access(1,4,32'hc9a70003,0,result);if(!run || !mode)$fatal(1,"Source commit");
  access(1,4,32'hc9a70001,1,result);
  access(1,8,32'h3c,0,result);repeat(12)@(negedge p);if(commands!=1 || last_gray!=8'h3c)$fatal(1,"Pattern command CDC");
  access(1,8'h10,1,0,result);
  access(1,8'h10,1,1,result);access(1,8'h14,1,1,result);
  n=0;result=0;
  while(!result[1] && n<100)begin access(0,8'h10,0,0,result);n=n+1;end
  if(!result[1])$fatal(1,"Snapshot timeout");
  access(0,8'h40,0,0,first);
  for(i=1;i<2;i=i+1)begin access(0,8'h40+4*i,0,0,result);if(result!==first+32'h10000000)$fatal(1,"Incoherent mem snapshot");end
  access(0,8'h48,0,1,result);
  repeat(100)@(negedge p);access(0,8'h40,0,0,result);if(result!==first)$fatal(1,"Snapshot changed before release");
  access(0,8'h60,0,0,first);for(i=1;i<2;i=i+1)begin access(0,8'h60+4*i,0,0,result);if(result!==first)$fatal(1,"Video snapshot");end
  access(0,8'h80,0,0,first);for(i=1;i<2;i=i+1)begin access(0,8'h80+4*i,0,0,result);if(result!==first)$fatal(1,"Display snapshot");end
  access(0,8'ha0,0,0,first);for(i=1;i<2;i=i+1)begin access(0,8'ha0+4*i,0,0,result);if(result!==first)$fatal(1,"Camera snapshot");end
  access(0,8'hc0,0,0,first);access(0,8'hc4,0,0,result);if(result!==first)$fatal(1,"PHY snapshot");
  access(1,8'h14,1,0,result);access(0,8'h40,0,1,result);
  repeat(12)@(negedge p);phy_running=0;
  access(1,8'h10,32'h301,0,result);repeat(100)@(negedge p);access(0,8'h10,0,0,result);
  if(!result[0] || result[1])$fatal(1,"Stopped source clock falsely completes");
  phy_running=1;repeat(100)@(negedge p);access(0,8'h10,0,0,result);if(!result[1])$fatal(1,"Clock recovery");
  access(0,8'h40,0,0,first);access(0,8'h44,0,0,result);
  if(first[31:28]!=6 || result[31:28]!=7 || result-first!=32'h10000000)$fatal(1,"Pair index or full 32bit data lost");
  access(0,8'hc0,0,0,result);if(result!=0)$fatal(1,"Padding of absent PHY pair");
  @(negedge p);reset_n=0;repeat(4)@(negedge p);reset_n=1;repeat(6)@(negedge p);
  access(0,4,0,0,result);if(result!=4)$fatal(1,"Reset source lock");
  access(0,8'h10,0,0,result);if(result!=0)$fatal(1,"Reset snapshot flush");
  $display("PASS c9_control checks=%0d five_native_domains frozen_bundles backpressure source_lock stopped_clock reset_flush",checks);$finish;
 end
 initial begin #100000;$fatal(1,"Timeout");end
endmodule
