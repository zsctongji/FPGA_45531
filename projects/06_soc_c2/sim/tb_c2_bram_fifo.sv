`timescale 1ns/1ps
module tb_c2_bram_fifo #(parameter S_HALF=3,D_HALF=11,ADDR_BITS=6);
localparam DEPTH=1<<ADDR_BITS;
reg rst=1,sclk=0,dclk=0,sv=0,ready=0;reg [129:0] data=0;
wire sr,valid,ref_sr,ref_valid;wire [129:0] out,ref_out;
reg [129:0] queue[0:8191],held_data;
integer sent=0,received=0,n,phase=0,stalls=0,checks=0;
reg held=0;reg [31:0] random_bits=32'h17ad2031;
always #(S_HALF) sclk=~sclk;always #(D_HALF) dclk=~dclk;
c2_bram_async_fifo #(.WIDTH(130),.ADDR_BITS(ADDR_BITS)) dut(rst,sclk,sv,sr,data,dclk,valid,ready,out);
c2_async_fifo #(.WIDTH(130),.ADDR_BITS(ADDR_BITS)) reference_fifo(rst,sclk,sv,ref_sr,data,dclk,ref_valid,ready,ref_out);
function [129:0] pattern(input integer i);
 begin pattern={2'(i%4),32'hac000000^32'(i),32'hbd000000+32'(i),32'hce000000-32'(i),32'hdf000000^32'(i)};end
endfunction
always @(posedge sclk) if(rst) begin
 if(sr!==ref_sr) $fatal(1,"FIFO capacity/ready differs from reference");
 if(sv && sr) begin queue[sent]=data;sent=sent+1;end
 if(sv && !sr) stalls=stalls+1;
end
always @(posedge dclk) if(rst) begin
 if(valid!==ref_valid || (valid && out!==ref_out)) $fatal(1,"FIFO cycle-level output differs from reference");
 if(held && (!valid || out!==held_data)) $fatal(1,"Output changed while stalled");
 held=valid&&!ready;held_data=out;
 if(valid && ready) begin
  if(received>=sent || out!==queue[received]) $fatal(1,"FIFO lost/reordered/tore data");
  received=received+1;
 end
 checks=checks+1;
end else held=0;
always @(negedge dclk) begin
 random_bits={random_bits[30:0],random_bits[31]^random_bits[21]^random_bits[1]^random_bits[0]};
 ready=phase && random_bits[0] && random_bits[2];
end
task send(input integer i);
 begin
  @(negedge sclk);sv=1;data=pattern(i);do @(posedge sclk);while(!sr);
  @(negedge sclk);sv=0;
 end
endtask
initial begin
 #1;rst=0;#29;rst=1;
 for(n=0;n<DEPTH;n=n+1)send(n);
 repeat(20) @(negedge sclk);
 if(sr || sent!=DEPTH || !valid) $fatal(1,"Not exactly DEPTH slots with stalled prefetch");
 // Reset a full FIFO and a held output, then wrap both pointers repeatedly.
 rst=0;#37;sent=0;received=0;phase=1;rst=1;
 for(n=0;n<4096;n=n+1)send(n+100);
 wait(received==4096);repeat(20) @(negedge dclk);
 if(valid || !sr || !stalls) $fatal(1,"Missing drain/full coverage");
 $display("PASS tb_c2_bram_fifo depth=%0d words=4096 checks=%0d cycle_equivalent exact_capacity pointer_wrap stable_stall common_reset synchronous_RAM",DEPTH,checks);$finish;
end
initial begin #3000000;$fatal(1,"BRAM FIFO timeout");end
endmodule
