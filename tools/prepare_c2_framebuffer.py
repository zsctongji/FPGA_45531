"""Generate a common video pipeline and the four-client functional test harness.
No encrypted DDR/CPU model or physical HDMI/MIPI is exercised by this test.
"""
from pathlib import Path
from prepare_c2_vendor import SP
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/06_soc_c2'

def pipeline():
    head='''`timescale 1ns/1ps
// A raster timing/GRAY8 boundaries; C2 owns the only DDR controller.
module c2_video_pipeline #(parameter integer WIDTH=1920,HEIGHT=1080)(
input wire arst_n,mem_clk,video_clk,display_clk,enable,time_valid,
input wire pixel_vs,pixel_de,input wire [7:0] pixel_gray,
input wire [31:0] now_ms,source_frames,
input wire record_valid,record_complete,input wire [31:0] record_id,record_ms,
input wire display_vs,display_de,display_hs,
output wire [23:0] display_rgb,output wire out_vs,out_de,out_hs,
output wire display_busy,display_available,display_failed,
output wire [31:0] display_frame_id,display_timestamp_ms,
output wire [31:0] published,dropped,overflow_frames,write_errors,read_errors,
output wire [31:0] repeated,empty_scans,underflows,missed_scans,completed_scans,max_aw_wait,max_ar_wait,
'''
    head+=',\n'.join(('input' if d=='out' else 'output')+' wire '+(f'[{w-1}:0] ' if w>1 else '')+n for n,d,w in SP)+'\n);\n'
    head+='''localparam integer STRIDE=((WIDTH+15)/16)*16;
localparam integer PITCH=((STRIDE*HEIGHT+4095)/4096)*4096;
localparam LAYOUT_OK=WIDTH>=16 && WIDTH<=65535 && HEIGHT>0 && HEIGHT<=65535 && PITCH>0 && PITCH<=5591040;
wire safe_enable=enable && LAYOUT_OK;
wire iv,ir,ov,orr,sv,sr;wire [129:0] idata,odata;
c2_video_ingress #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) ingress(
.arst_n(arst_n),.video_clk(video_clk),.mem_clk(mem_clk),.enable(safe_enable),.time_valid(time_valid),
.vs(pixel_vs),.de(pixel_de),.gray(pixel_gray),.now_ms(now_ms),.source_frames(source_frames),
.record_valid(record_valid),.record_complete(record_complete),.record_id(record_id),.record_ms(record_ms),
.valid(iv),.ready(ir),.data(idata),.overflow_frames(overflow_frames));
c2_video_framebuffer #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) framebuffer(
.arst_n(arst_n),.clk(mem_clk),.display_clk(display_clk),.enable(safe_enable),
.in_valid(iv),.in_ready(ir),.in_data(idata),.scan_valid(sv),.scan_ready(sr),
.out_valid(ov),.out_ready(orr),.out_data(odata),
.published(published),.dropped(dropped),.write_errors(write_errors),.read_errors(read_errors),
.repeated(repeated),.empty_scans(empty_scans),.max_aw_wait(max_aw_wait),.max_ar_wait(max_ar_wait),.bank_states(),
'''
    head+=',\n'.join(f'.{n}({n})' for n,d,w in SP)+');\n'
    head+='''c2_video_scanout #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) scanout(
.arst_n(arst_n),.clk(display_clk),.vs(display_vs),.de(display_de),.hs(display_hs),
.scan_valid(sv),.scan_ready(sr),.in_valid(ov),.in_ready(orr),.in_data(odata),
.rgb(display_rgb),.out_vs(out_vs),.out_de(out_de),.out_hs(out_hs),
.busy(display_busy),.frame_available(display_available),.frame_failed(display_failed),
.frame_id(display_frame_id),.timestamp_ms(display_timestamp_ms),.underflows(underflows),
.missed_scans(missed_scans),.completed_scans(completed_scans));
endmodule
'''
    (P/'rtl/c2_video_pipeline.sv').write_text(head,encoding='utf-8')

