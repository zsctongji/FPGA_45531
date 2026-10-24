`timescale 1ns/1ps
// Portable functional candidate: aligned 128-bit, INCR, 1 global outstanding
// burst, no source AXI IDs/reordering/exclusives/narrow transfers.
// Conservative transaction-level round-robin across all master/read-write pairs.
// This is not the encrypted vendor interconnect and is not a throughput signoff.
module c2_axi_arbiter #(parameter N=4)(
 input wire clk,rst_n,
 input wire [N-1:0] s_awvalid, output reg [N-1:0] s_awready,
 input wire [N*32-1:0] s_awaddr, input wire [N*8-1:0] s_awlen,
 input wire [N-1:0] s_wvalid, output reg [N-1:0] s_wready,
 input wire [N*128-1:0] s_wdata, input wire [N*16-1:0] s_wstrb,
 input wire [N-1:0] s_wlast,
 output reg [N-1:0] s_bvalid, input wire [N-1:0] s_bready,
 output reg [N*2-1:0] s_bresp,
 input wire [N-1:0] s_arvalid, output reg [N-1:0] s_arready,
 input wire [N*32-1:0] s_araddr, input wire [N*8-1:0] s_arlen,
 output reg [N-1:0] s_rvalid, input wire [N-1:0] s_rready,
 output reg [N*128-1:0] s_rdata, output reg [N-1:0] s_rlast,
 output reg [N*2-1:0] s_rresp,
 output wire m_awvalid,input wire m_awready,output wire [31:0] m_awaddr,
 output wire [7:0] m_awlen,output wire [2:0] m_awsize,output wire [1:0] m_awburst,
 output wire m_wvalid,input wire m_wready,output wire [127:0] m_wdata,
 output wire [15:0] m_wstrb,output wire m_wlast,
 input wire m_bvalid,output wire m_bready,input wire [1:0] m_bresp,
 output wire m_arvalid,input wire m_arready,output wire [31:0] m_araddr,
 output wire [7:0] m_arlen,output wire [2:0] m_arsize,output wire [1:0] m_arburst,
 input wire m_rvalid,output wire m_rready,input wire [127:0] m_rdata,
 input wire m_rlast,input wire [1:0] m_rresp,
 output reg protocol_error
);
 localparam IDLE=0,AW=1,W=2,B=3,AR=4,R=5;
 reg [2:0] state;
 integer owner,round_robin,k,choice,index;
 reg [31:0] address;
 reg [7:0] length;
 reg [8:0] beats;
 wire expected_last=(beats=={1'b0,length});
 assign m_awvalid=(state==AW);
 assign m_awaddr=address;assign m_awlen=length;assign m_awsize=4;assign m_awburst=1;
 assign m_wvalid=(state==W) && s_wvalid[owner];
 assign m_wdata=s_wdata[owner*128+:128];
 assign m_wstrb=s_wstrb[owner*16+:16];
 assign m_wlast=(state==W) && expected_last;
 assign m_bready=(state==B) && s_bready[owner];
 assign m_arvalid=(state==AR);
 assign m_araddr=address;assign m_arlen=length;assign m_arsize=4;assign m_arburst=1;
 assign m_rready=(state==R) && s_rready[owner];
 always @* begin
   choice=-1;
   for(k=0;k<2*N;k=k+1) begin
     index=round_robin+k;
     if(index>=2*N) index=index-2*N;
     if(choice<0 && ((index%2==0 && s_awvalid[index/2]) ||
                     (index%2==1 && s_arvalid[index/2]))) choice=index;
   end
   s_awready=0;s_wready=0;s_bvalid=0;s_bresp=0;
   s_arready=0;s_rvalid=0;s_rdata=0;s_rlast=0;s_rresp=0;
   case(state)
     AW: s_awready[owner]=m_awready;
     W: s_wready[owner]=m_wready;
     B: begin s_bvalid[owner]=m_bvalid;s_bresp[owner*2+:2]=m_bresp;end
     AR: s_arready[owner]=m_arready;
     R: begin
       s_rvalid[owner]=m_rvalid;s_rdata[owner*128+:128]=m_rdata;
       s_rlast[owner]=m_rlast;s_rresp[owner*2+:2]=m_rresp;
     end
   endcase
 end
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin state<=IDLE;owner<=0;round_robin<=0;
     address<=0;length<=0;beats<=0;protocol_error<=0;
   end else case(state)
     IDLE: if(choice>=0) begin
       owner<=choice/2;beats<=0;
       round_robin<=(choice==2*N-1)?0:choice+1;
       if(choice%2==0) begin
         address<=s_awaddr[(choice/2)*32+:32];
         length<=s_awlen[(choice/2)*8+:8];state<=AW;
         if(s_awaddr[(choice/2)*32+:4]!=0 ||
           ({1'b0,s_awaddr[(choice/2)*32+:12]}+
            (({5'b0,s_awlen[(choice/2)*8+:8]}+1)<<4))>4096) protocol_error<=1;
       end else begin
         address<=s_araddr[(choice/2)*32+:32];
         length<=s_arlen[(choice/2)*8+:8];state<=AR;
         if(s_araddr[(choice/2)*32+:4]!=0 ||
           ({1'b0,s_araddr[(choice/2)*32+:12]}+
            (({5'b0,s_arlen[(choice/2)*8+:8]}+1)<<4))>4096) protocol_error<=1;
       end
     end
     AW: if(m_awvalid && m_awready) state<=W;
     W: if(m_wvalid && m_wready) begin
       if(s_wlast[owner]!=expected_last) protocol_error<=1;
       if(expected_last) state<=B; else beats<=beats+9'd1;
     end
     B: if(m_bvalid && m_bready) state<=IDLE;
     AR: if(m_arvalid && m_arready) state<=R;
     R: if(m_rvalid && m_rready) begin
       if(m_rlast!=expected_last) protocol_error<=1;
       if(m_rlast) state<=IDLE; else beats<=beats+9'd1;
     end
   endcase
 end
endmodule

