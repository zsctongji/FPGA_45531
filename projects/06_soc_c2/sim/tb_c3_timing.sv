`timescale 1ns/1ps
// Ideal-pad digital timing, not an electrical rise/fall-time signoff.
module tb_c3_timing #(parameter integer RATE=400000);
reg clk=0,rst_n=1,slave_sda=0;always #5 clk=~clk;
tri1 scl,sda;wire sl,sd;
assign scl=sl?1'b0:1'bz;assign sda=sd||slave_sda?1'b0:1'bz;
reg [7:0] addr=0;reg sel=0,pen=0,wr=0;reg [31:0] wd=0;wire [31:0] rd;wire error,ready;
reg [31:0] value;integer bits=0,checks=0,starts=0,stops=0;
time rise_at=0,fall_at=0,start_at=0,stop_at=0;
localparam integer LOW_NS=RATE<=100000?4700:(RATE<=400000?1300:500);
localparam integer HIGH_NS=RATE<=100000?4000:(RATE<=400000?600:260);
localparam integer START_NS=RATE<=100000?4700:(RATE<=400000?600:260);
localparam integer HOLD_NS=RATE<=100000?4000:(RATE<=400000?600:260);
localparam integer BUF_NS=RATE<=100000?4700:(RATE<=400000?1300:500);
c3_apb_peripheral dut(.arst_n(rst_n),.pclk(clk),.io_enable(1'b1),.shared_ms(32'd1),.shared_valid(1'b1),
.scl_i(scl),.sda_i(sda),.scl_drive_low(sl),.sda_drive_low(sd),.buzzer(),.alarm_led(),
.paddr(addr),.psel(sel),.penable(pen),.pwrite(wr),.pwdata(wd),.pready(ready),.prdata(rd),.pslverror(error));
always @(posedge scl) if(rst_n) begin
 if(fall_at && $time-fall_at<LOW_NS) $fatal(1,"tLOW rate=%0d got=%0t",RATE,$time-fall_at);
 if(rise_at && $time-rise_at<1000000000/RATE) $fatal(1,"SCL too fast");
 rise_at=$time;checks=checks+1;
end
always @(negedge scl) if(rst_n) begin
 if(rise_at && $time-rise_at<HIGH_NS) $fatal(1,"tHIGH");
 if(start_at && $time-start_at<HOLD_NS) $fatal(1,"tHD_STA");
 fall_at=$time;bits=bits+1;
 if(bits==9) slave_sda=1;
 if(bits==10) begin slave_sda=0;bits=1;end
 checks=checks+1;
end
always @(negedge sda) if(rst_n && scl===1'b1) begin
 if(rise_at && $time-rise_at<START_NS) $fatal(1,"tSU_STA");
 if(stop_at && $time-stop_at<BUF_NS) $fatal(1,"tBUF");
 start_at=$time;starts=starts+1;bits=0;
end
always @(posedge sda) if(rst_n && scl===1'b1) begin
 if(rise_at && $time-rise_at<HIGH_NS) $fatal(1,"tSU_STO");
 stop_at=$time;stops=stops+1;
end
task apb(input bit w,input [7:0] a,input [31:0] d);
 begin
  @(negedge clk);addr=a;wd=d;wr=w;sel=1;pen=0;
  @(negedge clk);pen=1;@(posedge clk);if(error || !ready) $fatal(1,"Timing APB");value=rd;
  @(negedge clk);sel=0;pen=0;wr=0;
 end
endtask
task cmd(input integer c);
 begin
  apb(1,12,32'(c));apb(0,8,0);while(value[0]) apb(0,8,0);
  if((value&32'h3e)!=2) $fatal(1,"Timing I2C transaction status %h",value);
 end
endtask
initial begin
 #1;rst_n=0;#51;rst_n=1;repeat(10) @(negedge clk);
 apb(1,24,32'((100000000+RATE*5-1)/(RATE*5)));apb(1,28,1000000);
 apb(1,16,32'h66);cmd(9);apb(1,16,32'h66);cmd(9);cmd(2);
 apb(1,16,32'h66);cmd(9);cmd(2);
 if(starts!=3 || stops!=2 || checks<50) $fatal(1,"Timing coverage");
 $display("PASS tb_c3_timing rate=%0d checks=%0d tLOW tHIGH tHD_STA tSU_STA tSU_STO tBUF period ideal_pad_only",RATE,checks);$finish;
end
initial begin #10000000;$fatal(1,"Timing timeout");end
endmodule