DRIVER=r'''
reg bg_run=0,bg_busy0=0,bg_busy1=0;integer bg0=0,bg1=0,display_checks=0,full_checks=0;
integer simultaneous=0,overlap_ai=0,overlap_display=0;
integer peak_aw=0,peak_ar=0,cpu_aw_wait=0,cpu_ar_wait=0,ml_aw_wait=0,ml_ar_wait=0;
integer video_arb_aw_wait=0,video_arb_ar_wait=0;
integer cpu_max_wait=0,ml_max_wait=0;
reg video_write_outstanding=0;reg [31:0] last_published=0;
always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin video_write_outstanding<=0;last_published<=0;end
 else begin
  if(fbpipe.awvalid && fbpipe.awready) video_write_outstanding<=1;
  if(fbpipe.bvalid && fbpipe.bready) video_write_outstanding<=0;
  if(fb_published!=last_published &&
     (video_write_outstanding || !fbpipe.framebuffer.ended || fbpipe.framebuffer.wbad ||
      fbpipe.framebuffer.w_offset!=STRIDE*FRAME_HEIGHT/16)) $fatal(1,"READY before source/final BRESP fence");
  last_published<=fb_published;
 end
end
always @(posedge clk) if(rst_n) begin
 // Measure AFTER request serializers, at real arbitration inputs.
 video_arb_aw_wait=dut.q_awvalid&&!dut.q_awready?video_arb_aw_wait+1:0;
 video_arb_ar_wait=dut.q_arvalid&&!dut.q_arready?video_arb_ar_wait+1:0;
 if(video_arb_aw_wait>peak_aw) peak_aw=video_arb_aw_wait;
 if(video_arb_ar_wait>peak_ar) peak_ar=video_arb_ar_wait;
 cpu_aw_wait=u_awvalid[0]&&!u_awready[0]?cpu_aw_wait+1:0;
 cpu_ar_wait=u_arvalid[0]&&!u_arready[0]?cpu_ar_wait+1:0;
 ml_aw_wait=u_awvalid[2]&&!u_awready[2]?ml_aw_wait+1:0;
 ml_ar_wait=u_arvalid[2]&&!u_arready[2]?ml_ar_wait+1:0;
 if(cpu_aw_wait>cpu_max_wait) cpu_max_wait=cpu_aw_wait;
 if(cpu_ar_wait>cpu_max_wait) cpu_max_wait=cpu_ar_wait;
 if(ml_aw_wait>ml_max_wait) ml_max_wait=ml_aw_wait;
 if(ml_ar_wait>ml_max_wait) ml_max_wait=ml_ar_wait;
 if(fbpipe.awvalid && fbpipe.arvalid) simultaneous=simultaneous+1;
 if(transferring && (fbpipe.awvalid || fbpipe.arvalid)) overlap_ai=overlap_ai+1;
 if(fbpipe.framebuffer.rs!=0 && fbpipe.framebuffer.ws!=0 && bg_run) overlap_display=overlap_display+1;
 if(fbpipe.framebuffer.ws==3 && !fbpipe.wvalid) $fatal(1,"Video DDR writer reserved a burst without all data");
end
initial forever begin
 wait(bg_run);bg_busy0=1;write_burst(0,32'h10000+(bg0%16)*256,4,bg0,0);
 read_burst(0,32'h10000+(bg0%16)*256,4,bg0,0);bg0=bg0+1;bg_busy0=0;
end
initial forever begin
 wait(bg_run);bg_busy1=1;write_burst(1,32'h18000+(bg1%16)*256,4,100+bg1,0);
 read_burst(1,32'h18000+(bg1%16)*256,4,100+bg1,0);bg1=bg1+1;bg_busy1=0;
end
function [7:0] source_pixel(input integer seq,input integer x,input integer y);
 begin
  if(x%STEP_X==0 && y%STEP_Y==0) source_pixel=8'((y/STEP_Y*96+x/STEP_X)*17+seq+1);
  else source_pixel=8'(x*3+y*5+seq+73);
 end
endfunction
task check_bank(input integer seq);
 integer bank,x,y,off;reg found;reg [7:0] expected,observed;
 begin
  found=0;
  for(bank=0;bank<3;bank=bank+1) if(fbpipe.framebuffer.banks[bank]>=2 && fbpipe.framebuffer.ids[bank]==seq) begin
   found=1;
   if(fbpipe.framebuffer.stamps[bank]!==expected_stamp[seq]) $fatal(1,"Full-frame first-DE timestamp changed");
   for(y=0;y<FRAME_HEIGHT;y=y+1) for(x=0;x<STRIDE;x=x+1) begin
    off=32'h20000+bank*PITCH+y*STRIDE+x;
    observed=memory_model.memory[off/16][(off%16)*8+:8];
    expected=x<FRAME_WIDTH?source_pixel(seq,x,y):8'd0;
    if(observed!==expected) $fatal(1,"Video bank corruption seq=%0d bank=%0d x=%0d y=%0d got=%h expected=%h",seq,bank,x,y,observed,expected);
    full_checks=full_checks+1;
   end
  end
  if(!found) $fatal(1,"Published frame absent from banks seq=%0d",seq);
 end
endtask
task scan(input integer seq,input integer force_underflow);
 integer x,y,prior;reg [7:0] expected;
 begin
  prior=fb_underflows;
  @(negedge dclk);display_vs=1;display_de=0;
  repeat(4) @(negedge dclk);display_vs=0;
  if(force_underflow!=1) repeat(2000) @(negedge dclk);
  for(y=0;y<FRAME_HEIGHT;y=y+1) begin
   for(x=0;x<FRAME_WIDTH;x=x+1) begin
    display_de=1;@(posedge dclk);#1;
    if(force_underflow==0 && seq>=0) begin
     expected=source_pixel(seq,x,y);
     if(out_rgb!=={3{expected}} || !out_de || fb_display_id!=seq || fb_display_ms!==expected_stamp[seq] || fb_failed)
      $fatal(1,"Display tearing/underflow seq=%0d id=%0d x=%0d y=%0d rgb=%h exp=%h fail=%b",seq,fb_display_id,x,y,out_rgb,expected,fb_failed);
     display_checks=display_checks+1;
    end
    if(force_underflow==1 && out_rgb!==0) $fatal(1,"Starved scan shifted/stale pixels instead of black");
    @(negedge dclk);
   end
   display_de=0;repeat(10) @(negedge dclk);
  end
  display_de=0;wait(!fb_busy);repeat(30) @(negedge dclk);
  if(force_underflow==1 && fb_underflows<=prior) $fatal(1,"Starvation was not detected");
 end
endtask
task release_image(input integer seq);
 reg slot;reg [31:0] generation;
 begin collect(seq,0,slot,generation);control(3,slot,generation,0);control(4,slot,generation,0);end
endtask
reg tmp_slot;reg [31:0] tmp_generation;reg [2:0] tmp_status;integer count_before;
initial begin
 #1;rst_n=0;#53;rst_n=1;wait(a_source.capture_rst_n);repeat(12) @(negedge vclk);boundary();bg_run=1;
 // Source frame0 writes while CPU/TinyML traffic is live. No READY before A's next VS.
 pixels(0,0);
 if(fb_published!=0) $fatal(1,"Full frame published before physical source verdict");
 boundary();wait(fb_published==1);check_bank(0);release_image(0);$display("CHECK framebuffer frame0 + AI readback");
 if(!EXTENDED) begin
  scan(0,0);
  if(fb_failed || fb_overflow || fb_completed!=1 || !bg0 || !bg1) $fatal(1,"Full-HD scan coverage/error");
  $display("PASS tb_c2_framebuffer geometry=%0dx%0d full_HD=1 stride=%0d bank_pitch=%0d full_bytes=%0d display_bytes=%0d cpu_bursts=%0d tinyml_bursts=%0d max_aw_wait=%0d max_ar_wait=%0d actual_full_frame_write_read final_B_fence single_DDR synthetic_masters",FRAME_WIDTH,FRAME_HEIGHT,STRIDE,PITCH,full_checks,display_checks,bg0,bg1,peak_aw,peak_ar);
  $finish;
 end
 fork
  begin scan(0,0);end
  begin pixels(1,0);boundary();wait(fb_published==2);check_bank(1);release_image(1);end
 join
 $display("CHECK simultaneous source/display/AI/CPU/TinyML");scan(1,0);scan(1,0);
 if(fb_repeated==0) $fatal(1,"No repeat of held DISPLAY bank");
 // Keep DISPLAY frame1 and fill the other banks; newest whole source frame must drop.
 pixels(2,0);boundary();wait(fb_published==3);release_image(2);
 pixels(3,0);boundary();wait(fb_published==4);release_image(3);
 count_before=fb_dropped;pixels(4,0);boundary();release_image(4);
 wait(fb_dropped>count_before);
 if(fb_published!=4) $fatal(1,"No-free-bank frame incorrectly published");
 $display("CHECK no-free-bank drop");scan(2,0);scan(3,0);
 // Invalid geometry is drained, does not become READY, next valid frame recovers.
 count_before=fb_dropped;pixels(5,1);boundary();wait(fb_dropped>count_before);
 pixels(6,0);boundary();wait(fb_published==5);check_bank(6);release_image(6);
 $display("CHECK malformed recovery");scan(6,1);scan(6,0);$display("CHECK underflow recovery");
 // Stop background traffic before injecting bus faults, to target only video.
 bg_run=0;wait(!bg_busy0 && !bg_busy1);repeat(500) @(negedge clk);
 inject_b_error=1;count_before=fb_write_errors;
 pixels(7,0);boundary();wait(fb_write_errors>count_before);inject_b_error=0;
 // AI DMA used the same injected error; explicitly collect error if it failed.
 wait(delivered_valid);
 tmp_status=delivered[547:545];collect(7,tmp_status,tmp_slot,tmp_generation);
 if(tmp_status==0) begin control(3,tmp_slot,tmp_generation,0);control(4,tmp_slot,tmp_generation,0);end
 if(fb_published!=5) $fatal(1,"BRESP-failed video became READY");
 inject_r_error=1;count_before=fb_read_errors;
 scan(6,-1);wait(fb_read_errors>count_before);inject_r_error=0;
 if(!fb_failed) $fatal(1,"RRESP error failed to invalidate scan");
 // Stall new DDR bursts while real source pixels continue: overflow must poison
 // the whole video frame, then drain/recover without publishing partial pixels.
 count_before=fb_dropped;
 fork
  begin pixels(8,0);boundary();end
  begin repeat(500) @(negedge vclk);pause_ddr=1;wait(capture_record_valid);repeat(30) @(negedge vclk);pause_ddr=0;end
 join
 wait(fb_dropped>count_before);release_image(8);
 if(fb_overflow!=1 || fb_published!=5) $fatal(1,"Source overflow did not discard exactly one full frame");
 pixels(9,0);boundary();wait(fb_published==6);check_bank(9);release_image(9);scan(9,0);
 $display("CHECK BRESP/RRESP and source-overflow recovery");
 // Reset while source, display and AXI are active. Memory content alone must not create READY.
 fork
  begin pixels(10,0);end
  begin wait(fbpipe.wvalid && fbpipe.wready);@(negedge clk);rst_n=0;end
 join
 pixel_de=0;pixel_vs=0;display_de=0;display_vs=0;repeat(8) @(negedge clk);rst_n=1;
 wait(a_source.capture_rst_n);repeat(10) @(negedge vclk);
 if(fb_published || fb_busy || fbpipe.framebuffer.bank_states || states) $fatal(1,"Ghost frame after common reset");
 boundary();pixels(0,0);boundary();wait(fb_published==1);check_bank(0);release_image(0);scan(0,0);
 if(core_protocol_error || cpu_adapter_error || cpu_rejected || protocol_error || fb_overflow)
  $fatal(1,"Unexpected fabric/capture error");
 if(!overlap_ai || !overlap_display || bg0<2 || bg1<2 || !display_checks || !peak_aw || !peak_ar || !cpu_max_wait || !ml_max_wait)
  $fatal(1,"Missing concurrent/wait coverage ai=%0d rw=%0d cpu=%0d ml=%0d aw=%0d ar=%0d",overlap_ai,overlap_display,bg0,bg1,fb_max_aw,fb_max_ar);
 $display("PASS tb_c2_framebuffer geometry=%0dx%0d stride=%0d bank_pitch=%0d full_bytes=%0d display_bytes=%0d cpu_bursts=%0d tinyml_bursts=%0d overlap_ai=%0d overlap_rw=%0d max_aw_wait=%0d max_ar_wait=%0d cpu_max_wait=%0d tinyml_max_wait=%0d source_verdict final_B_fence triple_buffer repeat drop malformed underflow BRESP RRESP source_overflow common_reset single_DDR synthetic_masters",FRAME_WIDTH,FRAME_HEIGHT,STRIDE,PITCH,full_checks,display_checks,bg0,bg1,overlap_ai,overlap_display,peak_aw,peak_ar,cpu_max_wait,ml_max_wait);
 $finish;
end
initial begin #150000000;$fatal(1,"Concurrent framebuffer timeout ws=%0d rs=%0d pub=%0d drop=%0d ingress_active=%b ingress_bad=%b source_records=%0d busy=%b underflows=%0d",fbpipe.framebuffer.ws,fbpipe.framebuffer.rs,fb_published,fb_dropped,fbpipe.ingress.active,fbpipe.ingress.bad,record_checks,fb_busy,fb_underflows);end
endmodule
'''

