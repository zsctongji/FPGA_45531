`timescale 1ns/1ps
module tb_c2_vendor #(parameter MEM_HALF=5,parameter VIDEO_HALF=7);
localparam N=3;
reg pclk=0;always #11 pclk=~pclk;
reg clk=0,vclk=0,rst_n=1,inject_b_error=0,inject_r_error=0;
always #(MEM_HALF) clk=~clk;always #(VIDEO_HALF) vclk=~vclk;
reg [N*1-1:0] s_awvalid=0;
wire [N*1-1:0] s_awready;
reg [N*32-1:0] s_awaddr=0;
reg [N*8-1:0] s_awlen=0;
reg [N*1-1:0] s_wvalid=0;
wire [N*1-1:0] s_wready;
reg [N*128-1:0] s_wdata=0;
reg [N*16-1:0] s_wstrb=0;
reg [N*1-1:0] s_wlast=0;
wire [N*1-1:0] s_bvalid;
reg [N*1-1:0] s_bready=0;
wire [N*2-1:0] s_bresp;
reg [N*1-1:0] s_arvalid=0;
wire [N*1-1:0] s_arready;
reg [N*32-1:0] s_araddr=0;
reg [N*8-1:0] s_arlen=0;
wire [N*1-1:0] s_rvalid;
reg [N*1-1:0] s_rready=0;
wire [N*128-1:0] s_rdata;
wire [N*1-1:0] s_rlast;
wire [N*2-1:0] s_rresp;
wire [0:0] m_awvalid;
wire [0:0] m_awready;
wire [31:0] m_awaddr;
wire [7:0] m_awlen;
wire [2:0] m_awsize;
wire [1:0] m_awburst;
wire [0:0] m_wvalid;
wire [0:0] m_wready;
wire [127:0] m_wdata;
wire [15:0] m_wstrb;
wire [0:0] m_wlast;
wire [0:0] m_bvalid;
wire [0:0] m_bready;
wire [1:0] m_bresp;
wire [0:0] m_arvalid;
wire [0:0] m_arready;
wire [31:0] m_araddr;
wire [7:0] m_arlen;
wire [2:0] m_arsize;
wire [1:0] m_arburst;
wire [0:0] m_rvalid;
wire [0:0] m_rready;
wire [127:0] m_rdata;
wire [0:0] m_rlast;
wire [1:0] m_rresp;
wire protocol_error;
wire [31:0] completed_writes,completed_reads;
reg req_valid=0,event_ready=0;
reg [543:0] req_payload=0;
wire req_ready,frame_valid,frame_ready;
wire [543:0] frame_payload;
wire result_valid,result_ready,result_slot;
wire [2:0] result_status;
wire [31:0] result_generation;
wire [511:0] result_descriptor;
wire delivered_valid;
wire [547:0] delivered;
wire image_start_valid,image_start_ready,image_ready,image_done_valid,image_done_ready,image_error;
wire [31:0] image_address,image_checksum;
reg image_valid=0;
reg [127:0] image_words=0;
reg ctl_valid=0,ctl_rsp_ready=0,ctl_slot=0;
reg [2:0] ctl_cmd=0;
reg [31:0] ctl_generation=0;
wire ctl_ready,ctl_rsp_valid;
wire [1:0] ctl_status;
wire [511:0] ctl_descriptor;
wire [3:0] states;
wire [31:0] dropped;
wire ctl_rsp_slot;wire [31:0] ctl_rsp_generation;
wire grant_valid,grant_ready;wire [31:0] grant_frame_id;
reg [15:0] paddr=0;reg psel=0,penable=0,pwrite=0;
reg [31:0] pwdata=0;wire [31:0] prdata;wire pready,pslverror,irq;
wire core_protocol_error,cpu_adapter_error,cpu_rejected;
wire [7:0] cpu_bid,cpu_rid;
wire [2:0] u_awvalid;
wire [2:0] u_awready;
wire [95:0] u_awaddr;
wire [23:0] u_awlen;
wire [2:0] u_wvalid;
wire [2:0] u_wready;
wire [383:0] u_wdata;
wire [47:0] u_wstrb;
wire [2:0] u_wlast;
wire [2:0] u_bvalid;
wire [2:0] u_bready;
wire [5:0] u_bresp;
wire [2:0] u_arvalid;
wire [2:0] u_arready;
wire [95:0] u_araddr;
wire [23:0] u_arlen;
wire [2:0] u_rvalid;
wire [2:0] u_rready;
wire [383:0] u_rdata;
wire [2:0] u_rlast;
wire [5:0] u_rresp;
c2_vendor_attachment #(.SHARED_BASE(0),.VIDEO_BASE(32'h20000),.VIDEO_BYTES(32'h10000)) dut(
.arst_n(rst_n),.mem_clk(clk),.video_clk(vclk),.pclk(pclk),.map_enable(1'b1),
.external_protocol_error(cpu_adapter_error || cpu_rejected),
.v_source_valid(1'b0),.v_source_ready(),.v_source_error(1'b0),.v_source_frame_id(32'b0),.v_source_fnv(32'b0),
.paddr(paddr),.psel(psel),.penable(penable),.pwrite(pwrite),.pwdata(pwdata),
.pready(pready),.prdata(prdata),.pslverror(pslverror),.irq(irq),
.v_frame_valid(req_valid),.v_frame_ready(req_ready),.v_descriptor(req_payload[511:0]),
.v_grant_valid(grant_valid),.v_grant_ready(grant_ready),.v_grant_frame_id(grant_frame_id),
.v_word_valid(image_valid),.v_word_ready(image_ready),.v_word_data(image_words),
.v_event_valid(delivered_valid),.v_event_ready(event_ready),
.v_event_status(delivered[547:545]),.v_event_slot(delivered[544]),
.v_event_generation(delivered[543:512]),.v_event_descriptor(delivered[511:0]),
.video_awid(4'he),.video_arid(4'h7),.video_bid(),.video_rid(),
.video_awsize(3'd4),.video_arsize(3'd4),
.video_awburst(2'b01),.video_arburst(2'b01),.video_awlock(1'b0),.video_arlock(1'b0),
.video_awvalid(s_awvalid[2+:1]),
.video_awready(s_awready[2+:1]),
.video_awaddr(s_awaddr[64+:32]),
.video_awlen(s_awlen[16+:8]),
.video_wvalid(s_wvalid[2+:1]),
.video_wready(s_wready[2+:1]),
.video_wdata(s_wdata[256+:128]),
.video_wstrb(s_wstrb[32+:16]),
.video_wlast(s_wlast[2+:1]),
.video_bvalid(s_bvalid[2+:1]),
.video_bready(s_bready[2+:1]),
.video_bresp(s_bresp[4+:2]),
.video_arvalid(s_arvalid[2+:1]),
.video_arready(s_arready[2+:1]),
.video_araddr(s_araddr[64+:32]),
.video_arlen(s_arlen[16+:8]),
.video_rvalid(s_rvalid[2+:1]),
.video_rready(s_rready[2+:1]),
.video_rdata(s_rdata[256+:128]),
.video_rlast(s_rlast[2+:1]),
.video_rresp(s_rresp[4+:2]),
.m_awvalid(u_awvalid[1+:1]),
.m_awready(u_awready[1+:1]),
.m_awaddr(u_awaddr[32+:32]),
.m_awlen(u_awlen[8+:8]),
.m_awsize(),
.m_awburst(),
.m_wvalid(u_wvalid[1+:1]),
.m_wready(u_wready[1+:1]),
.m_wdata(u_wdata[128+:128]),
.m_wstrb(u_wstrb[16+:16]),
.m_wlast(u_wlast[1+:1]),
.m_bvalid(u_bvalid[1+:1]),
.m_bready(u_bready[1+:1]),
.m_bresp(u_bresp[2+:2]),
.m_arvalid(u_arvalid[1+:1]),
.m_arready(u_arready[1+:1]),
.m_araddr(u_araddr[32+:32]),
.m_arlen(u_arlen[8+:8]),
.m_arsize(),
.m_arburst(),
.m_rvalid(u_rvalid[1+:1]),
.m_rready(u_rready[1+:1]),
.m_rdata(u_rdata[128+:128]),
.m_rlast(u_rlast[1+:1]),
.m_rresp(u_rresp[2+:2]),
.protocol_error(core_protocol_error));
c2_axi_to_vendor #(.ALLOW_NARROW(1),.WINDOW_BYTES(32'h40000)) cpu_adapter(
.clk(clk),.rst_n(rst_n),.enable(1'b1),
.s_awid(8'hc7),.s_arid(8'hd9),.s_bid(cpu_bid),.s_rid(cpu_rid),
.s_awsize(3'd4),.s_arsize(3'd4),.s_awburst(2'b01),.s_arburst(2'b01),.s_awlock(1'b0),.s_arlock(1'b0),
.s_awvalid(s_awvalid[0+:1]),
.s_awready(s_awready[0+:1]),
.s_awaddr(s_awaddr[0+:32]),
.s_awlen(s_awlen[0+:8]),
.s_wvalid(s_wvalid[0+:1]),
.s_wready(s_wready[0+:1]),
.s_wdata(s_wdata[0+:128]),
.s_wstrb(s_wstrb[0+:16]),
.s_wlast(s_wlast[0+:1]),
.s_bvalid(s_bvalid[0+:1]),
.s_bready(s_bready[0+:1]),
.s_bresp(s_bresp[0+:2]),
.s_arvalid(s_arvalid[0+:1]),
.s_arready(s_arready[0+:1]),
.s_araddr(s_araddr[0+:32]),
.s_arlen(s_arlen[0+:8]),
.s_rvalid(s_rvalid[0+:1]),
.s_rready(s_rready[0+:1]),
.s_rdata(s_rdata[0+:128]),
.s_rlast(s_rlast[0+:1]),
.s_rresp(s_rresp[0+:2]),
.m_awvalid(u_awvalid[0+:1]),
.m_awready(u_awready[0+:1]),
.m_awaddr(u_awaddr[0+:32]),
.m_awlen(u_awlen[0+:8]),
.m_wvalid(u_wvalid[0+:1]),
.m_wready(u_wready[0+:1]),
.m_wdata(u_wdata[0+:128]),
.m_wstrb(u_wstrb[0+:16]),
.m_wlast(u_wlast[0+:1]),
.m_bvalid(u_bvalid[0+:1]),
.m_bready(u_bready[0+:1]),
.m_bresp(u_bresp[0+:2]),
.m_arvalid(u_arvalid[0+:1]),
.m_arready(u_arready[0+:1]),
.m_araddr(u_araddr[0+:32]),
.m_arlen(u_arlen[0+:8]),
.m_rvalid(u_rvalid[0+:1]),
.m_rready(u_rready[0+:1]),
.m_rdata(u_rdata[0+:128]),
.m_rlast(u_rlast[0+:1]),
.m_rresp(u_rresp[0+:2]),
.rejected(cpu_rejected),.protocol_error(cpu_adapter_error));
assign u_awvalid[2+:1]=s_awvalid[1+:1];
assign s_awready[1+:1]=u_awready[2+:1];
assign u_awaddr[64+:32]=s_awaddr[32+:32];
assign u_awlen[16+:8]=s_awlen[8+:8];
assign u_wvalid[2+:1]=s_wvalid[1+:1];
assign s_wready[1+:1]=u_wready[2+:1];
assign u_wdata[256+:128]=s_wdata[128+:128];
assign u_wstrb[32+:16]=s_wstrb[16+:16];
assign u_wlast[2+:1]=s_wlast[1+:1];
assign s_bvalid[1+:1]=u_bvalid[2+:1];
assign u_bready[2+:1]=s_bready[1+:1];
assign s_bresp[2+:2]=u_bresp[4+:2];
assign u_arvalid[2+:1]=s_arvalid[1+:1];
assign s_arready[1+:1]=u_arready[2+:1];
assign u_araddr[64+:32]=s_araddr[32+:32];
assign u_arlen[16+:8]=s_arlen[8+:8];
assign s_rvalid[1+:1]=u_rvalid[2+:1];
assign u_rready[2+:1]=s_rready[1+:1];
assign s_rdata[128+:128]=u_rdata[256+:128];
assign s_rlast[1+:1]=u_rlast[2+:1];
assign s_rresp[2+:2]=u_rresp[4+:2];
c2_axi_arbiter #(.N(3)) vendor_interface_model(.clk(clk),.rst_n(rst_n),
.s_awvalid(u_awvalid),
.s_awready(u_awready),
.s_awaddr(u_awaddr),
.s_awlen(u_awlen),
.s_wvalid(u_wvalid),
.s_wready(u_wready),
.s_wdata(u_wdata),
.s_wstrb(u_wstrb),
.s_wlast(u_wlast),
.s_bvalid(u_bvalid),
.s_bready(u_bready),
.s_bresp(u_bresp),
.s_arvalid(u_arvalid),
.s_arready(u_arready),
.s_araddr(u_araddr),
.s_arlen(u_arlen),
.s_rvalid(u_rvalid),
.s_rready(u_rready),
.s_rdata(u_rdata),
.s_rlast(u_rlast),
.s_rresp(u_rresp),
.m_awvalid(m_awvalid),
.m_awready(m_awready),
.m_awaddr(m_awaddr),
.m_awlen(m_awlen),
.m_awsize(m_awsize),
.m_awburst(m_awburst),
.m_wvalid(m_wvalid),
.m_wready(m_wready),
.m_wdata(m_wdata),
.m_wstrb(m_wstrb),
.m_wlast(m_wlast),
.m_bvalid(m_bvalid),
.m_bready(m_bready),
.m_bresp(m_bresp),
.m_arvalid(m_arvalid),
.m_arready(m_arready),
.m_araddr(m_araddr),
.m_arlen(m_arlen),
.m_arsize(m_arsize),
.m_arburst(m_arburst),
.m_rvalid(m_rvalid),
.m_rready(m_rready),
.m_rdata(m_rdata),
.m_rlast(m_rlast),
.m_rresp(m_rresp),
.protocol_error(protocol_error));
assign image_start_valid=dut.core.image_start_valid;assign image_start_ready=dut.core.image_start_ready;
assign image_done_valid=dut.core.image_done_valid;assign image_done_ready=dut.core.image_done_ready;
assign image_error=dut.core.image_error;assign frame_valid=dut.core.frame_valid;assign frame_ready=dut.core.frame_ready;
assign states=dut.core.slot_states;assign grant_ready=!active;
always @(posedge clk) if(rst_n) begin
 if(s_bvalid[0] && cpu_bid!==8'hc7) $fatal(1,"CPU BID lost");
 if(s_rvalid[0] && cpu_rid!==8'hd9) $fatal(1,"CPU RID lost");
end
c2_ddr_model memory_model(.clk(clk),.rst_n(rst_n),.inject_b_error(inject_b_error),.inject_r_error(inject_r_error),
.awvalid(m_awvalid),
.awready(m_awready),
.awaddr(m_awaddr),
.awlen(m_awlen),
.awsize(m_awsize),
.awburst(m_awburst),
.wvalid(m_wvalid),
.wready(m_wready),
.wdata(m_wdata),
.wstrb(m_wstrb),
.wlast(m_wlast),
.bvalid(m_bvalid),
.bready(m_bready),
.bresp(m_bresp),
.arvalid(m_arvalid),
.arready(m_arready),
.araddr(m_araddr),
.arlen(m_arlen),
.arsize(m_arsize),
.arburst(m_arburst),
.rvalid(m_rvalid),
.rready(m_rready),
.rdata(m_rdata),
.rlast(m_rlast),
.rresp(m_rresp),
.completed_writes(completed_writes),
.completed_reads(completed_reads));
integer checks=0,write_transactions=0,read_transactions=0;
function [127:0] pattern(input integer tag,input integer beat);
 integer lane;begin for(lane=0;lane<4;lane=lane+1) pattern[lane*32+:32]=tag*65536+beat*4+lane;end
endfunction
function [127:0] masked_pattern(input integer tag,input integer beat);
 reg [127:0] p;reg [15:0] mask;integer b;
 begin
   p=pattern(tag,beat);mask=16'hffff<<(beat%4);
   for(b=0;b<16;b=b+1) if(!mask[b]) p[b*8+:8]=0;
   masked_pattern=p;
 end
endfunction
task automatic write_burst(input integer p,input integer addr,input integer count,
                           input integer tag,input [1:0] response);
 integer b;
 begin
   @(negedge clk);s_awvalid[p]=1;s_awaddr[p*32+:32]=addr;s_awlen[p*8+:8]=count-1;
   do @(posedge clk);while(!s_awready[p]);
   @(negedge clk);s_awvalid[p]=0;
   for(b=0;b<count;b=b+1) begin
     repeat((b+p)%3) @(negedge clk);
     s_wvalid[p]=1;s_wdata[p*128+:128]=pattern(tag,b);
     s_wstrb[p*16+:16]=16'hffff<<(b%4);s_wlast[p]=(b==count-1);
     do @(posedge clk);while(!s_wready[p]);
     @(negedge clk);s_wvalid[p]=0;s_wlast[p]=0;
   end
   repeat(p+2) @(negedge clk);
   s_bready[p]=1;
   do @(posedge clk);while(!s_bvalid[p]);
   if(s_bresp[p*2+:2]!==response) $fatal(1,"B response misrouted p=%d",p);
   checks=checks+1;write_transactions=write_transactions+1;
   @(negedge clk);s_bready[p]=0;
 end
endtask
task automatic read_burst(input integer p,input integer addr,input integer count,
                          input integer tag,input [1:0] response);
 integer b;
 begin
   @(negedge clk);s_arvalid[p]=1;s_araddr[p*32+:32]=addr;s_arlen[p*8+:8]=count-1;
   do @(posedge clk);while(!s_arready[p]);
   @(negedge clk);s_arvalid[p]=0;
   for(b=0;b<count;b=b+1) begin
     repeat((b+2*p)%4) @(negedge clk);
     s_rready[p]=1;
     do @(posedge clk);while(!s_rvalid[p]);
     if(s_rresp[p*2+:2]!==response || s_rlast[p]!=(b==count-1) ||
        s_rdata[p*128+:128]!==masked_pattern(tag,b))
        $fatal(1,"Read mismatch p=%d beat=%d got=%h expected=%h",p,b,s_rdata[p*128+:128],masked_pattern(tag,b));
     checks=checks+1;
     @(negedge clk);s_rready[p]=0;
   end
   read_transactions=read_transactions+1;
 end
endtask
integer word_index=0,active_frame=0,frame_w=0,frame_b=0;
integer images_ok=0,images_error=0,t0,t1,t2,ctrl_calls=0;
reg active=0,consumed=0,fence_seen=0;
reg [31:0] random_bits=32'h613acb27;
function [127:0] image_pattern(input integer frame,input integer word_index);
 integer b;begin for(b=0;b<16;b=b+1) image_pattern[b*8+:8]=(word_index*16+b)*17+frame;end
endfunction
function [31:0] checksum(input integer frame);
 reg [31:0] value;integer n;
 begin value=32'd2166136261;
   for(n=0;n<9216;n=n+1) value=(value^((n*17+frame)&255))*32'd16777619;
   checksum=value;
 end
endfunction
// Producer lives entirely in the unrelated video clock domain. FIFO may fill.
always @(posedge vclk or negedge rst_n) begin
 if(!rst_n) begin active<=0;word_index<=0;active_frame<=0;consumed<=0;end
 else begin
   consumed<=image_valid && image_ready;
   if(grant_valid && grant_ready) begin active<=1;word_index<=0;active_frame<=grant_frame_id;end
   if(image_valid && image_ready) begin
     word_index<=word_index+1;if(word_index==575) active<=0;
   end
 end
end
always @(negedge vclk or negedge rst_n) begin
 if(!rst_n) begin image_valid=0;image_words=0;end
 else begin
   random_bits={random_bits[30:0],random_bits[31]^random_bits[21]^random_bits[1]^random_bits[0]};
   if(consumed) image_valid=0;
   if(!image_valid && active && random_bits[0]) begin
     image_valid=1;image_words=image_pattern(active_frame,word_index);
   end
 end
end
always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin frame_w<=0;frame_b<=0;fence_seen<=0;end
 else begin
   if(frame_valid && frame_ready) fence_seen<=0;
   if(image_start_valid && image_start_ready) begin frame_w<=0;frame_b<=0;end
   if(dut.core.hub.f_wvalid[3] && dut.core.hub.f_wready[3]) frame_w<=frame_w+1;
   if(dut.core.hub.f_bvalid[3] && dut.core.hub.f_bready[3]) frame_b<=frame_b+1;
   if(image_done_valid && image_done_ready && !image_error) begin
     if(frame_w!=576 || frame_b!=36) $fatal(1,"Writer completion before all 576 beats/36 responses");
     fence_seen<=1;
   end
   if(dut.core.publisher.choose_internal && dut.core.publisher.manager_ready && dut.core.publisher.internal_cmd==1 && !fence_seen)
     $fatal(1,"COMMIT before final write response");
 end
end
reg stalled=0;reg [127:0] stalled_word;
integer source_stalls=0;
always @(posedge vclk or negedge rst_n) if(rst_n) begin
 if(stalled && (!image_valid || image_words!==stalled_word)) $fatal(1,"Video word changed under backpressure");
 stalled<=image_valid && !image_ready;stalled_word<=image_words;
 if(image_valid && !image_ready) source_stalls=source_stalls+1;
end else stalled<=0;
task send_frame(input integer seq,input bit bad_descriptor);
 reg [511:0] f;
 begin
   f=0;f[31:0]=32'h10000;f[63:32]=seq;f[95:64]=seq*33;f[319:288]=1;
   if(bad_descriptor) f[511:480]=1;
   @(negedge vclk);req_payload={32'b0,f};req_valid=1;
   do @(posedge vclk);while(!req_ready);
   @(negedge vclk);req_valid=0;
 end
endtask
task collect(input integer seq,input [2:0] expected,
             output reg id,output reg [31:0] gen);
 reg [547:0] saved;reg [31:0] addr;
 reg [7:0] observed;integer n;
 begin
   event_ready=0;
   while(!delivered_valid) @(negedge vclk);
   saved=delivered;
   repeat(7) begin @(negedge vclk);
     if(!delivered_valid || delivered!==saved) $fatal(1,"Event payload not held");
   end
   if(delivered[547:545]!==expected || delivered[63:32]!=seq)
      $fatal(1,"Image event seq=%d got_frame=%h status=%d expected=%d payload=%h",seq,delivered[63:32],delivered[547:545],expected,delivered);
   id=delivered[544];gen=delivered[543:512];
   if(expected==0) begin
     addr=delivered[159:128];
     for(n=0;n<9216;n=n+1) begin
       observed=memory_model.memory[(addr+n)/16][((addr+n)%16)*8+:8];
       if(observed!==((n*17+seq)&255)) $fatal(1,"Image byte corrupted frame=%d offset=%d got=%h expected=%h",seq,n,observed,((n*17+seq)&255));
     end
     if(delivered[287:256]!==checksum(seq)) $fatal(1,"Image FNV mismatch got=%h expected=%h",delivered[287:256],checksum(seq));
     images_ok=images_ok+1;
   end else images_error=images_error+1;
   event_ready=1;@(negedge vclk);event_ready=0;
 end
endtask
reg [31:0] apb_value;
task apb(input bit wr,input [15:0] address,input [31:0] data);
 begin
  @(negedge pclk);paddr=address;pwdata=data;pwrite=wr;psel=1;penable=0;
  @(negedge pclk);penable=1;
  do @(posedge pclk);while(!pready);
  if(pslverror) $fatal(1,"Unexpected integration APB error");
  apb_value=prdata;
  @(negedge pclk);psel=0;penable=0;pwrite=0;
 end
endtask
task control(input [2:0] op,input bit id,input [31:0] gen,input [1:0] expected);
 begin
  // Unsupported opcode is now rejected by APB before reaching the owner.
  if(op!=0) begin
   apb(1,16'h10,gen);apb(1,16'h0c,{23'b0,id,5'b0,op});
   apb(0,8,0);while(apb_value!=2) apb(0,8,0);
   apb(0,16'h18,0);
   if(apb_value[1:0]!==expected || apb_value[8]!==id) $fatal(1,"APB control status/slot");
   if(op==5) begin
    apb(0,16'h1c,0);if(apb_value!==gen) $fatal(1,"APB QUERY generation");
    apb(0,16'h4c,0);if(apb_value!=={31'b0,id}) $fatal(1,"APB descriptor slot");
   end
   apb(1,16'h14,1);ctrl_calls=ctrl_calls+1;
  end
 end
endtask
task read_image(input integer seq,input integer addr);
 integer burst,b,n;reg [127:0] expected;
 begin
   for(burst=0;burst<36;burst=burst+1) begin
     @(negedge clk);s_arvalid[0]=1;s_araddr[31:0]=addr+burst*256;s_arlen[7:0]=15;
     do @(posedge clk);while(!s_arready[0]);
     @(negedge clk);s_arvalid[0]=0;
     for(b=0;b<16;b=b+1) begin
       repeat(b%3) @(negedge clk);s_rready[0]=1;
       do @(posedge clk);while(!s_rvalid[0]);
       expected=image_pattern(seq,burst*16+b);
       if(s_rdata[127:0]!==expected || s_rresp[1:0]!=0 || s_rlast[0]!=(b==15))
         $fatal(1,"CPU shared-image read mismatch");
       checks=checks+1;
       @(negedge clk);s_rready[0]=0;
     end
   end
 end
endtask
reg a,b,tmp;reg [31:0] ga,gb,old_ga,tmpgen;
initial begin
 // Explicit assertion edge and clocks present during reset, including the
 // intentionally slow video-domain case. Do not rely on time-zero X->0 events.
 #1;rst_n=0;#(VIDEO_HALF*4+23);rst_n=1;
 fork
   begin for(t0=0;t0<30;t0=t0+1) begin write_burst(0,32'h10000+t0*256,4,t0,0);read_burst(0,32'h10000+t0*256,4,t0,0);end end
   begin for(t1=0;t1<30;t1=t1+1) begin write_burst(1,32'h18000+t1*256,4,100+t1,0);read_burst(1,32'h18000+t1*256,4,100+t1,0);end end
   begin for(t2=0;t2<30;t2=t2+1) begin write_burst(2,t2*256,4,200+t2,0);read_burst(2,t2*256,4,200+t2,0);end end
   begin
     send_frame(1,0);collect(1,0,a,ga);old_ga=ga;
     send_frame(2,0);collect(2,0,b,gb);
     if(a==b || states!==4'b1010) $fatal(1,"Two images did not occupy separate READY slots");
     send_frame(3,0);collect(3,1,tmp,tmpgen);
   end
 join
 control(5,a,ga,0);control(0,a,ga,3);
 control(3,a,ga+1,2);control(3,a,ga,0);
 send_frame(4,0);collect(4,1,tmp,tmpgen);
 read_image(1,a?32'h4000:32'h1000);
 control(4,a,ga+1,2);control(4,a,ga,0);
 send_frame(5,0);collect(5,0,a,ga);
 if(ga==old_ga) $fatal(1,"Slot generation did not advance");
 control(3,a,old_ga,2);
 control(3,b,gb,0);control(4,b,gb,0);
 inject_b_error=1;send_frame(6,0);collect(6,4,tmp,tmpgen);inject_b_error=0;
 if(states[3:2]!=0) $fatal(1,"Failed write leaked WRITING/READY slot");
 // Recover from a failed first burst without reset: every pixel must be fresh.
 send_frame(10,0);collect(10,0,tmp,tmpgen);control(3,tmp,tmpgen,0);control(4,tmp,tmpgen,0);
 send_frame(7,1);collect(7,3,tmp,tmpgen);
 if(states[3:2]!=0) $fatal(1,"Rejected descriptor leaked slot");
 send_frame(8,0);
 wait(active && word_index>100);
 @(negedge clk);rst_n=0;
 repeat(4) @(negedge clk);rst_n=1;
 repeat(12) @(negedge vclk);
 if(delivered_valid || states!=0) $fatal(1,"Ghost state/event after shared reset");
 send_frame(9,0);collect(9,0,tmp,tmpgen);
 if(VIDEO_HALF<MEM_HALF*16 && source_stalls==0) $fatal(1,"FIFO backpressure was not exercised");
 if(core_protocol_error || cpu_adapter_error || cpu_rejected) $fatal(1,"Adapter protocol error");
 if(protocol_error) $fatal(1,"Unexpected fabric protocol error");
 $display("PASS tb_c2_vendor bytes=9216 success=%0d rejected=%0d cpu_controls=%0d background_writes=%0d background_reads=%0d checks=%0d source_stalls=%0d final_B_fence FNV CPU_readback APB CPU_ID vendor_S1 video_relocation async_pixel_FIFO grant error_drain CDC busy_drop errors reset",images_ok,images_error,ctrl_calls,write_transactions,read_transactions,checks,source_stalls);
 $finish;
end
initial begin #10000000;$fatal(1,"Image hub timeout");end
endmodule

