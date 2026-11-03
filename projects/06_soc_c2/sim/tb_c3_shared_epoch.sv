`timescale 1ns/1ps
// Same APB decoder/clock connections as native, with accelerated C2 ticks.
module tb_c3_shared_epoch;
reg pclk=0,mclk=0,vclk=0,rst_n=1;
always #5 pclk=~pclk;always #7 mclk=~mclk;always #11 vclk=~vclk;
reg [15:0] addr=0;reg sel=0,pen=0,wr=0;reg [31:0] wd=0;
wire page=addr[15:8]==8'h10;
wire [31:0] r2,r3,ms,video_ms;wire ok2,ok3,e2,e3,valid,video_valid,buzzer,led;
wire [31:0] rd=page?r3:r2;wire ready=page?ok3:ok2;wire error=page?e3:e2;
integer checks=0;reg [31:0] value,start;
c2_apb_control #(.TIME_CLOCK_HZ(100000),.TIME_INITIAL_MS(32'hfffffffe)) c2(
.arst_n(rst_n),.pclk(pclk),.mem_clk(mclk),.video_clk(vclk),.map_enable(1'b0),
.shared_video_ms(video_ms),.shared_video_valid(video_valid),.shared_cpu_ms(ms),.shared_cpu_valid(valid),
.paddr(addr),.psel(sel&&!page),.penable(pen),.pwrite(wr),.pwdata(wd),.pready(ok2),.prdata(r2),.pslverror(e2),.irq(),
.cpu_valid(),.cpu_ready(1'b1),.cpu_cmd(),.cpu_slot(),.cpu_generation(),
.cpu_rsp_valid(1'b0),.cpu_rsp_ready(),.cpu_rsp_status(2'b0),.cpu_rsp_slot(1'b0),
.cpu_rsp_generation(32'b0),.cpu_descriptor(512'b0),.slot_states(4'b0),.dropped(32'b0),.protocol_error(1'b0));
c3_apb_peripheral c3(.arst_n(rst_n),.pclk(pclk),.io_enable(1'b1),.shared_ms(ms),.shared_valid(valid),
.scl_i(1'b1),.sda_i(1'b1),.scl_drive_low(),.sda_drive_low(),.buzzer(buzzer),.alarm_led(led),
.paddr(addr[7:0]),.psel(sel&&page),.penable(pen),.pwrite(wr),.pwdata(wd),.pready(ok3),.prdata(r3),.pslverror(e3));
task apb(input bit w,input [15:0] a,input [31:0] d);
 begin
  @(negedge pclk);addr=a;wd=d;wr=w;sel=1;pen=0;
  @(negedge pclk);pen=1;@(posedge pclk);if(!ready || error) $fatal(1,"Epoch APB");value=rd;
  if(!w && a==16'h84 && value!==ms) $fatal(1,"C2 APB time differs from C3 wire");
  checks=checks+1;@(negedge pclk);sel=0;pen=0;wr=0;
 end
endtask
initial begin
 #1;rst_n=0;#53;rst_n=1;wait(valid);repeat(3) @(negedge pclk);
 apb(0,0,0);if(value!=32'h43325332) $fatal(1,"C2 page lost");
 apb(0,16'h1000,0);if(value!=32'h43335031) $fatal(1,"C3 page lost");
 apb(0,16'h84,0);apb(1,16'h102c,3);apb(1,16'h1024,32'h43474131);apb(1,16'h1020,3);
 start=c3.gpio_started;if(start!=32'hfffffffe || !buzzer) $fatal(1,"Shared epoch GPIO start");
 wait(ms==0);repeat(3) @(negedge pclk);if(!buzzer) $fatal(1,"Early expiry across counter wrap");
 apb(0,16'h84,0);wait(ms==1);repeat(3) @(negedge pclk);
 if(buzzer || led || c3.armed) $fatal(1,"GPIO did not use the same wrapping C2 clock");
 apb(1,16'h1024,32'h43474131);apb(1,16'h1020,2);
 rst_n=0;#31;if(buzzer || led || valid) $fatal(1,"Common epoch reset");
 rst_n=1;wait(valid);repeat(3) @(negedge pclk);apb(0,16'h84,0);
 if(value!=32'hfffffffe || c3.armed) $fatal(1,"Old epoch leaked after reset");
 $display("PASS tb_c3_shared_epoch checks=%0d C2_C3_same_counter APB_page_decode wrap_GPIO_expiry common_reset no_CLINT",checks);$finish;
end
initial begin #20000000;$fatal(1,"Epoch timeout");end
endmodule
