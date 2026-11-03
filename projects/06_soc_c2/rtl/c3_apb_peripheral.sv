`timescale 1ns/1ps
// C3 page 0x1000, byte-command I2C master and fail-closed alarm GPIO.
// Pads MUST drive constant zero with OE=drive_low; never drive a high level.
// Single bus owner. Common reset releases pads and disarms both outputs.
module c3_apb_peripheral #(parameter integer CLOCK_HZ=100000000)(
 input wire arst_n,pclk,io_enable,input wire [31:0] shared_ms,input wire shared_valid,
 input wire scl_i,sda_i,output reg scl_drive_low,sda_drive_low,
 output wire buzzer,alarm_led,
 input wire [7:0] paddr,input wire psel,penable,pwrite,input wire [31:0] pwdata,
 output wire pready,output reg [31:0] prdata,output reg pslverror
);
 localparam [4:0] IDLE=0,START_RISE=1,START_WAIT=2,START_PULL=3,START_LOW=4,
  BIT_RISE=5,BIT_SAMPLE=6,BIT_LOW=7,ACK_RISE=8,ACK_SAMPLE=9,ACK_LOW=10,
  STOP_RISE=11,STOP_WAIT=12,STOP_RELEASE=13,STOP_FINISH=14,
  REC_RISE=15,REC_SAMPLE=16,REC_LOW=17,
  BIT_HOLD0=18,BIT_HOLD1=19,ACK_HOLD0=20,ACK_HOLD1=21,REC_HOLD0=22,REC_HOLD1=23,
  START_STABLE=24,START_HOLD_PULL=25,STOP_DELAY0=26,STOP_DELAY1=27,STOP_HOLD0=28,STOP_HOLD1=29,
  START_HOLD0=30,START_HOLD1=31;
 // Three ticks low, two high: >=60% low duty. START/STOP/bus-free
 // holds also cover Standard/Fast/Fast-mode Plus at the requested rate.
 localparam integer MIN_DIV=(CLOCK_HZ+4999999)/5000000;
 reg [4:0] state;
 reg [15:0] divisor,ticks;
 reg [31:0] timeout_cycles,elapsed;
 reg [7:0] tx,rx,shift;
 reg [2:0] bit_index;
 reg [3:0] recovery_pulses;
 reg reading,send_nack,stop_after,owned,busy,done,nack,timed_out,arbitration,stuck;
 reg [1:0] gpio_data,polarity;
 reg armed;reg [31:0] gpio_started,max_on_ms;
 (* async_reg="true" *) reg [1:0] scl_sync,sda_sync;
 localparam integer FILTER_CYCLES=(CLOCK_HZ+19999999)/20000000+2;
 reg scl_filtered,sda_filtered;reg [7:0] scl_filter_count,sda_filter_count;
 reg [1:0] released;
 wire active=io_enable && shared_valid && released[1];
 wire access=psel && penable && pready;
 wire [6:0] cmd=pwdata[6:0];
 wire normal_cmd=(cmd==7'd9 || cmd==7'd8 || cmd==7'd4 || cmd==7'd20 ||
                  cmd==7'd10 || cmd==7'd6 || cmd==7'd22 || cmd==7'd2 || cmd==7'd32);
 wire invalid_owned=(cmd==8 || cmd==4 || cmd==20 || cmd==10 || cmd==6 || cmd==22) && !owned;
 assign pready=released[1];
 assign buzzer=polarity[1] ^ (armed && active && gpio_data[1]);
 assign alarm_led=polarity[0] ^ (armed && active && gpio_data[0]);
 always @(posedge pclk or negedge arst_n)
  if(!arst_n) begin released<=0;scl_sync<=3;sda_sync<=3;end
  else begin released<={released[0],1'b1};scl_sync<={scl_sync[0],scl_i};sda_sync<={sda_sync[0],sda_i};end
 always @(posedge pclk or negedge arst_n)
  if(!arst_n) begin scl_filtered<=1;sda_filtered<=1;scl_filter_count<=0;sda_filter_count<=0;end
  else begin
   if(scl_sync[1]==scl_filtered) scl_filter_count<=0;
   else if(scl_filter_count==8'(FILTER_CYCLES-1)) begin scl_filtered<=scl_sync[1];scl_filter_count<=0;end
   else scl_filter_count<=scl_filter_count+1'b1;
   if(sda_sync[1]==sda_filtered) sda_filter_count<=0;
   else if(sda_filter_count==8'(FILTER_CYCLES-1)) begin sda_filtered<=sda_sync[1];sda_filter_count<=0;end
   else sda_filter_count<=sda_filter_count+1'b1;
  end
 always @* begin
  prdata=0;pslverror=0;
  if(paddr[1:0]!=0) pslverror=1;
  else if(pwrite) case(paddr)
   8'h08:if(busy || pwdata!=1) pslverror=1;
   8'h0c:if(pwdata==64) begin end
          else if(!active || busy || !normal_cmd || pwdata[31:7]!=0 || invalid_owned) pslverror=1;
   8'h10:if(busy || pwdata>255) pslverror=1;
   8'h18:if(busy || pwdata<32'(MIN_DIV<2?2:MIN_DIV) || pwdata>65535) pslverror=1;
   8'h1c:if(busy || pwdata==0 || pwdata>32'(CLOCK_HZ/10)) pslverror=1;
   8'h20:if(pwdata>3 || (!armed && pwdata!=0) || (!active && pwdata!=0)) pslverror=1;
   8'h24:if(pwdata!=0 && (pwdata!=32'h43474131 || !active)) pslverror=1;
   8'h28:if(!active || armed || pwdata>3) pslverror=1;
   8'h2c:if(armed || pwdata==0 || pwdata>60000) pslverror=1;
   default:pslverror=1;
  endcase
  else case(paddr)
   8'h00:prdata=32'h43335031;
   8'h04:prdata=32'h00010000;
   8'h08:prdata={23'b0,active,sda_filtered,scl_filtered,stuck,arbitration,timed_out,nack,done,busy};
   8'h10:prdata={24'b0,tx};
   8'h14:prdata={24'b0,rx};
   8'h18:prdata={16'b0,divisor};
   8'h1c:prdata=timeout_cycles;
   8'h20:prdata={30'b0,gpio_data};
   8'h24:prdata={31'b0,armed};
   8'h28:prdata={30'b0,polarity};
   8'h2c:prdata=max_on_ms;
   8'h30:prdata={31'b0,active};
   8'h34:prdata=32'(CLOCK_HZ);
   default:pslverror=1;
  endcase
  if(!psel || !penable) pslverror=0;
 end
 task release_error(input bit timeout_error,input bit arbitration_error);
  begin
   state<=IDLE;busy<=0;done<=1;owned<=0;scl_drive_low<=0;sda_drive_low<=0;
   timed_out<=timeout_error;arbitration<=arbitration_error;
  end
 endtask
 always @(posedge pclk or negedge arst_n) begin
  if(!arst_n) begin
   state<=IDLE;divisor<=16'((CLOCK_HZ+1999999)/2000000);ticks<=0;
   timeout_cycles<=32'(CLOCK_HZ/50);elapsed<=0;tx<=0;rx<=0;shift<=0;bit_index<=7;recovery_pulses<=0;
   reading<=0;send_nack<=0;stop_after<=0;owned<=0;busy<=0;done<=0;
   nack<=0;timed_out<=0;arbitration<=0;stuck<=0;scl_drive_low<=0;sda_drive_low<=0;
   gpio_data<=0;polarity<=0;armed<=0;gpio_started<=0;max_on_ms<=5000;
  end else begin
   if(!active) begin armed<=0;gpio_data<=0;end
   else if(armed && gpio_data[1] && (shared_ms-gpio_started)>=max_on_ms) begin gpio_data<=0;armed<=0;end
   if(busy) begin
    elapsed<=elapsed+1'b1;
    if(!active || elapsed>=timeout_cycles-1) release_error(1,0);
    else if(ticks!=0) ticks<=ticks-1'b1;
    else begin
     ticks<=divisor-1'b1;
     case(state)
      START_HOLD0:state<=START_HOLD1;
      START_HOLD1:state<=START_RISE;
      START_RISE:begin scl_drive_low<=0;state<=START_WAIT;end
      START_WAIT:if(scl_filtered) begin
       if(!sda_filtered) begin stuck<=1;release_error(0,1);end
       else state<=START_STABLE;
      end
      START_STABLE:state<=START_PULL;
      START_PULL:begin sda_drive_low<=1;state<=START_HOLD_PULL;end
      START_HOLD_PULL:state<=START_LOW;
      START_LOW:begin scl_drive_low<=1;sda_drive_low<=reading?1'b0:!shift[7];state<=BIT_HOLD0;end
      BIT_HOLD0:state<=BIT_HOLD1;
      BIT_HOLD1:state<=BIT_RISE;
      BIT_RISE:begin scl_drive_low<=0;state<=BIT_SAMPLE;end
      BIT_SAMPLE:if(scl_filtered) begin
       if(!reading && shift[bit_index] && !sda_filtered) release_error(0,1);
       else begin if(reading) shift[bit_index]<=sda_filtered;state<=BIT_LOW;end
      end
      BIT_LOW:begin
       scl_drive_low<=1;
       if(bit_index==0) begin
        if(reading) rx<=shift;
        sda_drive_low<=reading && !send_nack;state<=ACK_HOLD0;
       end else begin bit_index<=bit_index-1'b1;sda_drive_low<=reading?1'b0:!shift[bit_index-1'b1];state<=BIT_HOLD0;end
      end
      ACK_HOLD0:state<=ACK_HOLD1;
      ACK_HOLD1:state<=ACK_RISE;
      ACK_RISE:begin scl_drive_low<=0;state<=ACK_SAMPLE;end
      ACK_SAMPLE:if(scl_filtered) begin if(!reading && sda_filtered) nack<=1;state<=ACK_LOW;end
      ACK_LOW:begin
       scl_drive_low<=1;sda_drive_low<=0;
       if(nack || stop_after) begin sda_drive_low<=1;state<=STOP_HOLD0;end
       else begin state<=IDLE;busy<=0;done<=1;owned<=1;end
      end
      STOP_HOLD0:state<=STOP_HOLD1;
      STOP_HOLD1:state<=STOP_RISE;
      STOP_RISE:begin scl_drive_low<=0;state<=STOP_WAIT;end
      STOP_WAIT:if(scl_filtered) state<=STOP_RELEASE;
      STOP_RELEASE:begin sda_drive_low<=0;state<=STOP_DELAY0;end
      STOP_DELAY0:state<=STOP_DELAY1;
      STOP_DELAY1:state<=STOP_FINISH;
      STOP_FINISH:begin
       if(!sda_filtered) stuck<=1;
       state<=IDLE;busy<=0;done<=1;owned<=0;scl_drive_low<=0;
      end
      REC_HOLD0:state<=REC_HOLD1;
      REC_HOLD1:state<=REC_RISE;
      REC_RISE:begin scl_drive_low<=0;state<=REC_SAMPLE;end
      REC_SAMPLE:if(scl_filtered) state<=REC_LOW;
      REC_LOW:begin
       scl_drive_low<=1;recovery_pulses<=recovery_pulses+1'b1;
       if(recovery_pulses==8) begin sda_drive_low<=1;state<=STOP_HOLD0;end else state<=REC_HOLD0;
      end
      default:release_error(0,1);
     endcase
    end
   end else if(!active) begin scl_drive_low<=0;sda_drive_low<=0;owned<=0;end
   if(access && pwrite && !pslverror) case(paddr)
    8'h08:begin done<=0;nack<=0;timed_out<=0;arbitration<=0;stuck<=0;end
    8'h10:tx<=pwdata[7:0];
    8'h18:divisor<=pwdata[15:0];
    8'h1c:timeout_cycles<=pwdata;
    8'h20:begin gpio_data<=pwdata[1:0];if(pwdata[1] && !gpio_data[1]) gpio_started<=shared_ms;end
    8'h24:begin armed<=pwdata!=0;gpio_data<=0;end
    8'h28:polarity<=pwdata[1:0];
    8'h2c:max_on_ms<=pwdata;
    8'h0c:begin
     if(cmd==64) begin release_error(1,0);armed<=0;gpio_data<=0;end
     else begin
      busy<=1;done<=0;nack<=0;timed_out<=0;arbitration<=0;stuck<=0;elapsed<=0;ticks<=divisor-1'b1;
      reading<=cmd[2];send_nack<=cmd[4];stop_after<=cmd[1];bit_index<=7;shift<=tx;
      if(cmd==32) begin scl_drive_low<=1;sda_drive_low<=0;recovery_pulses<=0;state<=REC_HOLD0;end
      else if(cmd==2) begin scl_drive_low<=1;sda_drive_low<=1;state<=STOP_HOLD0;end
      else if(cmd[0]) begin scl_drive_low<=owned;sda_drive_low<=0;state<=owned?START_HOLD0:START_RISE;end
      else begin scl_drive_low<=1;sda_drive_low<=cmd[2]?1'b0:!tx[7];state<=BIT_HOLD0;end
     end
    end
    default:begin end
   endcase
  end
 end
endmodule
