`timescale 1ns/1ps
// Three GRAY8 banks in the C2 video aperture. One writer, one scan reader.
// Full response-fenced writes publish READY; DISPLAY is retained for repeats.
// Collect a whole burst locally before AW/AR so neither source nor display
// FIFO backpressure can indefinitely occupy the shared DDR fabric.
module c2_video_framebuffer #(
 parameter integer WIDTH=1920,HEIGHT=1080,OUT_FIFO_BITS=6,
 parameter integer STRIDE=((WIDTH+15)/16)*16,
 parameter integer BANK_PITCH=((STRIDE*HEIGHT+4095)/4096)*4096
)(
 input wire arst_n,clk,display_clk,enable,
 input wire in_valid,output wire in_ready,input wire [129:0] in_data,
 input wire scan_valid,output wire scan_ready,
 output wire out_valid,input wire out_ready,output wire [129:0] out_data,
 output wire awvalid,input wire awready,output wire [31:0] awaddr,output wire [7:0] awlen,
 output wire wvalid,input wire wready,output wire [127:0] wdata,
 output wire [15:0] wstrb,output wire wlast,input wire bvalid,output wire bready,input wire [1:0] bresp,
 output wire arvalid,input wire arready,output wire [31:0] araddr,output wire [7:0] arlen,
 input wire rvalid,output wire rready,input wire [127:0] rdata,input wire rlast,input wire [1:0] rresp,
 output reg [31:0] published,dropped,write_errors,read_errors,repeated,empty_scans,
 output reg [31:0] max_aw_wait,max_ar_wait,
 output wire [5:0] bank_states
);
 localparam integer WORDS=STRIDE*HEIGHT/16;
 localparam [1:0] FREE=0,WRITING=1,READY=2,DISPLAY=3;
 localparam [2:0] W_IDLE=0,W_FILL=1,W_AW=2,W_DATA=3,W_B=4,W_DRAIN=5;
 localparam [3:0] R_IDLE=0,R_HEADER=1,R_AR=2,R_DATA=3,R_SEND=4,R_ABORT=5,R_END=6,R_ACK=7;
 reg [1:0] banks[0:2];reg [31:0] ids[0:2],stamps[0:2],orders[0:2];
 reg [31:0] order_next;
 reg [2:0] ws;reg [3:0] rs;
 reg [1:0] wb,rb,display_bank;reg display_held;
 reg [31:0] wid,wstamp,w_offset,r_offset,aw_wait,ar_wait;
 reg [4:0] fill,beats,windex,rindex,send_index,rbeats;
 reg [127:0] wbuf[0:15],rbuf[0:15];
 reg ended,wbad,available,rbad;
 reg [31:0] rid,rstamp;
 wire req_valid,req_ready,done_valid,done_ready;
 wire ignored_req,ignored_done;
 wire fifo_ready;reg fifo_valid;reg [129:0] fifo_data;
 integer j,free_bank,ready_bank;
 assign bank_states={banks[2],banks[1],banks[0]};
 wire [95:0] order_values={orders[2],orders[1],orders[0]};
 wire [127:0] send_word=rbuf[send_index[3:0]];
 c2_cdc_mailbox #(.WIDTH(1)) request_cdc(.arst_n(arst_n),.s_clk(display_clk),
  .s_valid(scan_valid),.s_ready(scan_ready),.s_data(1'b0),.d_clk(clk),
  .d_valid(req_valid),.d_ready(req_ready),.d_data(ignored_req));
 // END acknowledgement prevents a new scan from reusing live output FIFO data.
 c2_cdc_mailbox #(.WIDTH(1)) done_cdc(.arst_n(arst_n),.s_clk(display_clk),
  .s_valid(out_valid && out_ready && out_data[129:128]==2),.s_ready(done_ready),.s_data(1'b0),
  .d_clk(clk),.d_valid(done_valid),.d_ready(rs==R_ACK),.d_data(ignored_done));
 wire raw_valid;wire [129:0] raw_data;
 assign out_valid=raw_valid && (raw_data[129:128]!=2 || done_ready);
 assign out_data=raw_data;
 c2_async_fifo #(.WIDTH(130),.ADDR_BITS(OUT_FIFO_BITS)) output_cdc(
  .arst_n(arst_n),.s_clk(clk),.s_valid(fifo_valid),.s_ready(fifo_ready),.s_data(fifo_data),
  .d_clk(display_clk),.d_valid(raw_valid),.d_ready(out_ready && (raw_data[129:128]!=2 || done_ready)),.d_data(raw_data));
 assign req_ready=rs==R_IDLE && enable;
 assign in_ready=enable && (ws==W_IDLE || ws==W_DRAIN || (ws==W_FILL && fill<16 && !ended));
 assign awvalid=ws==W_AW;assign awaddr=32'(wb)*BANK_PITCH+w_offset*16;assign awlen=8'(beats-1'b1);
 assign wvalid=ws==W_DATA;assign wdata=wbuf[windex[3:0]];assign wstrb=16'hffff;assign wlast=windex==beats-1;
 assign bready=ws==W_B;
 assign arvalid=rs==R_AR;assign araddr=32'(rb)*BANK_PITCH+r_offset*16;assign arlen=8'(rbeats-1'b1);
 assign rready=rs==R_DATA;
 always @* begin
  free_bank=-1;ready_bank=-1;
  for(integer k=0;k<3;k=k+1) begin
   if(bank_states[k*2+:2]==FREE && free_bank==-1) free_bank=k;
   if(bank_states[k*2+:2]==READY) begin
    if(ready_bank==-1) ready_bank=k;
    else if($signed(order_values[k*32+:32]-order_values[ready_bank*32+:32])<0) ready_bank=k;
   end
  end
  fifo_valid=0;fifo_data=0;
  case(rs)
   R_HEADER:begin fifo_valid=1;fifo_data={2'd1,63'b0,available,rstamp,rid};end
   R_SEND:begin fifo_valid=1;fifo_data={2'd0,send_word};end
   R_ABORT:begin fifo_valid=1;fifo_data={2'd3,128'b0};end
   R_END:begin fifo_valid=1;fifo_data={2'd2,127'b0,rbad};end
   default:begin end
  endcase
 end
 always @(posedge clk or negedge arst_n) begin
  if(!arst_n) begin
   for(j=0;j<3;j=j+1) begin banks[j]<=FREE;ids[j]<=0;stamps[j]<=0;orders[j]<=0;end
   ws<=W_IDLE;rs<=R_IDLE;wb<=0;rb<=0;display_bank<=0;display_held<=0;order_next<=0;
   wid<=0;wstamp<=0;w_offset<=0;r_offset<=0;aw_wait<=0;ar_wait<=0;
   fill<=0;beats<=0;windex<=0;rindex<=0;send_index<=0;rbeats<=0;ended<=0;wbad<=0;
   available<=0;rbad<=0;rid<=0;rstamp<=0;
   published<=0;dropped<=0;write_errors<=0;read_errors<=0;repeated<=0;empty_scans<=0;
   max_aw_wait<=0;max_ar_wait<=0;
  end else begin
   if(awvalid && !awready) begin aw_wait<=aw_wait+1'b1;if(aw_wait+1>max_aw_wait) max_aw_wait<=aw_wait+1'b1;end
   else aw_wait<=0;
   if(arvalid && !arready) begin ar_wait<=ar_wait+1'b1;if(ar_wait+1>max_ar_wait) max_ar_wait<=ar_wait+1'b1;end
   else ar_wait<=0;
   case(ws)
    W_IDLE:if(in_valid && in_ready && in_data[129:128]==1) begin
     wid<=in_data[31:0];wstamp<=in_data[63:32];w_offset<=0;fill<=0;ended<=0;wbad<=0;
     if(free_bank>=0) begin wb<=2'(free_bank);banks[free_bank]<=WRITING;ws<=W_FILL;end
     else begin ws<=W_DRAIN;dropped<=dropped+1'b1;end
    end
    W_FILL:begin
     if(fill==16 || ended) begin
      if(fill!=0) begin beats<=fill;windex<=0;ws<=W_AW;end
      else if(ended) begin
       if(!wbad && w_offset==WORDS) begin
        banks[wb]<=READY;ids[wb]<=wid;stamps[wb]<=wstamp;orders[wb]<=order_next;
        order_next<=order_next+1'b1;published<=published+1'b1;
       end else begin banks[wb]<=FREE;dropped<=dropped+1'b1;end
       ws<=W_IDLE;
      end
     end else if(in_valid && in_ready) begin
      if(in_data[129:128]==0) begin
       if(w_offset+32'(fill)<WORDS) begin wbuf[fill[3:0]]<=in_data[127:0];fill<=fill+1'b1;end
       else wbad<=1;
      end else if(in_data[129:128]==2) begin
       ended<=1;if(in_data[32] || in_data[31:0]!=wid) wbad<=1;
      end else begin wbad<=1;end
     end
    end
    W_AW:if(awready) ws<=W_DATA;
    W_DATA:if(wready) begin if(wlast) ws<=W_B;else windex<=windex+1'b1;end
    W_B:if(bvalid) begin
     w_offset<=w_offset+32'(beats);fill<=0;
     if(bresp!=0) begin
      write_errors<=write_errors+1'b1;
      if(ended) begin banks[wb]<=FREE;dropped<=dropped+1'b1;ws<=W_IDLE;end
      else begin banks[wb]<=FREE;dropped<=dropped+1'b1;ws<=W_DRAIN;end
     end else ws<=W_FILL;
    end
    W_DRAIN:if(in_valid && in_ready && in_data[129:128]==2) ws<=W_IDLE;
    default:ws<=W_IDLE;
   endcase
   case(rs)
    R_IDLE:if(req_valid && req_ready) begin
     r_offset<=0;rbad<=0;available<=0;rid<=0;rstamp<=0;rs<=R_HEADER;
     if(ready_bank>=0) begin
      if(display_held) banks[display_bank]<=FREE;
      rb<=2'(ready_bank);display_bank<=2'(ready_bank);display_held<=1;banks[ready_bank]<=DISPLAY;
      available<=1;rid<=ids[ready_bank];rstamp<=stamps[ready_bank];
     end else if(display_held) begin
      rb<=display_bank;available<=1;rid<=ids[display_bank];rstamp<=stamps[display_bank];repeated<=repeated+1'b1;
     end else empty_scans<=empty_scans+1'b1;
    end
    R_HEADER:if(fifo_ready) begin
     if(available) begin rbeats<=5'(WORDS<16?WORDS:16);rs<=R_AR;end else rs<=R_END;
    end
    R_AR:if(arready) begin rindex<=0;rs<=R_DATA;end
    R_DATA:if(rvalid) begin
     rbuf[rindex[3:0]]<=rdata;rindex<=rindex+1'b1;
     if(rresp!=0 || rlast!=(rindex==rbeats-1)) rbad<=1;
     if(rindex==rbeats-1) begin
      send_index<=0;
      if(rbad || rresp!=0 || !rlast) begin read_errors<=read_errors+1'b1;rs<=R_ABORT;end
      else rs<=R_SEND;
     end
    end
    R_SEND:if(fifo_ready) begin
     if(send_index==rbeats-1) begin
      r_offset<=r_offset+32'(rbeats);
      if(r_offset+32'(rbeats)==WORDS) rs<=R_END;
      else begin rbeats<=5'(WORDS-r_offset-32'(rbeats)<16?WORDS-r_offset-32'(rbeats):16);rs<=R_AR;end
     end else send_index<=send_index+1'b1;
    end
    R_ABORT:if(fifo_ready) begin rbad<=1;rs<=R_END;end
    R_END:if(fifo_ready) rs<=R_ACK;
    R_ACK:if(done_valid) begin
     if(rbad && display_held) begin banks[display_bank]<=FREE;display_held<=0;end
     rs<=R_IDLE;
    end
    default:rs<=R_IDLE;
   endcase
  end
 end
endmodule
