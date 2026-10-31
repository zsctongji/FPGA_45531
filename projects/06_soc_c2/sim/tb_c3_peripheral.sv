`timescale 1ns/1ps
module tb_c3_peripheral;
reg clk=0,rst_n=1,enable=0,time_valid=1;always #5 clk=~clk;
reg [31:0] ms=0;reg slave_sda=0,slave_scl=0;
wire scl_low,sda_low,buzzer,led;
tri1 scl,sda;
assign scl=scl_low||slave_scl?1'b0:1'bz;
assign sda=sda_low||slave_sda?1'b0:1'bz;
reg [7:0] addr=0;reg sel=0,pen=0,wr=0;reg [31:0] wd=0;
wire ready,error;wire [31:0] rd;
reg [31:0] value,status;integer checks=0,starts=0,stops=0;reg [7:0] byte_value;
c3_apb_peripheral dut(.arst_n(rst_n),.pclk(clk),.io_enable(enable),.shared_ms(ms),.shared_valid(time_valid),
.scl_i(scl),.sda_i(sda),.scl_drive_low(scl_low),.sda_drive_low(sda_low),.buzzer(buzzer),.alarm_led(led),
.paddr(addr),.psel(sel),.penable(pen),.pwrite(wr),.pwdata(wd),.pready(ready),.prdata(rd),.pslverror(error));
always @(negedge sda) if(rst_n && scl===1'b1) starts=starts+1;
always @(posedge sda) if(rst_n && scl===1'b1) stops=stops+1;
task apb(input bit write_en,input [7:0] a,input [31:0] d,input bit expected_error);
 begin
  @(negedge clk);addr=a;wd=d;wr=write_en;sel=1;pen=0;
  @(negedge clk);pen=1;@(posedge clk);
  if(!ready || error!==expected_error) $fatal(1,"APB addr=%h ready=%b error=%b expected=%b",a,ready,error,expected_error);
  value=rd;checks=checks+1;
  @(negedge clk);sel=0;pen=0;wr=0;
 end
endtask
task command(input [31:0] c,input [31:0] expected_errors);
 integer n;
 begin
  apb(1,8'h0c,c,0);n=0;
  apb(0,8'h08,0,0);
  while(value[0] && n<30000) begin apb(0,8'h08,0,0);n=n+1;end
  status=value;
  if(n==30000 || !status[1] || (status&32'h3c)!==expected_errors)
   $fatal(1,"I2C cmd=%0d status=%h expected_errors=%h",c,status,expected_errors);
 end
endtask
task write_byte(input [7:0] data,input bit start);
 begin apb(1,8'h10,{24'b0,data},0);command(start?9:8,0);end
endtask
task start_seen;
 begin:wait_start
  forever begin @(negedge sda);if(scl===1'b1) disable wait_start;end
 end
endtask
task stop_seen;
 begin:wait_stop
  forever begin @(posedge sda);if(scl===1'b1) disable wait_stop;end
 end
endtask
task slave_receive(input [7:0] expected,input bit ack);
 integer i;reg [7:0] got;
 begin
  for(i=7;i>=0;i=i-1) begin @(posedge scl);#1;got[i]=sda;end
  if(got!==expected) $fatal(1,"Slave got=%h expected=%h",got,expected);
  @(negedge scl);slave_sda=ack;
  @(posedge scl);@(negedge scl);slave_sda=0;
 end
endtask
task slave_send(input [7:0] data,input bit expected_nack);
 integer i;
 begin
  for(i=7;i>=0;i=i-1) begin slave_sda=!data[i];@(posedge scl);@(negedge scl);end
  slave_sda=0;@(posedge scl);#1;
  if(sda!==expected_nack) $fatal(1,"Master ACK/NACK incorrect");
  @(negedge scl);
 end
endtask
initial begin
 #1;rst_n=0;#51;rst_n=1;repeat(5) @(negedge clk);
 if(scl_low || sda_low || buzzer || led) $fatal(1,"Unsafe reset pads");
 apb(1,8'h0c,9,1);apb(1,8'h24,32'h43474131,1);apb(1,8'h01,0,1);
 apb(0,0,0,0);if(value!=32'h43335031) $fatal(1,"C3 identity");
 enable=1;repeat(5) @(negedge clk);apb(1,8'h18,34,0);apb(1,8'h1c,10000,0);
 apb(1,8'h0c,8,1);apb(1,8'h0c,12,1);
 fork
  begin
   start_seen();slave_receive(8'h66,1);slave_receive(8'h00,1);slave_receive(8'h80,1);
   start_seen();slave_receive(8'h67,1);slave_send(8'h12,0);slave_send(8'h34,1);stop_seen();
  end
  begin
   write_byte(8'h66,1);write_byte(8'h00,0);write_byte(8'h80,0);write_byte(8'h67,1);
   command(4,0);apb(0,8'h14,0,0);if(value!=8'h12) $fatal(1,"RX first byte");
   command(20,0);apb(0,8'h14,0,0);if(value!=8'h34) $fatal(1,"RX final byte");command(2,0);
  end
  begin @(negedge scl);slave_scl=1;repeat(500) @(negedge clk);slave_scl=0;end
 join
 if(starts!=2 || stops!=1 || scl_low || sda_low) $fatal(1,"Combined transaction/repeated START/STOP");
 fork
  begin start_seen();slave_receive(8'h90,0);stop_seen();end
  begin apb(1,8'h10,32'h90,0);command(9,4);end
 join
 // Ignore short input spikes; do not misreport a driven-one arbitration loss.
 apb(1,8'h10,255,0);apb(1,8'h0c,9,0);wait(dut.state==6);
 slave_sda=1;#50;slave_sda=0;
 apb(0,8'h08,0,0);while(value[0]) apb(0,8'h08,0,0);
 if(value[4] || !value[2]) $fatal(1,"50ns spike escaped input filter");
 // Arbitration loss on a transmitted one; release without generating STOP.
 apb(1,8'h10,255,0);apb(1,8'h0c,9,0);
 wait(dut.state==6);slave_sda=1;wait(!dut.busy);slave_sda=0;
 apb(0,8'h08,0,0);if(!value[4] || scl_low || sda_low) $fatal(1,"Arbitration release");
 // Explicit 9-pulse recovery, then STOP. No automatic blind replay.
 slave_sda=1;
 fork
  begin repeat(9) @(posedge scl);@(negedge scl);slave_sda=0;end
  begin command(32,0);end
 join
 if(scl_low || sda_low || !scl || !sda) $fatal(1,"Recovery did not release bus");
 // Clock-stretch timeout and software abort both release OE, despite a stuck pad.
 slave_scl=1;apb(1,8'h1c,200,0);apb(1,8'h10,8'h66,0);command(9,8);
 if(scl_low || sda_low) $fatal(1,"Stretch timeout release");
 slave_scl=0;repeat(10) @(negedge clk);command(32,8); // too-short deadline cannot finish recovery
 apb(1,8'h1c,10000,0);command(32,0);
 apb(1,8'h10,0,0);apb(1,8'h0c,9,0);apb(1,8'h18,50,1);apb(1,8'h0c,64,0);
 if(dut.busy || scl_low || sda_low) $fatal(1,"Software abort release");
 // Wrap-safe shared-clock GPIO watchdog; repeated ON does not extend lease.
 ms=32'hfffffffe;apb(1,8'h2c,3,0);apb(1,8'h24,32'h43474131,0);apb(1,8'h20,3,0);
 if(!buzzer || !led) $fatal(1,"GPIO arm/write");
 ms=0;apb(1,8'h20,3,0);if(!buzzer) $fatal(1,"Watchdog expired before budget");
 ms=1;repeat(4) @(negedge clk);if(buzzer || led || dut.armed) $fatal(1,"Watchdog wrap/lease");
 apb(1,8'h28,2,0);if(!buzzer) $fatal(1,"Active-low inactive level");
 apb(1,8'h24,32'h43474131,0);apb(1,8'h20,2,0);if(buzzer) $fatal(1,"Active-low active level");
 time_valid=0;repeat(4) @(negedge clk);if(!buzzer || dut.armed) $fatal(1,"Clock fault disarm");
 time_valid=1;apb(1,8'h28,0,0);apb(1,8'h24,32'h43474131,0);apb(1,8'h20,2,0);
 apb(1,8'h0c,9,0);rst_n=0;#31;rst_n=1;repeat(5) @(negedge clk);
 if(buzzer || led || scl_low || sda_low || dut.busy) $fatal(1,"Common reset epoch");
 $display("PASS tb_c3_peripheral checks=%0d repeated_START READ WRITE ACK NACK stretch arbitration timeout abort nine_pulse_recovery GPIO_watchdog shared_time_wrap clock_fault reset open_drain",checks);
 $finish;
end
initial begin #20000000;$fatal(1,"C3 peripheral timeout state=%0d",dut.state);end
endmodule
