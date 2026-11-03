`timescale 1ns/1ps
// Dual-clock Gray-pointer FIFO. Common reset flushes both domains.
// Logical simulation is not metastability/physical CDC signoff.
module c2_async_fifo #(parameter WIDTH=128,parameter ADDR_BITS=4)(
 input wire arst_n,s_clk,input wire s_valid,output wire s_ready,input wire [WIDTH-1:0] s_data,
 input wire d_clk,output wire d_valid,input wire d_ready,output wire [WIDTH-1:0] d_data
);
 reg [WIDTH-1:0] memory[0:(1<<ADDR_BITS)-1];
 reg [ADDR_BITS:0] wbin,wgray,rbin,rgray;
 (* async_reg="true" *) reg [ADDR_BITS:0] rgray1,rgray2,wgray1,wgray2;
 reg full,empty;
 reg [1:0] sr,dr;
 wire [ADDR_BITS:0] wn=wbin+(s_valid && s_ready);
 wire [ADDR_BITS:0] rn=rbin+(d_valid && d_ready);
 wire [ADDR_BITS:0] wg=(wn>>1)^wn;
 wire [ADDR_BITS:0] rg=(rn>>1)^rn;
 assign s_ready=sr[1] && !full;
 assign d_valid=dr[1] && !empty;
 assign d_data=memory[rbin[ADDR_BITS-1:0]];
 initial if(ADDR_BITS<2) $error("ADDR_BITS must be >=2");
 always @(posedge s_clk or negedge arst_n)
   if(!arst_n) sr<=0;else sr<={sr[0],1'b1};
 always @(posedge d_clk or negedge arst_n)
   if(!arst_n) dr<=0;else dr<={dr[0],1'b1};
 always @(posedge s_clk or negedge arst_n) begin
   if(!arst_n) begin wbin<=0;wgray<=0;rgray1<=0;rgray2<=0;full<=0;end
   else begin
     rgray1<=rgray;rgray2<=rgray1;
     wbin<=wn;wgray<=wg;
     full<=(wg=={~rgray2[ADDR_BITS:ADDR_BITS-1],rgray2[ADDR_BITS-2:0]});
     if(s_valid && s_ready) memory[wbin[ADDR_BITS-1:0]]<=s_data;
   end
 end
 always @(posedge d_clk or negedge arst_n) begin
   if(!arst_n) begin rbin<=0;rgray<=0;wgray1<=0;wgray2<=0;empty<=1;end
   else begin
     wgray1<=wgray;wgray2<=wgray1;
     rbin<=rn;rgray<=rg;empty<=(rg==wgray2);
   end
 end
endmodule

