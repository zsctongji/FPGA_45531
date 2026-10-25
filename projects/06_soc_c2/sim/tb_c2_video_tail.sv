`timescale 1ns/1ps
// Six words/frame: explicitly exercise the <16-beat final write/read burst.
module tb_c2_video_tail;
reg clk=0,dclk=0,rst_n=1;
always #5 clk=~clk;always #7 dclk=~dclk;
reg iv=0,scan=0;wire ir,sr,ov;reg orr=0;reg [129:0] idata=0;wire [129:0] odata;
wire awvalid,awready,wvalid,wready,wlast,bvalid,bready,arvalid,arready,rvalid,rready,rlast;
wire [31:0] awaddr,araddr;wire [7:0] awlen,arlen;wire [127:0] wdata,rdata;
wire [15:0] wstrb;wire [1:0] bresp,rresp;
wire [31:0] published,dropped,write_errors,read_errors,repeated;
integer aws=0,bs=0,ars=0,words=0,n,k;
reg [31:0] random_bits=32'h296a718c;
function [127:0] pattern(input integer word_index);
 integer b;begin for(b=0;b<16;b=b+1) pattern[b*8+:8]=8'(word_index*19+b);end
endfunction
c2_video_framebuffer #(.WIDTH(32),.HEIGHT(3)) dut(
.arst_n(rst_n),.clk(clk),.display_clk(dclk),.enable(1'b1),
.in_valid(iv),.in_ready(ir),.in_data(idata),.scan_valid(scan),.scan_ready(sr),
.out_valid(ov),.out_ready(orr),.out_data(odata),
.awvalid(awvalid),.awready(awready),.awaddr(awaddr),.awlen(awlen),
.wvalid(wvalid),.wready(wready),.wdata(wdata),.wstrb(wstrb),.wlast(wlast),
.bvalid(bvalid),.bready(bready),.bresp(bresp),
.arvalid(arvalid),.arready(arready),.araddr(araddr),.arlen(arlen),
.rvalid(rvalid),.rready(rready),.rdata(rdata),.rlast(rlast),.rresp(rresp),
.published(published),.dropped(dropped),.write_errors(write_errors),.read_errors(read_errors),
.repeated(repeated),.empty_scans(),.max_aw_wait(),.max_ar_wait(),.bank_states());
c2_ddr_model #(.WORDS(1024)) mem(
.clk(clk),.rst_n(rst_n),.inject_b_error(1'b0),.inject_r_error(1'b0),
.awvalid(awvalid),.awready(awready),.awaddr(awaddr),.awlen(awlen),.awsize(3'd4),.awburst(2'b01),
.wvalid(wvalid),.wready(wready),.wdata(wdata),.wstrb(wstrb),.wlast(wlast),
.bvalid(bvalid),.bready(bready),.bresp(bresp),
.arvalid(arvalid),.arready(arready),.araddr(araddr),.arlen(arlen),.arsize(3'd4),.arburst(2'b01),
.rvalid(rvalid),.rready(rready),.rdata(rdata),.rlast(rlast),.rresp(rresp),
.completed_writes(),.completed_reads());
always @(posedge clk) if(rst_n) begin
 if(awvalid && awready) begin aws=aws+1;if(awlen!=5 || awaddr!=0) $fatal(1,"Short AW length/address");end
 if(bvalid && bready) bs=bs+1;
 if(arvalid && arready) begin ars=ars+1;if(arlen!=5 || araddr!=0) $fatal(1,"Short AR length/address");end
 if(published && bs!=1) $fatal(1,"Tail published without its BRESP");
end
task token(input [129:0] value);
 begin
  @(negedge clk);iv=1;idata=value;
  do @(posedge clk);while(!ir);
  @(negedge clk);iv=0;
 end
endtask
task read_scan;
 reg header,ended;integer count;
 begin
  @(negedge dclk);scan=1;do @(posedge dclk);while(!sr);
  @(negedge dclk);scan=0;header=0;ended=0;count=0;
  while(!ended) begin
   random_bits={random_bits[30:0],random_bits[31]^random_bits[21]^random_bits[1]^random_bits[0]};
   orr=random_bits[0];@(posedge dclk);
   if(ov && orr) begin
    case(odata[129:128])
     1:begin
      if(header || odata[64]!=1 || odata[63:32]!=123 || odata[31:0]!=42) $fatal(1,"Tail scan metadata");
      header=1;
     end
     0:begin
      if(!header || count>=6 || odata[127:0]!==pattern(count)) $fatal(1,"Tail data/stall corruption");
      count=count+1;words=words+1;
     end
     2:begin if(count!=6 || odata[0]) $fatal(1,"Tail END");ended=1;end
     default:$fatal(1,"Unexpected tail ABORT");
    endcase
   end
   @(negedge dclk);
  end
  orr=0;wait(dut.rs==0);repeat(5) @(negedge dclk);
 end
endtask
initial begin
 #1;rst_n=0;#53;rst_n=1;repeat(8) @(negedge clk);
 token({2'd1,64'b0,32'd123,32'd42});
 for(n=0;n<6;n=n+1) token({2'd0,pattern(n)});
 if(published || awvalid || aws) $fatal(1,"Short burst emitted before source END");
 token({2'd2,96'b0,32'd42});wait(published==1);
 for(k=0;k<6;k=k+1) if(mem.memory[k]!==pattern(k)) $fatal(1,"Tail DDR bytes");
 read_scan();read_scan();
 if(aws!=1 || ars!=2 || words!=12 || repeated!=1 || dropped || write_errors || read_errors) $fatal(1,"Tail coverage");
 $display("PASS tb_c2_video_tail words=6 AWLEN=5 ARLEN=5 writes=1 scans=2 checked_bytes=192 final_B_fence display_backpressure repeat");
 $finish;
end
initial begin #1000000;$fatal(1,"Tail timeout");end
endmodule
