`timescale 1ns/1ps
module tb_c9_ddr_probe;
 reg tck=0,selected=0,capture=0,shift=0,root=0;
 reg core_clk=0,sys_clk=0,tx_clk=0,rx_clk=0;
 reg run_core=1,run_sys=1,run_tx=1,run_rx=1;
 always #5 if(run_core)core_clk=~core_clk;
 always #6.5 if(run_sys)sys_clk=~sys_clk;
 always #1.25 if(run_tx)tx_clk=~tx_clk;
 always #1.5 if(run_rx)rx_clk=~rx_clk;
 wire tdo;
 c9_ddr_probe dut(.tck(tck),.tdi(1'b1),.selected(selected),.capture(capture),.shift(shift),.root_reset_n(root),
 .core_clk(core_clk),.system_clk(sys_clk),.tx_clk(tx_clk),.rx_clk(rx_clk),
 .locks(4'hf),.debug_high(4'h5),.status0(32'h12345678),.status1(32'h89abcdef),.status2(32'hdeadcafe),.tdo(tdo));
 task tick;begin #41;tck=1;#41;tck=0;end endtask
 task read_packet(output reg[35:0] value);
  integer bitno;
  begin
   selected=1;capture=1;tick();capture=0;shift=1;
   for(bitno=0;bitno<36;bitno=bitno+1)begin value[bitno]=tdo;tick();end
   shift=0;selected=0;
  end
 endtask
 reg [35:0] value;reg [3:0] observed0=0,observed1=0;integer n;
 initial begin
  // The chain remains usable while the whole application is held in reset.
  read_packet(value);if(value!==36'h012345678)$fatal(1,"reset bank0 %h",value);
  read_packet(value);if(value!==36'h189abcdef)$fatal(1,"reset bank1 %h",value);
  read_packet(value);if(value!==36'h2deadcafe)$fatal(1,"reset bank2 %h",value);
  read_packet(value);if(value[35:32]!=3||value[31:16]!=16'hc9d2||value[12]!=0||value[3:0]!=5)$fatal(1,"signature %h",value);
  root=1;
  // Reading USER1/another TAP must not advance the USER2 bank.
  capture=1;selected=0;tick();capture=0;
  read_packet(value);if(value[35:32]!=0)$fatal(1,"unselected capture advanced bank");
  for(n=0;n<63;n=n+1)begin
   read_packet(value);
   if(value[35:32]==3)begin observed0=observed0|~value[7:4];observed1=observed1|value[7:4];end
  end
  if((observed0&observed1)!=15)$fatal(1,"running clocks not visible %h %h",observed0,observed1);
  run_core=0;run_sys=0;run_tx=0;run_rx=0;
  repeat(3)tick();observed0=0;observed1=0;
  for(n=0;n<32;n=n+1)begin
   read_packet(value);
   if(value[35:32]==3)begin observed0=observed0|~value[7:4];observed1=observed1|value[7:4];end
  end
  if((observed0&observed1)!=0)$fatal(1,"stopped clocks falsely active");
  $display("PASS USER2 banks, CPU-reset independence, TAP isolation, running/stopped clock observation");$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
