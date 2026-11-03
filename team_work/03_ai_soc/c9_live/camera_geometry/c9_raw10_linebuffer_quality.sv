`timescale 1ns/1ps
// Fixed RAW10/VC0, four pixels per beat. In Generic CSI mode valid gaps and
// HS edges are NOT packet boundaries. Count validated payload, buffer a whole
// expected-width line, then emit an uninterrupted burst into the existing ISP.
// Full-frame payload count plus live transport error monitoring are mandatory.
// No padding, repeated pixels, partial-line release, or automatic error recovery.
module c9_raw10_linebuffer_quality #(
 parameter WIDTH=1920,HEIGHT=1080,GAP_LIMIT=50000,VS_GUARD=32
)(
 input wire clk,arst_n,run_async,vs,de,
 input wire [31:0] data,input wire [15:0] wordcount,
 input wire [5:0] datatype,input wire [1:0] vc,input wire [3:0] ppc,
 input wire transport_fault,quality_ready,
 output reg ovs,ohs,ode,output reg [31:0] odata,
 output wire fault,output reg armed,
 output reg [6:0] errors,output reg [18:0] last_frame_beats,
 output reg [15:0] input_frames,output reg [15:0] output_lines
);
 localparam GROUPS=WIDTH/4,EXPECTED_BYTES=WIDTH*10/8;
 localparam AW=$clog2(GROUPS),GW=$clog2(GAP_LIMIT+1);
 localparam IDLE=0,GUARD=1,VSPULSE=2,BLANK=3,READ=4,DRAIN=5;
 (* async_reg="true" *) reg run1,run2;
 reg vs_d,wbank,rbank,pending_vs;
 reg [1:0] busy,ready,first_line;
 reg [AW-1:0] column,read_column;
 reg [15:0] rows;
 reg [18:0] frame_beats;
 reg [GW-1:0] gap_count;
 reg [2:0] state;
 reg [7:0] delay_count;
 reg read_d;
 reg [31:0] read_data;
 // No reset on memory: ownership/ready state is reset instead. Infer BRAM.
 reg [31:0] memory[0:2*(1<<AW)-1];
 wire boundary=vs && !vs_d;
 wire metadata_ok=wordcount==EXPECTED_BYTES && datatype==6'h2b && vc==0;
 assign fault=|errors;
 wire take=run2 && armed && !fault && !transport_fault && de && !boundary &&
           metadata_ok && ppc==4 && rows<HEIGHT && (column!=0 || !busy[wbank]);
 wire read_enable=state==READ && run2 && !fault && !transport_fault;
 always @(posedge clk)begin
  if(take)memory[{wbank,column}]<=data;
  if(read_enable)read_data<=memory[{rbank,read_column}];
 end
 always @(posedge clk or negedge arst_n)
  if(!arst_n)begin run1<=0;run2<=0;end
  else begin run1<=run_async;run2<=run1;end
 always @(posedge clk or negedge arst_n)
  if(!arst_n)begin
   vs_d<=0;wbank<=0;rbank<=0;pending_vs<=0;busy<=0;ready<=0;first_line<=0;
   column<=0;read_column<=0;rows<=0;frame_beats<=0;gap_count<=0;state<=IDLE;delay_count<=0;
   read_d<=0;ovs<=0;ohs<=0;ode<=0;odata<=0;errors<=0;armed<=0;
   last_frame_beats<=0;input_frames<=0;output_lines<=0;
  end else if(!run2)begin
   vs_d<=vs;wbank<=0;rbank<=0;pending_vs<=0;busy<=0;ready<=0;first_line<=0;
   column<=0;read_column<=0;rows<=0;frame_beats<=0;gap_count<=0;state<=IDLE;delay_count<=0;
   read_d<=0;ovs<=0;ohs<=0;ode<=0;odata<=0;errors<=0;armed<=0;
   last_frame_beats<=0;input_frames<=0;output_lines<=0;
  end else begin
   vs_d<=vs;read_d<=read_enable;ovs<=state==VSPULSE;ohs<=read_d;ode<=read_d;odata<=read_data;
   if(armed && transport_fault)errors[4]<=1;
   if(fault || transport_fault)begin ovs<=0;ohs<=0;ode<=0;read_d<=0;end
   else begin
    if(boundary)begin
     if(de)errors[3]<=1;
     if(armed)begin
      last_frame_beats<=frame_beats;input_frames<=input_frames+1'b1;
      if(rows!=HEIGHT || column!=0 || frame_beats!=GROUPS*HEIGHT)errors[3]<=1;
     end
     if(pending_vs)errors[5]<=1;
     pending_vs<=1;armed<=1;rows<=0;column<=0;frame_beats<=0;gap_count<=0;
    end else if(armed && de)begin
     gap_count<=0;
     if(!metadata_ok)errors[1]<=1;
     if(ppc!=4)errors[2]<=1;
     if(rows>=HEIGHT)errors[3]<=1;
     if(column==0 && busy[wbank])errors[0]<=1;
     if(take)begin
      frame_beats<=frame_beats+1'b1;
      if(column==0)begin busy[wbank]<=1;first_line[wbank]<=rows==0;end
      if(column==GROUPS-1)begin
       column<=0;rows<=rows+1'b1;ready[wbank]<=1;wbank<=~wbank;
      end else column<=column+1'b1;
     end
    end else if(armed && column!=0)begin
     if(gap_count==GAP_LIMIT-1)errors[6]<=1;
     else gap_count<=gap_count+1'b1;
    end
    case(state)
     IDLE:begin
      // Old-frame rows drain before the next frame marker. New first row waits.
      if(!quality_ready)begin end
      else if(pending_vs && (!ready[rbank] || first_line[rbank]))begin
       state<=GUARD;delay_count<=VS_GUARD-1;pending_vs<=0;
      end else if(ready[rbank])begin state<=READ;read_column<=0;end
     end
     GUARD:if(delay_count==0)begin state<=VSPULSE;delay_count<=3;end else delay_count<=delay_count-1'b1;
     VSPULSE:if(delay_count==0)begin state<=BLANK;delay_count<=7;end else delay_count<=delay_count-1'b1;
     BLANK:if(delay_count==0)state<=IDLE;else delay_count<=delay_count-1'b1;
     READ:if(read_column==GROUPS-1)begin state<=DRAIN;read_column<=0;end else read_column<=read_column+1'b1;
     DRAIN:begin
      busy[rbank]<=0;ready[rbank]<=0;rbank<=~rbank;output_lines<=output_lines+1'b1;
      state<=BLANK;delay_count<=7;
     end
     default:state<=IDLE;
    endcase
   end
  end
 initial begin
  if(WIDTH<16 || WIDTH%4 || WIDTH>2048 || HEIGHT<1 || HEIGHT>1080 || GROUPS*HEIGHT>=524288 || GAP_LIMIT<2 || VS_GUARD<2 || VS_GUARD>256)
   $error("Unsupported fixed RAW10 linebuffer parameters");
 end
endmodule
