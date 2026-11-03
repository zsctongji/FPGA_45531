`timescale 1ns/1ps
// Synthetic stimulus through the actual split/ISP/luma/capture RTL.
// MODE 1: native payload gap each 18 four-pixel beats (72 pixels).
// MODE 2: suppress ISP valid at the luma boundary. MODE 3: source fault gate.
module tb_stage_chain #(parameter MODE=0, PHASE=0, WIDTH=1920);
 reg rst=0,c50=0,c100=0,c200=0,run=0;
 always #10 c50=~c50;
 initial begin #(PHASE);forever #5 c100=~c100;end
 always #2.5 c200=~c200;
 reg vs=0,hs=0,de=0;
 wire rvs,rhs,rde,rov,gvs,ghs,gde,pvs,phs,pde,pov;
 wire [15:0] raw2,gray2;
 wire ivs,ihs,ide,ivalid;wire [47:0] rgb;
 wire [7:0] pixel;
 physical_pixel_split raw_split(rst,c50,c100,vs,hs,de,32'h80808080,rvs,rhs,rde,raw2,rov);
 a_phys_debayer_top_2to1 isp(.in_pclk(c100),.in_rstn(rst),
 .raw_vs_i(rvs),.raw_hs_i(rhs),.raw_de_i(rde),.raw_valid_i(rde),.raw_datax4_i(raw2),
 .r_gain(16'd255),.g_gain(16'd255),.b_gain(16'd255),
 .rgb_vs_o(ivs),.rgb_hs_o(ihs),.rgb_de_o(ide),.rgb_valid_o(ivalid),.rgb_datax2_o(rgb));
 wire effective_valid=ivalid && MODE!=2;
 physical_gray2 luma(c100,rst,ivs,ihs,ide && effective_valid,rgb,gvs,ghs,gde,gray2);
 physical_pixel_split #(.IN_BITS(16),.OUT_BITS(8)) gray_split(rst,c100,c200,gvs,ghs,gde,gray2,pvs,phs,pde,pixel,pov);
 wire source_vs=run && pvs;
 wire source_de=run && pde && MODE!=3;
 wire [63:0] native;wire [159:0] stages;wire [31:0] output_stage;
 c9_stage_probe probe(.arst_n(rst),.run_async(run),.phy_clk(c50),.isp_clk(c100),.video_clk(c200),
 .native_vs(vs),.native_hs(hs),.native_de(de),.native_wc(16'd2400),.native_dt(6'h2b),.native_vc(2'b0),.native_ppc(4'd4),
 .raw_vs(rvs),.raw_de(rde),.raw_overflow(rov),.rgb_vs(ivs),.rgb_de(ide),.rgb_valid(effective_valid),.gray_vs(gvs),.gray_de(gde),
 .pixel_vs(pvs),.pixel_de(pde),.source_vs(source_vs),.source_de(source_de),.mode(1'b0),.fault(MODE==3),.config_valid(1'b1),.time_valid(1'b1),
 .phy_data(native),.isp_data(stages),.video_data(output_stage));
 wire record_valid,complete;wire [15:0] width,height;wire [31:0] frames,errors;
 video_a_capture #(.FRAME_WIDTH(WIDTH),.FRAME_HEIGHT(4),.STEP_X(20),.STEP_Y(1)) capture(
 .clk(c200),.rst_n(rst),.in_vs(source_vs),.in_de(source_de),.in_gray(pixel),.now_ms(32'd1),
 .record_valid(record_valid),.record_complete(complete),.record_width(width),.record_height(height),.source_frames(frames),.format_errors(errors));
 integer f,y,x;integer complete_records=0;
 always @(posedge c200) if(rst && record_valid && complete)complete_records=complete_records+1;
 initial begin
  #1;rst=0;#67;rst=1;
  repeat(50)@(negedge c50);run=1;repeat(50)@(negedge c50);
  for(f=0;f<3;f=f+1)begin
   vs=1;repeat(5)@(negedge c50);vs=0;repeat(20)@(negedge c50);
   for(y=0;y<4;y=y+1)begin
    hs=1;repeat(2)@(negedge c50);de=1;
    for(x=0;x<WIDTH/4;x=x+1)begin
     if(MODE==1 && x>0 && x%18==0)begin de=0;@(negedge c50);de=1;end
     @(negedge c50);
    end
    de=0;repeat(2)@(negedge c50);hs=0;repeat(14)@(negedge c50);
   end
   repeat(50)@(negedge c50);
  end
  vs=1;repeat(100)@(negedge c50);
  if(rov || pov)$fatal(1,"Unexpected overflow in stage stimulus");
  $display("STAGES mode=%0d phase=%0d native=%h isp=%h video=%h capture_width=%0d height=%0d frames=%0d errors=%0d complete_records=%0d",MODE,PHASE,native,stages,output_stage,width,height,frames,errors,complete_records);
  if(MODE==0 && (complete_records!=3 || width!=WIDTH || height!=4))$fatal(1,"Continuous baseline failed");
  if(MODE==1 && (complete_records!=0 || width!=72 || native[22:12]!=18 || stages[22:12]!=36 || output_stage[10:0]!=72))$fatal(1,"Gap did not reproduce 72-pixel fragmentation");
  if(MODE==2 && (stages[70:60]!=0 || stages[46:36]==0 || output_stage[10:0]!=0 || !stages[123]))$fatal(1,"Missing valid was not localized at ISP gate");
  if(MODE==3 && (output_stage[10:0]==0 || output_stage[21:11]!=0 || !output_stage[24]))$fatal(1,"Fault gate was not localized after pixel output");
  $display("PASS tb_stage_chain mode=%0d phase=%0d",MODE,PHASE);$finish;
 end
 initial begin #10000000;$fatal(1,"Stage chain timeout");end
endmodule
