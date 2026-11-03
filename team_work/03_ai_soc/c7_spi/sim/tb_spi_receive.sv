`timescale 1ns/1ps
module tb_spi_receive;
 reg clk=0,reset=1,valid=0,kind=0,rd=0,wr=0;reg[7:0]data=0;
 wire ready,rvalid,sclk,ss,mosi;wire[7:0]reply;
 reg miso=1;reg[7:0]rx=0;integer bits=0,outbit=0,count=0;reg[23:0]got=0;
 parameter FIXED=0,DIVIDER=8;
 always #5 clk=~clk;
 TopLevel_ba6762f3781649428952cf46a6343376 dut(
 .io_config_kind_cpol(1'b0),.io_config_kind_cpha(1'b0),.io_config_sclkToggle(12'(DIVIDER)),.io_config_mod(2'd0),
 .io_config_ss_activeHigh(1'b0),.io_config_ss_setup(12'd8),.io_config_ss_hold(12'd8),.io_config_ss_disable(12'd8),
 .io_cmd_valid(valid),.io_cmd_ready(ready),.io_cmd_payload_kind(kind),.io_cmd_payload_read(rd),.io_cmd_payload_write(wr),.io_cmd_payload_data(data),
 .io_rsp_valid(rvalid),.io_rsp_payload_data(reply),.io_spi_sclk_write(sclk),.io_spi_ss(ss),
 .io_spi_data_0_write(mosi),.io_spi_data_0_read(1'b0),.io_spi_data_1_read(miso),.io_spi_data_2_read(1'b1),.io_spi_data_3_read(1'b1),
 .io_peripheralClk(clk),.peripheralCd_logic_outputReset(reset));
 always @(posedge ss)begin bits=0;outbit=0;miso=1;end
 always @(posedge sclk)if(!ss)begin rx={rx[6:0],mosi};bits=bits+1;if(bits==8 && rx!=8'h9f)$fatal(1,"bad command %h",rx);end
 always @(negedge sclk)if(!ss && bits>=8)begin
  if(outbit<24)begin #1;miso=(24'hef6017>>(23-outbit))&1;outbit=outbit+1;end
  else begin #1;miso=0;end
 end
 always @(posedge clk)if(rvalid)begin got={got[15:0],reply};count=count+1;end
 task send(input k,input r,input w,input[7:0]b);
 begin @(negedge clk);kind=k;rd=r;wr=w;data=b;valid=1;@(posedge clk);while(!ready)@(posedge clk);@(negedge clk);valid=0;repeat(8)@(posedge clk);end endtask
 initial begin repeat(8)@(posedge clk);@(negedge clk);reset=0;repeat(8)@(posedge clk);
  send(1,0,0,8'h80);send(0,0,1,8'h9f);repeat(3)send(0,1,0,0);repeat(10)@(posedge clk);send(1,0,0,0);
  if(count!=3)$fatal(1,"missing replies %0d",count);
  if(FIXED && got!=24'hef6017)$fatal(1,"fixed receive %h",got);
  if(!FIXED && got!=24'hdec02e)$fatal(1,"raw negative changed %h",got);
  $display("PASS spi_read fixed=%0d jedec=%h expected=%h",FIXED,got,FIXED?24'hef6017:24'hdec02e);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
