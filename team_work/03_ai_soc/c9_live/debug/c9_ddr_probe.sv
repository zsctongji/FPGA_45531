`timescale 1ns/1ps
// Diagnostic-only USER2 chain. No output feeds DDR, reset or CPU control.
// Native multi-bit status is best-effort, not an atomic functional CDC.
// Require repeated stable status reads before interpreting a stopped stage.
module c9_ddr_probe(
 input wire tck,tdi,selected,capture,shift,root_reset_n,
 input wire core_clk,system_clk,tx_clk,rx_clk,
 input wire [3:0] locks,debug_high,
 input wire [31:0] status0,status1,status2,
 output wire tdo
);
 // Period seven avoids aliasing at the nominal integer clock ratios.
 reg [2:0] core_phase=3'b001,system_phase=3'b001;
 reg [2:0] tx_phase=3'b001,rx_phase=3'b001;
 always @(posedge core_clk or negedge root_reset_n)
  if(!root_reset_n)core_phase<=3'b001;
  else core_phase<={core_phase[1:0],core_phase[2]^core_phase[1]};
 always @(posedge system_clk or negedge root_reset_n)
  if(!root_reset_n)system_phase<=3'b001;
  else system_phase<={system_phase[1:0],system_phase[2]^system_phase[1]};
 always @(posedge tx_clk or negedge root_reset_n)
  if(!root_reset_n)tx_phase<=3'b001;
  else tx_phase<={tx_phase[1:0],tx_phase[2]^tx_phase[1]};
 always @(posedge rx_clk or negedge root_reset_n)
  if(!root_reset_n)rx_phase<=3'b001;
  else rx_phase<={rx_phase[1:0],rx_phase[2]^rx_phase[1]};
 (* async_reg="true" *) reg [3:0] phase1=0,phase2=0;
 reg [1:0] bank=0;
 reg [35:0] packet=0;
 wire [31:0] status3={16'hc9d2,3'b0,root_reset_n,locks,phase2,debug_high};
 wire [31:0] payload=bank==0?status0:bank==1?status1:bank==2?status2:status3;
 assign tdo=packet[0];
 always @(posedge tck)begin
  phase1<={rx_phase[2],tx_phase[2],system_phase[2],core_phase[2]};
  phase2<=phase1;
  if(selected && capture)begin packet<={2'b0,bank,payload};bank<=bank+1'b1;end
  // Keep required hard-TAP TDI alive. It only fills the consumed shift
  // register; it cannot change a bank, functional control or captured data.
  else if(selected && shift)packet<={tdi,packet[35:1]};
 end
endmodule
