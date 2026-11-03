`timescale 1ns/1ps
module tb_c2_axi;
localparam N=4;
reg clk=0,rst_n=0,inject_b_error=0,inject_r_error=0;
always #5 clk=~clk;
reg [N*1-1:0] s_awvalid=0;
wire [N*1-1:0] s_awready;
reg [N*32-1:0] s_awaddr=0;
reg [N*8-1:0] s_awlen=0;
reg [N*1-1:0] s_wvalid=0;
wire [N*1-1:0] s_wready;
reg [N*128-1:0] s_wdata=0;
reg [N*16-1:0] s_wstrb=0;
reg [N*1-1:0] s_wlast=0;
wire [N*1-1:0] s_bvalid;
reg [N*1-1:0] s_bready=0;
wire [N*2-1:0] s_bresp;
reg [N*1-1:0] s_arvalid=0;
wire [N*1-1:0] s_arready;
reg [N*32-1:0] s_araddr=0;
reg [N*8-1:0] s_arlen=0;
wire [N*1-1:0] s_rvalid;
reg [N*1-1:0] s_rready=0;
wire [N*128-1:0] s_rdata;
wire [N*1-1:0] s_rlast;
wire [N*2-1:0] s_rresp;
wire protocol_error;wire [31:0] completed_writes,completed_reads;
c2_bus_fixture #(.N(N)) dut(.clk(clk),.rst_n(rst_n),.inject_b_error(inject_b_error),.inject_r_error(inject_r_error),
.s_awvalid(s_awvalid),
.s_awready(s_awready),
.s_awaddr(s_awaddr),
.s_awlen(s_awlen),
.s_wvalid(s_wvalid),
.s_wready(s_wready),
.s_wdata(s_wdata),
.s_wstrb(s_wstrb),
.s_wlast(s_wlast),
.s_bvalid(s_bvalid),
.s_bready(s_bready),
.s_bresp(s_bresp),
.s_arvalid(s_arvalid),
.s_arready(s_arready),
.s_araddr(s_araddr),
.s_arlen(s_arlen),
.s_rvalid(s_rvalid),
.s_rready(s_rready),
.s_rdata(s_rdata),
.s_rlast(s_rlast),
.s_rresp(s_rresp),
.protocol_error(protocol_error),
.completed_writes(completed_writes),
.completed_reads(completed_reads));
integer checks=0,write_transactions=0,read_transactions=0;
function [127:0] pattern(input integer tag,input integer beat);
 integer lane;begin for(lane=0;lane<4;lane=lane+1) pattern[lane*32+:32]=tag*65536+beat*4+lane;end
endfunction
function [127:0] masked_pattern(input integer tag,input integer beat);
 reg [127:0] p;reg [15:0] mask;integer b;
 begin
   p=pattern(tag,beat);mask=16'hffff<<(beat%4);
   for(b=0;b<16;b=b+1) if(!mask[b]) p[b*8+:8]=0;
   masked_pattern=p;
 end
endfunction
task automatic write_burst(input integer p,input integer addr,input integer count,
                           input integer tag,input [1:0] response);
 integer b;
 begin
   @(negedge clk);s_awvalid[p]=1;s_awaddr[p*32+:32]=addr;s_awlen[p*8+:8]=count-1;
   do @(posedge clk);while(!s_awready[p]);
   @(negedge clk);s_awvalid[p]=0;
   for(b=0;b<count;b=b+1) begin
     repeat((b+p)%3) @(negedge clk);
     s_wvalid[p]=1;s_wdata[p*128+:128]=pattern(tag,b);
     s_wstrb[p*16+:16]=16'hffff<<(b%4);s_wlast[p]=(b==count-1);
     do @(posedge clk);while(!s_wready[p]);
     @(negedge clk);s_wvalid[p]=0;s_wlast[p]=0;
   end
   repeat(p+2) @(negedge clk);
   s_bready[p]=1;
   do @(posedge clk);while(!s_bvalid[p]);
   if(s_bresp[p*2+:2]!==response) $fatal(1,"B response misrouted p=%d",p);
   checks=checks+1;write_transactions=write_transactions+1;
   @(negedge clk);s_bready[p]=0;
 end
endtask
task automatic read_burst(input integer p,input integer addr,input integer count,
                          input integer tag,input [1:0] response);
 integer b;
 begin
   @(negedge clk);s_arvalid[p]=1;s_araddr[p*32+:32]=addr;s_arlen[p*8+:8]=count-1;
   do @(posedge clk);while(!s_arready[p]);
   @(negedge clk);s_arvalid[p]=0;
   for(b=0;b<count;b=b+1) begin
     repeat((b+2*p)%4) @(negedge clk);
     s_rready[p]=1;
     do @(posedge clk);while(!s_rvalid[p]);
     if(s_rresp[p*2+:2]!==response || s_rlast[p]!=(b==count-1) ||
        s_rdata[p*128+:128]!==masked_pattern(tag,b))
        $fatal(1,"Read mismatch p=%d beat=%d got=%h expected=%h",p,b,s_rdata[p*128+:128],masked_pattern(tag,b));
     checks=checks+1;
     @(negedge clk);s_rready[p]=0;
   end
   read_transactions=read_transactions+1;
 end
endtask
integer t0,t1,t2,t3,j,max_wait=0;
integer waits[0:N-1];
initial for(j=0;j<N;j=j+1) waits[j]=0;
always @(posedge clk) if(rst_n) begin
 for(j=0;j<N;j=j+1) begin
   if((s_awvalid[j]&&!s_awready[j])||(s_arvalid[j]&&!s_arready[j])) begin
     waits[j]=waits[j]+1;
     if(waits[j]>max_wait) max_wait=waits[j];
     if(waits[j]>2000) $fatal(1,"Request starvation p=%d",j);
   end else waits[j]=0;
 end
end
initial begin
 #23;rst_n=1;
 fork
  begin for(t0=0;t0<20;t0=t0+1) begin write_burst(0,t0*256,1+t0%8,t0,0);read_burst(0,t0*256,1+t0%8,t0,0);end end
  begin for(t1=0;t1<20;t1=t1+1) begin write_burst(1,32'h8000+t1*256,1+(t1+1)%8,100+t1,0);read_burst(1,32'h8000+t1*256,1+(t1+1)%8,100+t1,0);end end
  begin for(t2=0;t2<20;t2=t2+1) begin write_burst(2,32'h10000+t2*256,1+(t2+2)%8,200+t2,0);read_burst(2,32'h10000+t2*256,1+(t2+2)%8,200+t2,0);end end
  begin for(t3=0;t3<20;t3=t3+1) begin write_burst(3,32'h18000+t3*256,1+(t3+3)%8,300+t3,0);read_burst(3,32'h18000+t3*256,1+(t3+3)%8,300+t3,0);end end
 join
 // Match the vendor video's 128-beat configuration and the AXI maximum
 // 256-beat aligned full-page burst, including every byte-enable pattern.
 write_burst(2,32'h28000,128,555,0);read_burst(2,32'h28000,128,555,0);
 write_burst(3,32'h29000,256,556,0);read_burst(3,32'h29000,256,556,0);
 if(protocol_error) $fatal(1,"Unexpected AXI protocol error");
 inject_b_error=1;write_burst(2,32'h24000,4,999,2);inject_b_error=0;
 inject_r_error=1;read_burst(2,32'h24000,4,999,2);inject_r_error=0;
 // Abort an in-progress write using the shared fabric+memory reset.
 @(negedge clk);s_awvalid[0]=1;s_awaddr[31:0]=32'h30000;s_awlen[7:0]=3;
 do @(posedge clk);while(!s_awready[0]);
 @(negedge clk);s_awvalid[0]=0;s_wvalid[0]=1;s_wdata[127:0]=128'hf00d;s_wstrb[15:0]=16'hffff;
 do @(posedge clk);while(!s_wready[0]);
 @(negedge clk);s_wvalid=0;rst_n=0;
 repeat(4) @(negedge clk);rst_n=1;
 write_burst(0,32'h31000,3,1234,0);read_burst(0,32'h31000,3,1234,0);
 if(protocol_error) $fatal(1,"Reset recovery error");
 $display("PASS tb_c2_axi masters=4 writes=%0d reads=%0d checks=%0d max_request_wait=%0d full128_INCR strobes stalls error_routing reset",write_transactions,read_transactions,checks,max_wait);
 $finish;
end
initial begin #10000000;$fatal(1,"AXI test timeout");end
endmodule

