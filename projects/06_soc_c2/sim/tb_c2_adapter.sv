`timescale 1ns/1ps
module tb_c2_adapter;
localparam N=1;
reg clk=0,rst_n=0,inject_b_error=0,inject_r_error=0;
always #5 clk=~clk;
reg [0:0] s_awvalid=0;
wire [0:0] s_awready;
reg [31:0] s_awaddr=0;
reg [7:0] s_awlen=0;
reg [0:0] s_wvalid=0;
wire [0:0] s_wready;
reg [127:0] s_wdata=0;
reg [15:0] s_wstrb=0;
reg [0:0] s_wlast=0;
wire [0:0] s_bvalid;
reg [0:0] s_bready=0;
wire [1:0] s_bresp;
reg [0:0] s_arvalid=0;
wire [0:0] s_arready;
reg [31:0] s_araddr=0;
reg [7:0] s_arlen=0;
wire [0:0] s_rvalid;
reg [0:0] s_rready=0;
wire [127:0] s_rdata;
wire [0:0] s_rlast;
wire [1:0] s_rresp;
reg [7:0] s_awid=0,s_arid=0;wire [7:0] s_bid,s_rid;
reg [2:0] s_awsize=4,s_arsize=4;reg [1:0] s_awburst=1,s_arburst=1;reg s_awlock=0,s_arlock=0,enable=1;
wire rejected,protocol_error,fabric_error;
wire [0:0] q_awvalid;
wire [0:0] q_awready;
wire [31:0] q_awaddr;
wire [7:0] q_awlen;
wire [0:0] q_wvalid;
wire [0:0] q_wready;
wire [127:0] q_wdata;
wire [15:0] q_wstrb;
wire [0:0] q_wlast;
wire [0:0] q_bvalid;
wire [0:0] q_bready;
wire [1:0] q_bresp;
wire [0:0] q_arvalid;
wire [0:0] q_arready;
wire [31:0] q_araddr;
wire [7:0] q_arlen;
wire [0:0] q_rvalid;
wire [0:0] q_rready;
wire [127:0] q_rdata;
wire [0:0] q_rlast;
wire [1:0] q_rresp;
wire [31:0] completed_writes,completed_reads;
c2_axi_to_vendor #(.ALLOW_NARROW(1),.SOURCE_BASE(32'h1000),.TARGET_BASE(32'h10000),.WINDOW_BYTES(32'h10000)) adapter(.clk(clk),.rst_n(rst_n),.enable(enable),
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
.s_awid(s_awid),
.s_arid(s_arid),
.s_bid(s_bid),
.s_rid(s_rid),
.s_awsize(s_awsize),
.s_arsize(s_arsize),
.s_awburst(s_awburst),
.s_arburst(s_arburst),
.s_awlock(s_awlock),
.s_arlock(s_arlock),
.m_awvalid(q_awvalid),
.m_awready(q_awready),
.m_awaddr(q_awaddr),
.m_awlen(q_awlen),
.m_wvalid(q_wvalid),
.m_wready(q_wready),
.m_wdata(q_wdata),
.m_wstrb(q_wstrb),
.m_wlast(q_wlast),
.m_bvalid(q_bvalid),
.m_bready(q_bready),
.m_bresp(q_bresp),
.m_arvalid(q_arvalid),
.m_arready(q_arready),
.m_araddr(q_araddr),
.m_arlen(q_arlen),
.m_rvalid(q_rvalid),
.m_rready(q_rready),
.m_rdata(q_rdata),
.m_rlast(q_rlast),
.m_rresp(q_rresp),
.rejected(rejected),.protocol_error(protocol_error));
c2_bus_fixture #(.N(N)) fixture(.clk(clk),.rst_n(rst_n),.inject_b_error(inject_b_error),.inject_r_error(inject_r_error),
.s_awvalid(q_awvalid),
.s_awready(q_awready),
.s_awaddr(q_awaddr),
.s_awlen(q_awlen),
.s_wvalid(q_wvalid),
.s_wready(q_wready),
.s_wdata(q_wdata),
.s_wstrb(q_wstrb),
.s_wlast(q_wlast),
.s_bvalid(q_bvalid),
.s_bready(q_bready),
.s_bresp(q_bresp),
.s_arvalid(q_arvalid),
.s_arready(q_arready),
.s_araddr(q_araddr),
.s_arlen(q_arlen),
.s_rvalid(q_rvalid),
.s_rready(q_rready),
.s_rdata(q_rdata),
.s_rlast(q_rlast),
.s_rresp(q_rresp),
.protocol_error(fabric_error),.completed_writes(completed_writes),.completed_reads(completed_reads));
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

always @(posedge clk) if(rst_n) begin
 if(s_bvalid && s_bid!==s_awid) $fatal(1,"Write ID lost");
 if(s_rvalid && s_rid!==s_arid) $fatal(1,"Read ID lost");
end
task rejected_read(input [31:0] addr,input integer count);
 integer b;begin
 @(negedge clk);s_arvalid=1;s_araddr=addr;s_arlen=count-1;
 do @(posedge clk);while(!s_arready);
 @(negedge clk);s_arvalid=0;s_rready=1;
 for(b=0;b<count;b=b+1) begin
   do @(posedge clk);while(!s_rvalid);
   if(s_rresp!=3 || s_rdata!=0 || s_rlast!=(b==count-1)) $fatal(1,"Malformed DECERR read");
   @(negedge clk);
 end
 s_rready=0;
 end
endtask
integer id,before_w,before_r;reg [127:0] expected;
initial begin
 #23;rst_n=1;
 for(id=0;id<256;id=id+1) begin
   s_awid=id;s_arid=255-id;
   write_burst(0,32'h1000+id*16,1,id,0);
   read_burst(0,32'h1000+id*16,1,id,0);
 end
 write_burst(0,32'h5000,128,555,0);read_burst(0,32'h5000,128,555,0);
 write_burst(0,32'h6000,256,556,0);read_burst(0,32'h6000,256,556,0);
 // A CPU 32-bit store at lane 1 must preserve the other 12 bytes.
 @(negedge clk);s_awsize=2;s_awaddr=32'ha004;s_awlen=0;s_awvalid=1;
 do @(posedge clk);while(!s_awready);
 @(negedge clk);s_awvalid=0;s_wdata=128'h11223344_55667788_aabbccdd_eeff0011;s_wstrb=16'h00f0;s_wlast=1;s_wvalid=1;
 do @(posedge clk);while(!s_wready);
 @(negedge clk);s_wvalid=0;s_bready=1;
 do @(posedge clk);while(!s_bvalid);
 if(s_bresp!=0) $fatal(1,"Narrow store rejected");
 @(negedge clk);s_bready=0;s_awsize=4;
 expected=128'h00000000_00000000_aabbccdd_00000000;
 if(fixture.memory_model.memory[32'h19000/16]!==expected) $fatal(1,"Narrow store lane/relocation corruption");
 @(negedge clk);s_arsize=2;s_araddr=32'ha004;s_arlen=0;s_arvalid=1;
 do @(posedge clk);while(!s_arready);
 @(negedge clk);s_arvalid=0;
 repeat(8) @(negedge clk);
 if(!s_rvalid || s_rdata!==expected || s_rresp!=0) $fatal(1,"Narrow read result/stall wrong");
 s_rready=1;@(negedge clk);s_rready=0;s_arsize=4;
 if(protocol_error || fabric_error || rejected) $fatal(1,"Legal traffic flagged");
 before_w=completed_writes;before_r=completed_reads;
 write_burst(0,32'h0,2,777,3);rejected_read(32'h0,2);
 write_burst(0,32'h1ff0,2,778,3);rejected_read(32'h1ff0,2);
 s_awsize=2;s_arsize=2;
 write_burst(0,32'h3000,2,779,3);rejected_read(32'h3000,2);
 s_awsize=4;s_arsize=4;s_awlock=1;s_arlock=1;
 write_burst(0,32'h3000,1,780,3);rejected_read(32'h3000,1);
 s_awlock=0;s_arlock=0;enable=0;
 write_burst(0,32'h3000,1,781,3);rejected_read(32'h3000,1);
 if(completed_writes!=before_w || completed_reads!=before_r || !rejected)
   $fatal(1,"Rejected request escaped to DDR");
 enable=1;
 inject_b_error=1;write_burst(0,32'hb000,4,900,2);inject_b_error=0;
 inject_r_error=1;read_burst(0,32'hb000,4,900,2);inject_r_error=0;
 $display("PASS tb_c2_adapter ids=256 full128 burst128 burst256 narrow32 byte_lanes relocation DECERR no_invalid_DDR error_routing");
 $finish;
end
initial begin #10000000;$fatal(1,"Adapter timeout");end
endmodule