def test():
    s=(P/'sim/tb_c2_video.sv').read_text(encoding='utf-8-sig')
    s=s.replace('module tb_c2_video #','module tb_c2_framebuffer #').replace('FRAME_WIDTH=1920,FRAME_HEIGHT=1080,STEP_X=20,STEP_Y=20','FRAME_WIDTH=384,FRAME_HEIGHT=216,STEP_X=4,STEP_Y=4')
    s=s[:s.index('reg a,b,tmp;')]+DRIVER
    s=s.replace('localparam N=3;', '''localparam N=3;
localparam STRIDE=((FRAME_WIDTH+15)/16)*16,PITCH=((STRIDE*FRAME_HEIGHT+4095)/4096)*4096;
reg dclk=0;always #13 dclk=~dclk;
reg display_vs=0,display_de=0,pause_ddr=0;wire [23:0] out_rgb;wire out_de;
wire raw_awready,raw_arready;
wire fb_busy,fb_available,fb_failed;
wire [31:0] fb_display_id,fb_display_ms,fb_published,fb_dropped,fb_overflow,fb_write_errors,fb_read_errors;
wire [31:0] fb_repeated,fb_empty,fb_underflows,fb_missed,fb_completed,fb_max_aw,fb_max_ar;
''')
    for n,d,w in SP:
        if d=='in':
            old=f'reg [N*{w}-1:0] s_{n}=0;'
            assert old in s,old
            s=s.replace(old,f'wire [N*{w}-1:0] s_{n};\nreg [{2*w-1}:0] drive_{n}=0;\nassign s_{n}[0+:{2*w}]=drive_{n};')
            # Only tasks drive the synthetic CPU/TinyML request channels.
            start=s.index('task automatic write_burst');end=s.index('integer word_index=',start)
            section=s[start:end].replace('s_'+n,'drive_'+n)
            s=s[:start]+section+s[end:]
            start=s.index('task read_image');end=s.index('endtask',start)
            section=s[start:end].replace('s_'+n,'drive_'+n)
            s=s[:start]+section+s[end:]
    s=s.replace(".VIDEO_BYTES(32'h10000)",".VIDEO_BYTES(32'h1000000)")
    s=s.replace('c2_ddr_model memory_model(',"c2_ddr_model #(.WORDS((32'h20000+PITCH*3)/16+16)) memory_model(")
    s=s.replace('if(mode==0 && !a_source.capture.sampler.pending_last)', 'if(mode==0 && rst_n && !a_source.capture.sampler.pending_last)')
    a=s.index('c2_ddr_model #(')
    b=s.index('integer checks=',a)
    model=s[a:b].replace('.awvalid(m_awvalid)', '.awvalid(m_awvalid && !pause_ddr)').replace('.awready(m_awready)', '.awready(raw_awready)')
    model=model.replace('.arvalid(m_arvalid)', '.arvalid(m_arvalid && !pause_ddr)').replace('.arready(m_arready)', '.arready(raw_arready)')
    model+='assign m_awready=raw_awready && !pause_ddr;\nassign m_arready=raw_arready && !pause_ddr;\n'
    s=s[:a]+model+s[b:]
    block='''c2_video_pipeline #(.WIDTH(FRAME_WIDTH),.HEIGHT(FRAME_HEIGHT)) fbpipe(
.arst_n(rst_n),.mem_clk(clk),.video_clk(vclk),.display_clk(dclk),.enable(1'b1),.time_valid(sample_time_valid),
.pixel_vs(pixel_vs),.pixel_de(pixel_de),.pixel_gray(pixel_gray),.now_ms(shared_ms),.source_frames(capture_source_frames),
.record_valid(capture_record_valid),.record_complete(capture_record_complete),.record_id(capture_record_frame_id),.record_ms(capture_record_timestamp_ms),
.display_vs(display_vs),.display_de(display_de),.display_hs(1'b0),.display_rgb(out_rgb),.out_vs(),.out_de(out_de),.out_hs(),
.display_busy(fb_busy),.display_available(fb_available),.display_failed(fb_failed),
.display_frame_id(fb_display_id),.display_timestamp_ms(fb_display_ms),
.published(fb_published),.dropped(fb_dropped),.overflow_frames(fb_overflow),.write_errors(fb_write_errors),.read_errors(fb_read_errors),
.repeated(fb_repeated),.empty_scans(fb_empty),.underflows(fb_underflows),.missed_scans(fb_missed),.completed_scans(fb_completed),.max_aw_wait(fb_max_aw),.max_ar_wait(fb_max_ar),
'''+',\n'.join(f'.{n}(s_{n}[{2*w}+:{w}])' for n,d,w in SP)+');\n'
    s=s.replace('c2_ddr_model #(',block+'c2_ddr_model #(',1)
    (P/'sim/tb_c2_framebuffer.sv').write_text(s,encoding='utf-8')

if __name__=='__main__':
    pipeline();test();print('Prepared video pipeline and concurrent framebuffer harness.')
