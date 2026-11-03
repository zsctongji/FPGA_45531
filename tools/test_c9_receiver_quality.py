"""Prove startup status never releases data, and qualified errors stay fatal."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parents[1];S=R/'team_work/03_ai_soc/c9_live/camera_geometry';B=R/'build/c9_receiver_quality_tests_20261103'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 B.mkdir(exist_ok=True);iv=R/'tools/iverilog/bin/iverilog.exe';cases=[];generated=[]
 unit=(S/'tb_raw10_linebuffer.sv').read_text().replace('c9_raw10_linebuffer #','c9_raw10_linebuffer_quality #')
 unit=unit.replace('wire ov,oh,od,fault,armed;', '''reg [31:0] quality_debug=32'h8000;wire quality_fault,quality_ready;wire [3:0] quality_flags;
 c9_receiver_quality quality(clk,rst,run,armed,de,quality_debug | (transport?32'd4:32'd0),quality_fault,quality_ready,quality_flags);
 wire ov,oh,od,fault,armed;''')
 unit=unit.replace('vc,ppc,transport,','vc,ppc,quality_fault,quality_ready,')
 unit=unit.replace('  boundary();\n  case(CASE)',"  if(CASE==11 || CASE==12)quality_debug[16]=1;\n  boundary();\n  if(CASE==11)begin repeat(20)@(negedge clk);quality_debug[16]=0;end\n  case(CASE)")
 unit=unit.replace('0,9:begin','0,9,11:begin').replace('   10:begin vc=1;row(480,1);end','   10:begin vc=1;row(480,1);end\n   12:begin for(y=0;y<4;y=y+1)row(480,1);boundary();end')
 unit=unit.replace('CASE==0 || CASE==8 || CASE==9','CASE==0 || CASE==8 || CASE==9 || CASE==11')
 unit=unit.replace('  $display("PASS tb_raw10_linebuffer', '  if(CASE==12 && (got || vscount || !errors[0]))$fatal(1,"Persistent PHY error released data");\n  $display("PASS tb_raw10_linebuffer')
 test=B/'unit.sv';test.write_text(unit,newline='\n');generated.append(test)
 gate=B/'quality.sv';gate.write_text('''`timescale 1ns/1ps
module tb_quality;
 reg clk=0,rst=0,en=0,arm=0,de=0;always #5 clk=~clk;reg [31:0] dbg=32'h18000;
 wire fail,ready;wire [3:0] flags;c9_receiver_quality dut(clk,rst,en,arm,de,dbg,fail,ready,flags);
 initial begin
  repeat(3)@(negedge clk);rst=1;en=1;repeat(10)@(negedge clk);arm=1;repeat(100)@(negedge clk);
  if(ready || fail || !flags[0])$fatal(1,"Persistent startup PHY status qualified");
  dbg[16]=0;repeat(31)@(negedge clk);if(ready)$fatal(1,"Too short clean interval");
  repeat(2)@(negedge clk);if(!ready || fail)$fatal(1,"Clean qualification failed");
  dbg[16]=1;#1;if(!fail)$fatal(1,"New active PHY fault ignored");@(negedge clk);dbg[16]=0;
  if(!fail || !flags[1])$fatal(1,"Active PHY fault not sticky");
  rst=0;#1;rst=1;arm=0;dbg=32'h8004;repeat(3)@(negedge clk);if(!fail)$fatal(1,"Packet CRC ignored before qualification");
  $display("PASS tb_quality no_release_for_persistent_status exact_clean_wait new_error_sticky CRC_not_masked");$finish;
 end
endmodule
''',newline='\n');generated.append(gate)
 for case in [-1,*range(13)]:
  top='tb_quality' if case==-1 else 'tb_raw10_linebuffer';files=[S/'c9_receiver_quality.sv',gate] if case==-1 else [S/'c9_receiver_quality.sv',S/'c9_raw10_linebuffer_quality.sv',test]
  exe=B/f'test{case}.vvp';q=subprocess.run([str(iv),'-g2012','-s',top,*([f'-P{top}.CASE={case}'] if case>=0 else []),'-o',str(exe),*[str(p) for p in files]],capture_output=True,text=True);assert q.returncode==0,q.stderr
  q=subprocess.run([str(iv.with_name('vvp.exe')),str(exe)],capture_output=True,text=True,timeout=30);out=q.stdout+q.stderr;(B/f'test{case}.log').write_text(out);assert q.returncode==0 and 'PASS '+top in out,out
  cases.append(dict(case=case,evidence=out));print(out.splitlines()[0],flush=True)
 inputs=[Path(__file__),S/'c9_receiver_quality.sv',S/'c9_raw10_linebuffer_quality.sv',S/'tb_raw10_linebuffer.sv']
 m=dict(status='PASS',hardware_accessed=False,source_sha256={p.relative_to(R).as_posix():sha(p) for p in inputs},generated_sha256={p.relative_to(R).as_posix():sha(p) for p in generated},cases=cases)
 (R/'logs/c9_receiver_quality_tests_20261103.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
