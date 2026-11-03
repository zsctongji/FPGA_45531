`timescale 1ns/1ps
// Exact DEPTH-entry asynchronous FIFO with a synchronous, reset-free RAM read.
// rbin advances on CONSUMPTION, not prefetch, so the output register does not
// increase capacity or release a stalled RAM slot to the writer prematurely.
// Common reset cancels all ownership; RAM bytes themselves are not reset.
// CDC synchronizers/Gray buses still require physical constraints/signoff.
module c2_bram_async_fifo #(parameter WIDTH=130,parameter ADDR_BITS=6)(
 input wire arst_n,s_clk,input wire s_valid,output wire s_ready,input wire [WIDTH-1:0] s_data,
 input wire d_clk,output wire d_valid,input wire d_ready,output wire [WIDTH-1:0] d_data
);
 reg [WIDTH-1:0] memory[0:(1<<ADDR_BITS)-1];
 reg [WIDTH-1:0] ram_data;
 reg [ADDR_BITS:0] wbin,wgray,rbin,rgray;
 (* async_reg="true" *) reg [ADDR_BITS:0] rgray1,rgray2,wgray1,wgray2;
 reg full,output_valid;
 reg [1:0] sr,dr;
 wire pop=d_valid && d_ready;
 wire [ADDR_BITS:0] wn=wbin+(s_valid && s_ready),rn=rbin+pop;
 wire [ADDR_BITS:0] wg=(wn>>1)^wn,rg=(rn>>1)^rn;
 wire have_next=rg!=wgray2;
 wire load=dr[1] && (!output_valid || pop) && have_next;
 assign s_ready=sr[1] && !full;
 assign d_valid=dr[1] && output_valid;
 assign d_data=ram_data;
 initial if(ADDR_BITS<2) $error("ADDR_BITS must be >=2");
 // Keep both RAM processes free of reset so Efinity can infer block RAM.
 always @(posedge s_clk) if(s_valid && s_ready) memory[wbin[ADDR_BITS-1:0]]<=s_data;
 always @(posedge d_clk) if(load) ram_data<=memory[rn[ADDR_BITS-1:0]];
 always @(posedge s_clk or negedge arst_n)
  if(!arst_n) sr<=0;else sr<={sr[0],1'b1};
 always @(posedge d_clk or negedge arst_n)
  if(!arst_n) dr<=0;else dr<={dr[0],1'b1};
 always @(posedge s_clk or negedge arst_n) begin
  if(!arst_n) begin wbin<=0;wgray<=0;rgray1<=0;rgray2<=0;full<=0;end
  else begin
   rgray1<=rgray;rgray2<=rgray1;wbin<=wn;wgray<=wg;
   full<=(wg=={~rgray2[ADDR_BITS:ADDR_BITS-1],rgray2[ADDR_BITS-2:0]});
  end
 end
 always @(posedge d_clk or negedge arst_n) begin
  if(!arst_n) begin rbin<=0;rgray<=0;wgray1<=0;wgray2<=0;output_valid<=0;end
  else begin
   wgray1<=wgray;wgray2<=wgray1;rbin<=rn;rgray<=rg;
   if(!dr[1]) output_valid<=0;
   else if(!output_valid || pop) output_valid<=have_next;
  end
 end
endmodule
