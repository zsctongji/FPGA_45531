`timescale 1ns/1ps
module tb_c2_a_errors;
 reg clk=0,rst=0,ready=0,active=0,rv=0,re=0;
 reg [7:0] data=0;reg [31:0] frame=0,stamp=0,sum32=0;
 wire take,release_frame,req;wire [15:0] address;
 wire fv,fr,gv,gr,wv,wr,sv,sr,se,ev,er;
 wire [511:0] desc;wire [127:0] word_data;wire [31:0] sid,sh;
 wire [31:0] completed,rejected,faults;wire [2:0] status;
 reg [31:0] random_bits=32'ha2c41935;
 integer mode=0,target=0,delay_count=0,words=0,leases=0,releases=0,reads=0;
 reg [31:0] hash=0;reg stalled=0;reg [127:0] held;
 always #5 clk=~clk;
 function [7:0] pixel(input integer n);begin pixel=(n<2016 || n>=7200)?0:((n-2016)*17+mode+1);end endfunction
 function [31:0] expected_sum;
 integer n;reg [31:0] v;begin v=0;for(n=0;n<9216;n=n+1)v=v+pixel(n);expected_sum=v;end
 endfunction
 assign fr=target==0;assign gv=target==1 && delay_count==0;
 assign wr=target==2 && random_bits[0] && random_bits[2];
 assign sr=target==2 && words==576 && delay_count>=10;
 assign ev=target==3;
 assign status=mode==6?1:(mode==0?0:4);
 wire [511:0] event_desc={448'b0,frame,32'h10000};
 c2_a_mailbox_bridge #(.READ_TIMEOUT(8)) dut(.clk(clk),.rst_n(rst),.enable(1'b1),
 .a_ready(ready),.a_active(active),.a_frame_id(frame),.a_timestamp_ms(stamp),.a_sum32(sum32),
 .a_take(take),.a_release(release_frame),.a_read_req(req),.a_read_address(address),
 .a_read_valid(rv),.a_read_error(re),.a_read_data(data),
 .v_frame_valid(fv),.v_frame_ready(fr),.v_descriptor(desc),
 .v_grant_valid(gv),.v_grant_ready(gr),.v_grant_frame_id(mode==5?frame+1:frame),
 .v_word_valid(wv),.v_word_ready(wr),.v_word_data(word_data),
 .v_source_valid(sv),.v_source_ready(sr),.v_source_error(se),.v_source_frame_id(sid),.v_source_fnv(sh),
 .v_event_valid(ev),.v_event_ready(er),.v_event_status(status),.v_event_descriptor(event_desc),
 .completed(completed),.rejected(rejected),.source_faults(faults),
 .last_frame_id(),.last_sum32(),.last_fnv(),.last_status());
 always @(posedge clk) if(rst) begin
  if(take) begin active<=1;ready<=0;leases=leases+1;end
  if(release_frame) begin active<=0;releases=releases+1;end
  rv<=req && !(mode==2 && address==5);re<=req && mode==1 && address==5;
  data<=(mode==3 && address==1)?8'd90:pixel(address);
  if(req) reads=reads+1;
  random_bits<={random_bits[30:0],random_bits[31]^random_bits[21]^random_bits[1]^random_bits[0]};
  if(stalled && (!wv || word_data!==held)) $fatal(1,"Packed word changed under stall");
  stalled<=wv && !wr;held<=word_data;
  case(target)
   0: if(fv && fr) begin target<=mode==6?3:1;delay_count<=8;words=0;hash=32'd2166136261;end
   1: if(delay_count>0) delay_count<=delay_count-1;else if(gv && gr) target<=2;
   2: begin
    if(wv && wr) begin
      for(integer b=0;b<16;b=b+1) hash=(hash^{24'b0,word_data[b*8+:8]})*32'd16777619;
      words=words+1;
    end
    if(words==576) delay_count<=delay_count+1;
    if(sv && sr) begin
      if(words!=576 || sid!=frame || sh!==hash || se!==(mode!=0)) $fatal(1,"Source verdict mismatch mode=%0d",mode);
      target<=3;
    end
   end
   3: if(ev && er) target<=0;
  endcase
 end else begin rv<=0;re<=0;stalled<=0;end
 initial begin
 #23;rst=1;
 for(mode=0;mode<7;mode=mode+1) begin
  @(negedge clk);frame=mode+1;stamp=100;sum32=expected_sum()+(mode==4?1:0);ready=1;
  wait(releases==mode+1);repeat(4) @(negedge clk);
  if(active) $fatal(1,"A lease leaked");
 end
 if(completed!=1 || rejected!=6 || faults!=5 || leases!=7) $fatal(1,"Fault/release counts wrong");
 $display("PASS tb_c2_a_errors modes=7 read_error timeout bad_padding bad_sum wrong_grant busy drain576 stable_word release");$finish;
 end
 initial begin #5000000;$fatal(1,"A bridge fault test timeout");end
endmodule
