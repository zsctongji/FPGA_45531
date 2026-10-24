`timescale 1ns/1ps
module tb_c2_cdc;
 reg reset_n=0,s_clk=0,d_clk=0,s_valid=0,d_ready=0;
 reg [511:0] s_data=0;
 wire s_ready,d_valid;wire [511:0] d_data;
 integer sent=0,received=0,phase=0,i;
 reg [511:0] queue[0:511],previous;
 reg held=0;
 reg [31:0] random_bits=32'h71cc4101;
 c2_cdc_mailbox dut(reset_n,s_clk,s_valid,s_ready,s_data,d_clk,d_valid,d_ready,d_data);
 always #5 s_clk=~s_clk;
 always #7 d_clk=~d_clk;
 function [511:0] payload(input integer n);
   integer k;begin for(k=0;k<16;k=k+1) payload[k*32+:32]=n^(32'h5a000000+k*37);end
 endfunction
 always @(posedge s_clk) if(reset_n && s_valid && s_ready) begin queue[sent]=s_data;sent=sent+1;end
 always @(posedge d_clk) begin
   if(reset_n) begin
     if(held && (!d_valid || d_data!==previous)) $fatal(1,"CDC payload changed under backpressure");
     held=d_valid && !d_ready;previous=d_data;
     if(d_valid && d_ready) begin
       if(received>=sent || d_data!==queue[received]) $fatal(1,"Torn/stale CDC message");
       received=received+1;
     end
   end else held=0;
 end
 always @(negedge d_clk) begin
   random_bits={random_bits[30:0],random_bits[31]^random_bits[21]^random_bits[1]^random_bits[0]};
   if(phase==1) d_ready=random_bits[0] && random_bits[2];else d_ready=0;
 end
 task send(input integer n);
   begin
     @(negedge s_clk);s_valid=1;s_data=payload(n);
     do @(posedge s_clk);while(!s_ready);
     @(negedge s_clk);s_valid=0;
   end
 endtask
 initial begin
   #23;reset_n=1;
   send(999);
   repeat(15) @(posedge d_clk);
   if(!d_valid || s_ready) $fatal(1,"Mailbox didn't hold pending message");
   // Reset cancels one pending transfer in BOTH domains, not only the receiver.
   @(negedge s_clk);reset_n=0;
   #19;sent=0;received=0;phase=1;reset_n=1;
   for(i=0;i<200;i=i+1) send(i);
   wait(received==200);
   repeat(10) @(posedge d_clk);
   if(d_valid) $fatal(1,"Ghost message after drain");
   $display("PASS tb_c2_cdc messages=200 width=512 asynchronous_clocks backpressure common_reset_cancel");$finish;
 end
 initial begin #200000; $fatal(1,"CDC timeout");end
endmodule

