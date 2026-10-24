`timescale 1ns/1ps
// Digital transaction model only: no DDR PHY, calibration, timing or cache.
module c2_ddr_model #(parameter WORDS=16384)(
 input wire clk,rst_n,inject_b_error,inject_r_error,
 input wire awvalid,output wire awready,input wire [31:0] awaddr,input wire [7:0] awlen,
 input wire [2:0] awsize,input wire [1:0] awburst,
 input wire wvalid,output wire wready,input wire [127:0] wdata,
 input wire [15:0] wstrb,input wire wlast,
 output reg bvalid,input wire bready,output reg [1:0] bresp,
 input wire arvalid,output wire arready,input wire [31:0] araddr,input wire [7:0] arlen,
 input wire [2:0] arsize,input wire [1:0] arburst,
 output reg rvalid,input wire rready,output reg [127:0] rdata,
 output reg rlast,output reg [1:0] rresp,
 output reg [31:0] completed_writes,completed_reads
);
 reg [127:0] memory[0:WORDS-1];
 reg [31:0] random_bits;
 reg wa,ra,b_pending,read_error;
 integer wi,ri,wn,rn,wbeat,rbeat,delay_b,delay_r,seed,i,j;
 initial begin
   seed=32'h5a7310c9;
   if($value$plusargs("SEED=%d",seed)) begin end
   for(i=0;i<WORDS;i=i+1) memory[i]=0;
 end
 assign awready=!wa && !bvalid && !b_pending && random_bits[0];
 assign wready=wa && random_bits[1];
 assign arready=!ra && !rvalid && random_bits[2];
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin
     random_bits<=seed;wa<=0;ra<=0;b_pending<=0;bvalid<=0;bresp<=0;
     rvalid<=0;rdata<=0;rlast<=0;rresp<=0;wi<=0;ri<=0;wn<=0;rn<=0;
     wbeat<=0;rbeat<=0;delay_b<=0;delay_r<=0;read_error<=0;
     completed_writes<=0;completed_reads<=0;
   end else begin
     random_bits<={random_bits[30:0],random_bits[31]^random_bits[21]^random_bits[1]^random_bits[0]};
     if(awvalid && awready) begin
       if(awsize!=4 || awburst!=1 || awaddr[3:0]!=0 ||
          (awaddr[11:0]+(awlen+1)*16)>4096 || awaddr/16+awlen>=WORDS)
           $fatal(1,"Invalid write transaction to DDR model");
       wa<=1;wi<=awaddr/16;wn<=awlen;wbeat<=0;
       bresp<=inject_b_error?2:0;
     end
     if(wvalid && wready) begin
       if(wlast!=(wbeat==wn)) $fatal(1,"Write beat length mismatch");
       for(j=0;j<16;j=j+1) if(wstrb[j]) memory[wi][j*8+:8]<=wdata[j*8+:8];
       wi<=wi+1;wbeat<=wbeat+1;
       if(wlast) begin wa<=0;b_pending<=1;delay_b<=3+random_bits[5:3];end
     end
     if(b_pending) begin
       if(delay_b==0) begin bvalid<=1;b_pending<=0;end else delay_b<=delay_b-1;
     end
     if(bvalid && bready) begin bvalid<=0;completed_writes<=completed_writes+1;end
     if(arvalid && arready) begin
       if(arsize!=4 || arburst!=1 || araddr[3:0]!=0 ||
          (araddr[11:0]+(arlen+1)*16)>4096 || araddr/16+arlen>=WORDS)
           $fatal(1,"Invalid read transaction to DDR model");
       ra<=1;ri<=araddr/16;rn<=arlen;rbeat<=0;delay_r<=2;
       read_error<=inject_r_error;
     end
     if(ra && !rvalid) begin
       if(delay_r!=0) delay_r<=delay_r-1;
       else begin rvalid<=1;rdata<=memory[ri];rlast<=(rbeat==rn);rresp<=read_error?2:0;end
     end
     if(rvalid && rready) begin
       rvalid<=0;
       if(rlast) begin ra<=0;completed_reads<=completed_reads+1;end
       else begin ri<=ri+1;rbeat<=rbeat+1;delay_r<=random_bits[4:3];end
     end
   end
 end
endmodule

