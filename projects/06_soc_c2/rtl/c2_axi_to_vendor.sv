`timescale 1ns/1ps
// Full AXI source -> vendor beta's ID-less, full-width INCR source port.
// One read and one write outstanding. IDs are retained until final response.
// Optional single-beat narrow accesses use AXI byte lanes unchanged; only the
// downstream address is aligned. Unsupported requests terminate with DECERR.
module c2_axi_to_vendor #(
 parameter ID_WIDTH=8,parameter ALLOW_NARROW=0,
 parameter [31:0] SOURCE_BASE=0,TARGET_BASE=0,WINDOW_BYTES=32'h01000000
)(
 input wire clk,rst_n,enable,
 input wire s_awvalid,output wire s_awready,input wire [ID_WIDTH-1:0] s_awid,
 input wire [31:0] s_awaddr,input wire [7:0] s_awlen,input wire [2:0] s_awsize,
 input wire [1:0] s_awburst,input wire s_awlock,
 input wire s_wvalid,output wire s_wready,input wire [127:0] s_wdata,
 input wire [15:0] s_wstrb,input wire s_wlast,
 output wire s_bvalid,input wire s_bready,output wire [ID_WIDTH-1:0] s_bid,output wire [1:0] s_bresp,
 input wire s_arvalid,output wire s_arready,input wire [ID_WIDTH-1:0] s_arid,
 input wire [31:0] s_araddr,input wire [7:0] s_arlen,input wire [2:0] s_arsize,
 input wire [1:0] s_arburst,input wire s_arlock,
 output wire s_rvalid,input wire s_rready,output wire [ID_WIDTH-1:0] s_rid,
 output wire [127:0] s_rdata,output wire [1:0] s_rresp,output wire s_rlast,
 output wire m_awvalid,input wire m_awready,output wire [31:0] m_awaddr,output wire [7:0] m_awlen,
 output wire m_wvalid,input wire m_wready,output wire [127:0] m_wdata,
 output wire [15:0] m_wstrb,output wire m_wlast,
 input wire m_bvalid,output wire m_bready,input wire [1:0] m_bresp,
 output wire m_arvalid,input wire m_arready,output wire [31:0] m_araddr,output wire [7:0] m_arlen,
 input wire m_rvalid,output wire m_rready,input wire [127:0] m_rdata,
 input wire [1:0] m_rresp,input wire m_rlast,
 output reg rejected,output reg protocol_error
);
 localparam WI=0,WA=1,WD=2,WB=3,WX=4,WE=5;
 localparam RI=0,RA=1,RD=2,RX=3;
 reg [2:0] ws;reg [1:0] rs;
 reg [ID_WIDTH-1:0] wid,rid;
 reg [31:0] wa,ra;reg [7:0] wl,rl;
 reg [8:0] wc,rc;
 reg [15:0] allowed_strobes;
 function legal(input [31:0] address,input [7:0] length,input [2:0] size,
                input [1:0] burst,input locked);
   reg [32:0] last_byte,translated_end,span,aligned;
   begin
     aligned={1'b0,address[31:4],4'b0};
     span=({25'b0,length}+33'd1)<<4;
     last_byte=aligned+span;
     translated_end={1'b0,TARGET_BASE}+(last_byte-{1'b0,SOURCE_BASE});
     legal=enable && !locked && WINDOW_BYTES!=0 && SOURCE_BASE[3:0]==0 && TARGET_BASE[3:0]==0 &&
       size<=4 && ((size==4 && address[3:0]==0) ||
        (ALLOW_NARROW && length==0 && (address & ((32'd1<<size)-32'd1))==0)) &&
       (burst==1 || (length==0 && burst==0)) &&
       aligned>={1'b0,SOURCE_BASE} && last_byte<=({1'b0,SOURCE_BASE}+{1'b0,WINDOW_BYTES}) &&
       translated_end<=33'h100000000 &&
       ({1'b0,address[11:4],4'b0}+span)<=4096;
   end
 endfunction
 assign s_awready=rst_n && ws==WI;assign s_arready=rst_n && rs==RI;
 assign m_awvalid=ws==WA;assign m_awaddr=wa;assign m_awlen=wl;
 assign m_arvalid=rs==RA;assign m_araddr=ra;assign m_arlen=rl;
 assign m_wvalid=ws==WD && s_wvalid;assign m_wdata=s_wdata;
 assign m_wstrb=s_wstrb & allowed_strobes;assign m_wlast=wc=={1'b0,wl};
 assign s_wready=ws==WX || (ws==WD && m_wready);
 assign s_bvalid=ws==WE || (ws==WB && m_bvalid);assign s_bid=wid;
 assign s_bresp=ws==WE?2'b11:m_bresp;assign m_bready=ws==WB && s_bready;
 assign s_rvalid=rs==RX || (rs==RD && m_rvalid);assign s_rid=rid;
 assign s_rdata=rs==RX?128'b0:m_rdata;assign s_rresp=rs==RX?2'b11:m_rresp;
 assign s_rlast=rs==RX?(rc=={1'b0,rl}):m_rlast;
 assign m_rready=rs==RD && s_rready;
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin ws<=WI;rs<=RI;wid<=0;rid<=0;wa<=0;ra<=0;wl<=0;rl<=0;
     wc<=0;rc<=0;allowed_strobes<=0;rejected<=0;protocol_error<=0;end
   else begin
     case(ws)
       WI: if(s_awvalid && s_awready) begin
         wid<=s_awid;wl<=s_awlen;wc<=0;
         wa<=((s_awaddr-SOURCE_BASE)&32'hfffffff0)+TARGET_BASE;
         allowed_strobes<=s_awsize==4?16'hffff:
           ((16'h0001<<(1<<s_awsize))-16'h0001)<<s_awaddr[3:0];
         if(legal(s_awaddr,s_awlen,s_awsize,s_awburst,s_awlock)) ws<=WA;
         else begin ws<=WX;rejected<=1;end
       end
       WA: if(m_awready) ws<=WD;
       WD,WX: if(s_wvalid && s_wready) begin
         if(s_wlast!=(wc=={1'b0,wl})) protocol_error<=1;
         if(ws==WD && (s_wstrb & ~allowed_strobes)!=0) protocol_error<=1;
         if(wc=={1'b0,wl}) ws<=ws==WX?WE:WB;else wc<=wc+9'd1;
       end
       WB,WE: if(s_bvalid && s_bready) ws<=WI;
     endcase
     case(rs)
       RI: if(s_arvalid && s_arready) begin
         rid<=s_arid;rl<=s_arlen;rc<=0;
         ra<=((s_araddr-SOURCE_BASE)&32'hfffffff0)+TARGET_BASE;
         if(legal(s_araddr,s_arlen,s_arsize,s_arburst,s_arlock)) rs<=RA;
         else begin rs<=RX;rejected<=1;end
       end
       RA: if(m_arready) rs<=RD;
       RD,RX: if(s_rvalid && s_rready) begin
         if(rs==RD && m_rlast!=(rc=={1'b0,rl})) protocol_error<=1;
         if(s_rlast) rs<=RI;else rc<=rc+9'd1;
       end
     endcase
   end
 end
endmodule
