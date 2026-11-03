`timescale 1ns/1ps
// Diagnostic only. Every counter stays in the clock domain of its input.
// Runs are contiguous DE cycles, not sensor rows. Saturation never wraps.
module c9_stage_counter(input wire clk,arst_n,run,de,output wire [23:0] value);
 reg [10:0] current,maximum;
 reg [11:0] segments;
 reg last_de;
 wire [10:0] next_count=(&current)?current:current+1'b1;
 always @(posedge clk or negedge arst_n)
  if(!arst_n)begin current<=0;maximum<=0;segments<=0;last_de<=0;end
  else if(!run)begin current<=0;maximum<=0;segments<=0;last_de<=0;end
  else begin
   last_de<=de;
   if(de)begin
    current<=next_count;
    if(next_count>maximum)maximum<=next_count;
    if(!last_de && !(&segments))segments<=segments+1'b1;
   end else current<=0;
  end
 assign value={1'b0,maximum,segments};
endmodule

module c9_stage_run(input wire clk,arst_n,run_async,output wire run);
 (* async_reg="true" *) reg first,second;
 always @(posedge clk or negedge arst_n)
  if(!arst_n)begin first<=0;second<=0;end
  else begin first<=run_async;second<=first;end
 assign run=second;
endmodule

module c9_stage_probe(
 input wire arst_n,run_async,phy_clk,isp_clk,video_clk,
 input wire native_vs,native_hs,native_de,
 input wire [15:0] native_wc,input wire [5:0] native_dt,
 input wire [1:0] native_vc,input wire [3:0] native_ppc,
 input wire raw_vs,raw_de,raw_overflow,rgb_vs,rgb_de,rgb_valid,gray_vs,gray_de,
 input wire pixel_vs,pixel_de,source_vs,source_de,mode,fault,config_valid,time_valid,
 output wire [63:0] phy_data,output wire [159:0] isp_data,output wire [31:0] video_data
);
 wire nr,ir,vr;
 c9_stage_run rn(phy_clk,arst_n,run_async,nr);
 c9_stage_run ri(isp_clk,arst_n,run_async,ir);
 c9_stage_run rv(video_clk,arst_n,run_async,vr);
 wire image=native_dt==6'h2b && native_vc==0;
 wire [23:0] nc,rc,dc,vc,jc,gc,pc,sc;
 c9_stage_counter cn(phy_clk,arst_n,nr,native_de && native_hs && image,nc);
 c9_stage_counter cr(isp_clk,arst_n,ir,raw_de,rc);
 c9_stage_counter cd(isp_clk,arst_n,ir,rgb_de,dc);
 c9_stage_counter cv(isp_clk,arst_n,ir,rgb_valid,vc);
 c9_stage_counter cj(isp_clk,arst_n,ir,rgb_de && rgb_valid,jc);
 c9_stage_counter cg(isp_clk,arst_n,ir,gray_de,gc);
 c9_stage_counter cp(video_clk,arst_n,vr,pixel_de,pc);
 c9_stage_counter cs(video_clk,arst_n,vr,source_de,sc);
 reg [15:0] wc;
 reg [6:0] nf;
 always @(posedge phy_clk or negedge arst_n)
  if(!arst_n)begin wc<=0;nf<=0;end
  else if(!nr)begin wc<=0;nf<=0;end
  else begin
   if(native_vs)nf[0]<=1;
   if(native_hs)nf[1]<=1;
   if(native_de && image)begin
    wc<=native_wc;nf[2]<=1;
    if(!native_hs)nf[3]<=1;
    if(native_ppc!=4)nf[4]<=1;
   end
   if(native_de && !image)nf[5]<=1;
   if(raw_overflow)nf[6]<=1; // raw FIFO producer is this clock domain
  end
 assign phy_data={8'he1,nr,nf,wc,8'b0,nc};
 reg [6:0] inf;
 (* async_reg="true" *) reg ov1,ov2;
 always @(posedge isp_clk or negedge arst_n)
  if(!arst_n)begin inf<=0;ov1<=0;ov2<=0;end
  else begin
   ov1<=raw_overflow;ov2<=ov1;
   if(!ir)inf<=0;
   else begin
    if(raw_vs)inf[0]<=1;
    if(rgb_vs)inf[1]<=1;
    if(gray_vs)inf[2]<=1;
    if(rgb_de && !rgb_valid)inf[3]<=1;
    if(rgb_valid && !rgb_de)inf[4]<=1;
    if(ov2)inf[5]<=1;
    if(raw_de)inf[6]<=1;
   end
  end
 assign isp_data={32'hc9e21001,ir,inf,gc,jc,vc,dc,rc};
 reg [2:0] vf;
 always @(posedge video_clk or negedge arst_n)
  if(!arst_n)vf<=0;
  else if(!vr)vf<=0;
  else begin
   if(pixel_vs)vf[0]<=1;
   if(source_vs)vf[1]<=1;
   if(source_de)vf[2]<=1;
  end
 assign video_data={2'b10,vf,time_valid,config_valid,fault,mode,vr,sc[22:12],pc[22:12]};
endmodule
