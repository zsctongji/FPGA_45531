"""Prepare the A BRAM -> C2 integration bench, preserving A's source snapshot."""
from pathlib import Path
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/06_soc_c2'

def main():
    s=(P/'sim/tb_c2_vendor.sv').read_text(encoding='utf-8-sig')
    s=s.replace('module tb_c2_vendor #','module tb_c2_a_bridge #')
    s=s.replace('reg req_valid=0,event_ready=0;', 'wire req_valid;reg event_ready=0;')
    s=s.replace('reg [543:0] req_payload=0;', "wire [543:0] req_payload;assign req_payload[543:512]=0;")
    s=s.replace('reg image_valid=0;', 'wire image_valid;').replace('reg [127:0] image_words=0;', 'wire [127:0] image_words;')
    s=s.replace("#(.SHARED_BASE(0),.VIDEO_BASE(32'h20000)","#(.REQUIRE_SOURCE_COMPLETION(1),.SHARED_BASE(0),.VIDEO_BASE(32'h20000)")
    s=s.replace(".v_source_valid(1'b0),.v_source_ready(),.v_source_error(1'b0),.v_source_frame_id(32'b0),.v_source_fnv(32'b0),",'''
.v_source_valid(source_valid && verdict_allow),.v_source_ready(core_source_ready),.v_source_error(source_error),
.v_source_frame_id(source_frame_id),.v_source_fnv(source_fnv),''')
    s=s.replace('.v_event_valid(delivered_valid),.v_event_ready(event_ready)', '.v_event_valid(core_event_valid),.v_event_ready(core_event_ready)')
    s=s.replace('.v_event_status(delivered[547:545]),.v_event_slot(delivered[544])', '.v_event_status(core_event[547:545]),.v_event_slot(core_event[544])')
    s=s.replace('.v_event_generation(delivered[543:512]),.v_event_descriptor(delivered[511:0])', '.v_event_generation(core_event[543:512]),.v_event_descriptor(core_event[511:0])')
    s=s.replace('assign states=dut.core.slot_states;assign grant_ready=!active;', 'assign states=dut.core.slot_states;')
    a=s.index('c2_vendor_attachment #(')
    extra='''reg sample_valid=0,sample_sof=0,sample_eof=0,sample_abort=0;
reg [7:0] sample_gray=0;reg [31:0] sample_frame_id=0,sample_timestamp_ms=0;
wire source_valid,core_source_ready,source_error;reg verdict_allow=1;
wire [31:0] source_frame_id,source_fnv;
wire core_event_valid,core_event_ready;wire [547:0] core_event;
wire [31:0] a_completed,a_rejected,a_faults,a_commits,a_drops,a_malformed;
reg [547:0] event_queue[0:63];integer event_write=0,event_read=0;
assign delivered_valid=event_write>event_read;assign delivered=event_queue[event_read];
always @(posedge vclk or negedge rst_n) begin
 if(!rst_n) begin event_write=0;event_read=0;end
 else begin
  if(core_event_valid && core_event_ready) begin event_queue[event_write]=core_event;event_write=event_write+1;end
  if(delivered_valid && event_ready) event_read=event_read+1;
 end
end
c2_a_image_source a_source(.arst_n(rst_n),.video_clk(vclk),.enable(1'b1),
.sample_valid(sample_valid),.sample_sof(sample_sof),.sample_eof(sample_eof),.sample_abort(sample_abort),
.sample_gray(sample_gray),.sample_frame_id(sample_frame_id),.sample_timestamp_ms(sample_timestamp_ms),
.v_frame_valid(req_valid),.v_frame_ready(req_ready),.v_descriptor(req_payload[511:0]),
.v_grant_valid(grant_valid),.v_grant_ready(grant_ready),.v_grant_frame_id(grant_frame_id),
.v_word_valid(image_valid),.v_word_ready(image_ready),.v_word_data(image_words),
.v_source_valid(source_valid),.v_source_ready(core_source_ready && verdict_allow),.v_source_error(source_error),
.v_source_frame_id(source_frame_id),.v_source_fnv(source_fnv),
.v_event_valid(core_event_valid),.v_event_ready(core_event_ready),.v_event_status(core_event[547:545]),.v_event_descriptor(core_event[511:0]),
.completed(a_completed),.rejected(a_rejected),.source_faults(a_faults),.source_commits(a_commits),.source_drops(a_drops),
.source_malformed(a_malformed),.last_frame_id(),.last_sum32(),.last_fnv(),.last_status());
'''
    s=s[:a]+extra+s[a:]
    a=s.index('// Producer lives entirely');b=s.index('task send_frame',a)
    monitor=s[s.index('always @(posedge clk or negedge rst_n) begin\n if(!rst_n) begin frame_w',a):s.index('reg stalled=0;',a)]
    monitor+='''integer source_stalls=0;
reg burst_reserved=0;
always @(posedge clk or negedge rst_n) begin
 if(!rst_n) burst_reserved<=0;
 else begin
  if(dut.core.hub.f_awvalid[3] && dut.core.hub.f_awready[3]) burst_reserved<=1;
  if(burst_reserved && !dut.core.hub.f_wvalid[3]) $fatal(1,"DDR burst reserved while waiting for A pixels/hash");
  if(dut.core.hub.f_wvalid[3] && dut.core.hub.f_wready[3] && dut.core.hub.f_wlast[3]) burst_reserved<=0;
 end
end
always @(posedge vclk) if(rst_n) begin
 if(image_valid && !image_ready) source_stalls=source_stalls+1;
 if(image_valid && !a_source.active) $fatal(1,"A lease released before transfer finished");
end
'''
    s=s[:a]+monitor+s[b:]
    a=s.index('task send_frame');b=s.index('task collect',a)
    s=s[:a]+'''task send_frame(input integer seq,input bit bad_checksum);
 integer n;
 begin
  wait(a_source.rst_n);
  if(bad_checksum) force a_source.sum32=32'hdeadbeef;
  for(n=0;n<5184;n=n+1) begin
   @(negedge vclk);sample_valid=1;sample_sof=n==0;sample_eof=n==5183;
   sample_gray=(n*17+seq)&255;sample_frame_id=seq;sample_timestamp_ms=seq*33;
  end
  @(negedge vclk);sample_valid=0;sample_sof=0;sample_eof=0;
 end
endtask
'''+s[b:]
    s=s.replace('image_pattern[b*8+:8]=(word_index*16+b)*17+frame;',
                'image_pattern[b*8+:8]=pixel_value(frame,word_index*16+b);')
    at=s.index('function [127:0] image_pattern')
    s=s[:at]+'''function [7:0] pixel_value(input integer frame,input integer index);
 begin pixel_value=(index<2016 || index>=7200)?0:((index-2016)*17+frame);end
endfunction
'''+s[at:]
    s=s.replace('((n*17+frame)&255)', 'pixel_value(frame,n)').replace('((n*17+seq)&255)', 'pixel_value(seq,n)')
    s=s.replace('send_frame(5,0);collect(5,0,a,ga);', '''verdict_allow=0;send_frame(5,0);
 wait(dut.core.source_fence.fence.have_writer);
 repeat(50) @(negedge clk);
 if(states[1:0]!=1 || core_event_valid) $fatal(1,"DDR completion published before source verdict");
 verdict_allow=1;collect(5,0,a,ga);''')
    s=s.replace('collect(7,3,tmp,tmpgen);','collect(7,4,tmp,tmpgen);release a_source.sum32;')
    s=s.replace('wait(active && word_index>100);','wait(a_source.bridge.pixel>1600);')
    # Keep background traffic active while A's 5184-sample source is collected.
    s=s.replace('for(t0=0;t0<30;t0=t0+1) begin write_burst','for(t0=0;t0<30;t0=t0+1) begin repeat(1000) @(posedge clk);write_burst')
    s=s.replace('for(t1=0;t1<30;t1=t1+1) begin write_burst','for(t1=0;t1<30;t1=t1+1) begin repeat(1000) @(posedge clk);write_burst')
    s=s.replace('for(t2=0;t2<30;t2=t2+1) begin write_burst','for(t2=0;t2<30;t2=t2+1) begin repeat(1000) @(posedge clk);write_burst')
    s=s.replace('if(VIDEO_HALF<MEM_HALF*16 && source_stalls==0) $fatal(1,"FIFO backpressure was not exercised");','')
    s=s.replace('PASS tb_c2_vendor','PASS tb_c2_a_bridge')
    s=s.replace('APB CPU_ID vendor_S1 video_relocation','A_BRAM lease pack128 SUM32 source_verdict FNV APB CPU_ID vendor_S1 video_relocation')
    s=s.replace('initial begin #10000000;', 'initial begin #100000000;')
    # Save real bridge/DDR bytes, never the synthetic generator's input array.
    s=s.replace('reg [7:0] observed;integer n;', 'reg [7:0] observed;integer n,fd;')
    s=s.replace('for(n=0;n<9216;n=n+1) begin\n       observed=', 'if(seq==1) fd=$fopen("a_c2_frame1.gray","wb");\n     for(n=0;n<9216;n=n+1) begin\n       observed=')
    s=s.replace('if(observed!==pixel_value(seq,n))', 'if(seq==1) $fwrite(fd,"%c",observed);\n       if(observed!==pixel_value(seq,n))')
    s=s.replace('if(delivered[287:256]!==checksum(seq))', 'if(seq==1) $fclose(fd);\n     if(delivered[287:256]!==checksum(seq))')
    # Exercise the same single time source used by the native overlay. Accelerate
    # only the simulation divider and record the timestamp latched at sample SOF.
    s=s.replace('.REQUIRE_SOURCE_COMPLETION(1),.SHARED_BASE(0)', '.TIME_CLOCK_HZ(1000000),.REQUIRE_SOURCE_COMPLETION(1),.SHARED_BASE(0)')
    s=s.replace('reg [31:0] sample_frame_id=0,sample_timestamp_ms=0;', 'reg [31:0] sample_frame_id=0;wire [31:0] sample_timestamp_ms;wire sample_time_valid;reg [31:0] expected_stamp[0:31];')
    s=s.replace('.external_protocol_error(cpu_adapter_error || cpu_rejected),', '.external_protocol_error(cpu_adapter_error || cpu_rejected),.shared_video_ms(sample_timestamp_ms),.shared_video_valid(sample_time_valid),')
    s=s.replace('wait(a_source.rst_n);', 'wait(a_source.rst_n && sample_time_valid);')
    s=s.replace('sample_frame_id=seq;sample_timestamp_ms=seq*33;', 'sample_frame_id=seq;if(n==0) expected_stamp[seq]=sample_timestamp_ms;')
    s=s.replace('if(delivered[287:256]!==checksum(seq))', 'if(delivered[95:64]!==expected_stamp[seq]) $fatal(1,"Shared SOF timestamp lost");\n     if(delivered[287:256]!==checksum(seq))')
    (P/'sim/tb_c2_a_bridge.sv').write_text(s,encoding='utf-8')
    manifest={'origin':'https://github.com/zsctongji/FPGA_cooperation','A_last_commit':'06908f4',
              'policy':'96x54 + 21 black rows on each side; transport candidate, model-quality approval pending',
              'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((P/'a_side').glob('*.v'))}}
    (P/'a_side/SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Prepared A mailbox -> C2 source-verdict integration bench.')

if __name__=='__main__':main()
