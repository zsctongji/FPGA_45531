`timescale 1ns/1ps
module tb_c2_fifo;
 reg arst_n=0,sclk=0,dclk=0,sv=0,dr=0;
 reg [127:0] sd=0;wire sr,dv;wire [127:0] dd;
 reg [127:0] queue[0:4095],held_data;
 integer sent=0,received=0,i,phase=0,full_stalls=0;
 reg held=0;reg [31:0] random_bits=32'h17ad2031;
 always #3 sclk=~sclk;always #11 dclk=~dclk;
 c2_async_fifo #(.WIDTH(128),.ADDR_BITS(2)) dut(arst_n,sclk,sv,sr,sd,dclk,dv,dr,dd);
 function [127:0] pattern(input integer n);
   begin pattern={32'hac000000^n,32'hbd000000+n,32'hce000000-n,32'hdf000000^n};end
 endfunction
 always @(posedge sclk) if(arst_n) begin
   if(sv && sr) begin queue[sent]=sd;sent=sent+1;end
   if(sv && !sr) full_stalls=full_stalls+1;
 end
 always @(posedge dclk) if(arst_n) begin
   if(held && (!dv || dd!==held_data)) $fatal(1,"FIFO output changed under stall");
   held=dv && !dr;held_data=dd;
   if(dv && dr) begin
     if(received>=sent || dd!==queue[received]) $fatal(1,"FIFO loss/reorder/torn word");
     received=received+1;
   end
 end else held=0;
 always @(negedge dclk) begin
   random_bits={random_bits[30:0],random_bits[31]^random_bits[21]^random_bits[1]^random_bits[0]};
   dr=phase && random_bits[0] && random_bits[2];
 end
 task send(input integer n);
   begin
     @(negedge sclk);sv=1;sd=pattern(n);
     do @(posedge sclk);while(!sr);
     @(negedge sclk);sv=0;
   end
 endtask
 initial begin
   #19;arst_n=1;
   for(i=0;i<4;i=i+1) send(i);
   repeat(10) @(negedge sclk);
   if(sr || sent!=4 || !dv) $fatal(1,"FIFO depth/full boundary wrong");
   // Shared reset cancels a full queue, followed by many pointer wraps.
   arst_n=0;#29;sent=0;received=0;phase=1;arst_n=1;
   for(i=0;i<2048;i=i+1) send(i+100);
   wait(received==2048);
   repeat(12) @(negedge dclk);
   if(dv || !sr || full_stalls==0) $fatal(1,"FIFO did not fully drain/exercise full stalls");
   $display("PASS tb_c2_fifo words=2048 depth=4 pointer_wrap full empty async_clocks stable_stall common_reset");
   $finish;
 end
 initial begin #2000000;$fatal(1,"FIFO timeout");end
endmodule
