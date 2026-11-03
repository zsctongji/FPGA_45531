"""Actual sensor ROM/sequencer with mock transaction completion, red/green."""
from pathlib import Path
import hashlib,json,re,subprocess
from patch_c9_camera_stream_gate import patched
R=Path(__file__).resolve().parents[1];V=R/'build/c9_linebuffer_reset_image_20261103/vendor_a/rtl/cam_i2c_ctrl/i2c';B=R/'build/c9_camera_stream_gate_tests_20261103'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 B.mkdir(exist_ok=True);cases=[];generated=[];iv=R/'tools/iverilog/bin/iverilog.exe'
 sources=[V/n for n in ['i2c_master_reg_rom.v','i2c_master_reg_set.v','i2c_master_ctrl_top.v']]
 for fixed in [False,True]:
  folder=B/('fixed' if fixed else 'red');folder.mkdir(exist_ok=True);files=[]
  for name in ['i2c_master_reg_rom.v','i2c_master_reg_set.v']:
   text=(V/name).read_text();text=patched(name,text) if fixed else text;p=folder/name;p.write_text(text,newline='\n');files.append(p)
  ctrl=patched('i2c_master_ctrl_top.v',(V/'i2c_master_ctrl_top.v').read_text());assert 'DATA_LENGTH = 183' in ctrl and '.allow_stream(stream_sync[1])' in ctrl and 'async_reg="true"' in ctrl
  rom=files[0].read_text();entries=re.findall(r"^ROM\[8'h([0-9a-f]+)\]\s*=\s*\{16'h([0-9a-f]+),8'h([0-9a-f]+),1'b([01])\};",rom,re.M)
  assert len(entries)==(183 if fixed else 182)
  bench='''`timescale 1ns/1ps
module tb_stream_gate;
 reg clk=0,rst=0,allow=0;always #5 clk=~clk;
 wire wr,rd;wire [15:0] addr;wire [7:0] data,dev;reg wd=0,rr=0;
 integer writes=0,reads=0,streamons=0;reg [31:0] cycles=0;
 i2c_master_reg_set #(.DATA_LENGTH('''+('183' if fixed else '182')+'''),.I2C_DEVICE_ADDR(8'h60)) dut(.clk(clk),.rst_n(rst),.init_done(1'b1),.rd_done(rr),.wr_done(wd),.wr_en(wr),.rd_en(rd),.addr(addr),.dout(data),.dev_addr(dev)'''+(',.allow_stream(allow)' if fixed else '')+''');
 always @(posedge clk)begin
  wd<=wr;rr<=rd;cycles<=cycles+1;
  if(wr)begin writes=writes+1;if(addr==16'h0100 && data==1)begin
   if(!allow)$fatal(1,"Stream started before qualification");streamons=streamons+1;
  end end
  if(rd)reads=reads+1;
 end
 initial begin
  repeat(3)@(negedge clk);rst=1;repeat(3000)@(negedge clk);
  if(streamons || reads!=16 || writes!=166)$fatal(1,"Standby config/readback incomplete w=%0d r=%0d",writes,reads);
  allow=1;repeat(100)@(negedge clk);
  if(streamons!=1 || writes!=167 || reads!=16)$fatal(1,"Final stream-on/termination failed");
  $display("PASS tb_stream_gate all_configuration_and_16_reads_before_enable single_final_stream_on");$finish;
 end
endmodule
'''
  f=folder/'tb.sv';f.write_text(bench,newline='\n');files.append(f);generated.extend(files);exe=folder/'test.vvp'
  q=subprocess.run([str(iv),'-g2012','-s','tb_stream_gate','-o',str(exe),*[str(p) for p in files]],capture_output=True,text=True);assert q.returncode==0,q.stderr
  q=subprocess.run([str(iv.with_name('vvp.exe')),str(exe)],capture_output=True,text=True);out=q.stdout+q.stderr;(folder/'test.log').write_text(out)
  assert (q.returncode==0 and 'PASS tb_stream_gate' in out) if fixed else q.returncode!=0 and 'Stream started before qualification' in out,out
  cases.append(dict(fixed=fixed,evidence=out));print(out.splitlines()[0])
 files=[*sources,Path(__file__),R/'tools/patch_c9_camera_stream_gate.py']
 m=dict(status='PASS',hardware_accessed=False,sensor_electrical_behavior_simulated=False,cases=cases,source_sha256={p.relative_to(R).as_posix():sha(p) for p in files},generated_sha256={p.relative_to(R).as_posix():sha(p) for p in generated})
 (R/'logs/c9_camera_stream_gate_tests_20261103.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
