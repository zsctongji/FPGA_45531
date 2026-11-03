"""Reuse the AXI/DDR/APB harness, replacing direct grid samples with full pixels.
The pinned A capture and sampler are exercised without changes. No camera/board.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/06_soc_c2'

DRIVER=r'''
integer record_checks=0,bad_records=0,sof_checks=0,eof_checks=0,stamp_edges=0,time_wraps=0;
integer traffic_during_image=0;reg transferring=0;
reg [31:0] previous_ms=32'hfffffffc;
reg [31:0] grid_clock[0:31],eof_clock[0:31];
reg [31:0] last_record_id=0;reg last_record_complete=0;
always @(posedge pclk or negedge rst_n) begin
 if(!rst_n) previous_ms=32'hfffffffc;
 else begin
  if(dut.control.clock_service.cpu_ms<previous_ms &&
     (dut.control.clock_service.cpu_ms-previous_ms)<32'h80000000) time_wraps=time_wraps+1;
  previous_ms=dut.control.clock_service.cpu_ms;
 end
end
always @(posedge clk or negedge rst_n) begin
 if(!rst_n) transferring<=0;
 else begin
  if(image_start_valid && image_start_ready) transferring<=1;
  if(image_done_valid && image_done_ready) transferring<=0;
  if(transferring && ((|(s_awvalid&s_awready)) || (|(s_arvalid&s_arready))))
   traffic_during_image=traffic_during_image+1;
 end
end
always @(posedge vclk) if(rst_n && a_source.capture_rst_n) begin
 if(capture_record_valid) begin
  record_checks=record_checks+1;last_record_id=capture_record_frame_id;
  last_record_complete=capture_record_complete;
  if(capture_record_timestamp_ms!==expected_stamp[capture_record_frame_id])
   $fatal(1,"First-DE timestamp lost in source record");
  if(capture_record_complete) begin
   if(capture_record_width!=FRAME_WIDTH || capture_record_height!=FRAME_HEIGHT)
    $fatal(1,"Source geometry record mismatch");
  end else bad_records=bad_records+1;
 end
 if(a_source.sample_valid && a_source.sample_sof) begin
  sof_checks=sof_checks+1;grid_clock[a_source.sample_frame_id]=shared_ms;
  if(a_source.sample_timestamp_ms!==expected_stamp[a_source.sample_frame_id])
   $fatal(1,"Grid SOF overwrote first-DE timestamp");
  if(shared_ms!=a_source.sample_timestamp_ms) stamp_edges=stamp_edges+1;
 end
 if(a_source.sample_valid && a_source.sample_eof) begin
  eof_checks=eof_checks+1;eof_clock[a_source.sample_frame_id]=shared_ms;
  if(!capture_record_valid || !capture_record_complete ||
     capture_record_frame_id!==a_source.sample_frame_id ||
     a_source.sample_timestamp_ms!==expected_stamp[a_source.sample_frame_id])
    $fatal(1,"Delayed EOF used new VS frame metadata or an invalid source frame");
 end
end
task pixels(input integer seq,input integer mode);
 integer x,y,width,height;
 begin
  // At this edge the next clock consumes a DIFFERENT coherent time snapshot.
  // Capture must use the old first-DE time; grid SOF observes the new time.
  if(seq==0) begin
   @(negedge vclk);
   while(!(dut.control.clock_service.snap_valid &&
           dut.control.clock_service.snapshot!=shared_ms)) @(negedge vclk);
  end else @(negedge vclk);
  height=FRAME_HEIGHT+(mode==2?-1:(mode==3?1:0));
  for(y=0;y<height;y=y+1) begin
   width=FRAME_WIDTH-((mode==1 && y==0)?1:0);
   for(x=0;x<width;x=x+1) begin
    pixel_de=1;
    // Sampled coordinates produce the exact C24 self-test when source ID=0.
    // Unsampled pixels differ so a wrong sampling position cannot pass.
    if(x%STEP_X==0 && y%STEP_Y==0)
     pixel_gray=8'((y/STEP_Y*96+x/STEP_X)*17+seq+1);
    else pixel_gray=8'(x*3+y*5+seq+73);
    if(x==0 && y==0) expected_stamp[seq]=shared_ms;
    @(negedge vclk);
   end
   pixel_de=0;repeat(3) @(negedge vclk);
  end
  pixel_de=0;repeat(4) @(negedge vclk);
  if(mode==0 && !a_source.capture.sampler.pending_last)
   $fatal(1,"Valid physical frame did not retain its final grid pixel until VS");
 end
endtask
task boundary;
 begin
  @(negedge vclk);pixel_vs=1;pixel_de=0;
  repeat(4) @(negedge vclk);pixel_vs=0;
  repeat(3) @(negedge vclk);
 end
endtask
task malformed(input integer seq,input integer mode);
 integer before_commits;
 begin
  before_commits=a_commits;pixels(seq,mode);boundary();
  repeat(100) @(negedge vclk);
  if(event_write!=event_read || a_commits!=before_commits ||
     last_record_id!=seq || last_record_complete)
   $fatal(1,"Malformed source frame reached DDR or complete record");
 end
endtask
'''

SCENARIO=r'''
reg a,b,tmp;reg [31:0] ga,gb,old_ga,tmpgen;
initial begin
 #1;rst_n=0;#(VIDEO_HALF*4+23);rst_n=1;
 // Unframed active pixels, including startup before time becomes valid, must
 // not manufacture a frame. The first usable source frame begins at a VS.
 repeat(20) begin @(negedge vclk);pixel_de=1;pixel_gray=8'ha5;end
 @(negedge vclk);pixel_de=0;wait(a_source.capture_rst_n);
 repeat(12) @(negedge vclk);
 if(a_commits || capture_source_frames || req_valid) $fatal(1,"Startup pixels accepted without a valid VS/time");
 if(!capture_config_valid) $fatal(1,"Valid 96x54 capture configuration rejected");
 boundary();
 if(!EXTENDED) begin
  pixels(0,0);
  if(a_commits || event_write || states) $fatal(1,"Full-HD frame published before next VS");
  boundary();collect(0,0,a,ga);
  control(5,a,ga,0);apb(0,16'h48,0);
  if(apb_value!==expected_stamp[0]) $fatal(1,"Full-HD APB first-DE timestamp mismatch");
  control(3,a,ga,0);read_image(0,a?32'h4000:32'h1000);control(4,a,ga,0);
  if(record_checks!=1 || eof_checks!=1 || stamp_edges!=1 || time_wraps==0)
   $fatal(1,"Missing full-HD source/EOF/time boundary coverage");
  if(core_protocol_error || cpu_adapter_error || cpu_rejected || protocol_error)
   $fatal(1,"Full-HD fabric error");
  $display("PASS tb_c2_video geometry=%0dx%0d step=%0dx%0d bytes=9216 full_HD=1 success=1 records=%0d delayed_eof=%0d first_DE_edges=%0d time_wraps=%0d checks=%0d first_source_DE_timestamp A_capture sampler mailbox C2_DDR CPU_AXI APB synthetic_pixels_no_camera",FRAME_WIDTH,FRAME_HEIGHT,STEP_X,STEP_Y,record_checks,eof_checks,stamp_edges,time_wraps,checks);
  $finish;
 end
 fork
  begin wait(a_commits!=0);for(t0=0;t0<30;t0=t0+1) begin repeat(1000) @(posedge clk);write_burst(0,32'h10000+t0*256,4,t0,0);read_burst(0,32'h10000+t0*256,4,t0,0);end end
  begin wait(a_commits!=0);for(t1=0;t1<30;t1=t1+1) begin repeat(1000) @(posedge clk);write_burst(1,32'h18000+t1*256,4,100+t1,0);read_burst(1,32'h18000+t1*256,4,100+t1,0);end end
  begin wait(a_commits!=0);for(t2=0;t2<30;t2=t2+1) begin repeat(1000) @(posedge clk);write_burst(2,t2*256,4,200+t2,0);read_burst(2,t2*256,4,200+t2,0);end end
  begin
   pixels(0,0);
   if(a_commits || event_write || states) $fatal(1,"Frame published before validation at next VS");
   boundary();
   // Capture the next source frame while frame0 is being moved to DDR.
   pixels(1,0);boundary();
   collect(0,0,a,ga);old_ga=ga;collect(1,0,b,gb);
   if(a==b || states!==4'b1010) $fatal(1,"Two complete source frames did not occupy independent DDR slots");
   pixels(2,0);boundary();collect(2,1,tmp,tmpgen);
  end
 join
 control(5,a,ga,0);
 apb(0,16'h48,0);if(apb_value!==expected_stamp[0]) $fatal(1,"APB source timestamp mismatch");
 control(3,a,ga,0);read_image(0,a?32'h4000:32'h1000);control(4,a,ga,0);
 malformed(3,1);
 pixels(4,0);boundary();collect(4,0,a,ga);
 if(ga==old_ga) $fatal(1,"Generation did not advance after capture recovery");
 control(3,b,gb,0);control(4,b,gb,0);
 control(3,a,ga,0);read_image(4,a?32'h4000:32'h1000);control(4,a,ga,0);
 malformed(5,2);malformed(6,3);
 pixels(7,0);boundary();collect(7,0,tmp,tmpgen);
 control(3,tmp,tmpgen,0);read_image(7,tmp?32'h4000:32'h1000);control(4,tmp,tmpgen,0);
 if(capture_format_errors!=3 || a_faults) $fatal(1,"Malformed frame counters/source transport mismatch");
 // Common reset in the middle of active source capture: no ghost sample/lease.
 @(negedge vclk);pixel_de=1;pixel_gray=8'h5c;expected_stamp[8]=shared_ms;
 repeat(20) @(negedge vclk);
 @(negedge clk);rst_n=0;pixel_de=0;pixel_vs=0;
 repeat(5) @(negedge clk);rst_n=1;
 wait(a_source.capture_rst_n);repeat(8) @(negedge vclk);
 if(states || delivered_valid || a_commits || capture_source_frames) $fatal(1,"Ghost capture/DDR epoch after common reset");
 boundary();pixels(0,0);boundary();collect(0,0,tmp,tmpgen);
 control(3,tmp,tmpgen,0);read_image(0,tmp?32'h4000:32'h1000);control(4,tmp,tmpgen,0);
 if(images_ok!=5 || images_error!=1 || bad_records!=3 || eof_checks!=6 ||
    record_checks!=9 || stamp_edges<2 || time_wraps==0 || traffic_during_image==0)
  $fatal(1,"Missing coverage images=%0d bad=%0d records=%0d eof=%0d edges=%0d wraps=%0d concurrent=%0d",images_ok,bad_records,record_checks,eof_checks,stamp_edges,time_wraps,traffic_during_image);
 if(core_protocol_error || cpu_adapter_error || cpu_rejected || protocol_error)
  $fatal(1,"Unexpected fabric/adapter protocol error");
 $display("PASS tb_c2_video geometry=%0dx%0d step=%0dx%0d bytes=9216 success=%0d busy=%0d malformed=%0d records=%0d delayed_eof=%0d first_DE_edges=%0d time_wraps=%0d concurrent_requests=%0d checks=%0d first_source_DE_timestamp A_capture sampler mailbox C2_DDR CPU_AXI APB common_reset synthetic_pixels_no_camera",FRAME_WIDTH,FRAME_HEIGHT,STEP_X,STEP_Y,images_ok,images_error,bad_records,record_checks,eof_checks,stamp_edges,time_wraps,traffic_during_image,checks);
 $finish;
end
initial begin #1000000000;$fatal(1,"Full pixel capture timeout");end
endmodule
'''


def main():
    s=(P/'sim/tb_c2_a_bridge.sv').read_text(encoding='utf-8-sig')
    s=s.replace('module tb_c2_a_bridge #(parameter MEM_HALF=5,parameter VIDEO_HALF=7);',
                'module tb_c2_video #(parameter MEM_HALF=5,VIDEO_HALF=7,FRAME_WIDTH=1920,FRAME_HEIGHT=1080,STEP_X=20,STEP_Y=20,EXTENDED=1);')
    old='reg sample_valid=0,sample_sof=0,sample_eof=0,sample_abort=0;\nreg [7:0] sample_gray=0;reg [31:0] sample_frame_id=0;'
    assert old in s
    s=s.replace(old,'reg pixel_vs=0,pixel_de=0;reg [7:0] pixel_gray=0;\n')
    s=s.replace('sample_timestamp_ms','shared_ms')
    at=s.index('c2_a_image_source a_source(')
    s=s[:at]+'''wire capture_config_valid,capture_record_valid,capture_record_complete;
wire [31:0] capture_record_frame_id,capture_record_timestamp_ms,capture_source_frames,capture_format_errors;
wire [15:0] capture_record_width,capture_record_height;
'''+s[at:]
    s=s.replace('c2_a_image_source a_source(','''c2_a_video_source #(.FRAME_WIDTH(FRAME_WIDTH),.FRAME_HEIGHT(FRAME_HEIGHT),.STEP_X(STEP_X),.STEP_Y(STEP_Y)) a_source(''')
    old='''.sample_valid(sample_valid),.sample_sof(sample_sof),.sample_eof(sample_eof),.sample_abort(sample_abort),
.sample_gray(sample_gray),.sample_frame_id(sample_frame_id),.shared_ms(shared_ms),'''
    assert old in s
    s=s.replace(old,'''.pixel_vs(pixel_vs),.pixel_de(pixel_de),.pixel_gray(pixel_gray),
.shared_now_ms(shared_ms),.shared_time_valid(sample_time_valid),
.capture_config_valid(capture_config_valid),.capture_record_valid(capture_record_valid),.capture_record_complete(capture_record_complete),
.capture_record_frame_id(capture_record_frame_id),.capture_record_timestamp_ms(capture_record_timestamp_ms),
.capture_record_width(capture_record_width),.capture_record_height(capture_record_height),
.capture_source_frames(capture_source_frames),.capture_format_errors(capture_format_errors),''')
    s=s.replace('.TIME_CLOCK_HZ(1000000)',".TIME_CLOCK_HZ(10000000),.TIME_INITIAL_MS(32'hfffffffc)")
    s=s.replace('!a_source.active','!a_source.image.active')
    s=s.replace('((index-2016)*17+frame)','((index-2016)*17+frame+1)')
    start=s.index('task send_frame');end=s.index('task collect',start)
    s=s[:start]+DRIVER+'\n'+s[end:]
    s=s.replace('if(seq==1)','if(seq==0)').replace('a_c2_frame1.gray','a_c2_video_frame0.gray')
    s=s.replace('integer n,fd;','integer n,fd,meta;')
    marker='if(seq==0) $fclose(fd);'
    assert marker in s
    s=s.replace(marker,'''if(seq==0) begin
      $fclose(fd);meta=$fopen("a_c2_video_frame0.json","w");
      $fwrite(meta,"{\\"synthetic\\":true,\\"source\\":\\"GRAY8_VS_DE_simulation\\",\\"source_frame_id\\":0,\\"width\\":%0d,\\"height\\":%0d,\\"step_x\\":%0d,\\"step_y\\":%0d,\\"timestamp_ms\\":%0d,\\"grid_sof_observed_ms\\":%0d,\\"completion_shared_ms\\":%0d,\\"timestamp_origin\\":\\"first_source_DE\\",\\"raw_fnv\\":\\"%08x\\"}\\n",FRAME_WIDTH,FRAME_HEIGHT,STEP_X,STEP_Y,delivered[95:64],grid_clock[0],eof_clock[0],checksum(0));
      $fclose(meta);
     end''')
    start=s.index('reg a,b,tmp;')
    s=s[:start]+SCENARIO
    (P/'sim/tb_c2_video.sv').write_text(s,encoding='utf-8')
    print('Prepared full source-pixel A capture -> C2/DDR/APB/CPU-readback test.')


if __name__=='__main__':main()
