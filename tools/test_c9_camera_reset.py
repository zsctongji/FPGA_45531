"""Red/green on the exact reset/configuration fragment of the actual top."""
from pathlib import Path
import hashlib,json,re,subprocess
from prepare_c9_linebuffer_reset import B,modified_top
R=Path(__file__).resolve().parents[1];O=R/'build/c9_camera_reset_tests_20261103'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 O.mkdir(exist_ok=True);source=B/'soc_physical_top.sv';original=source.read_text();iv=R/'tools/iverilog/bin/iverilog.exe';cases=[];generated=[]
 for fixed in [False,True]:
  t=modified_top(original) if fixed else original
  counter=re.search(r'reg \[12:0\] config_delay;.*?config_delay\+1\x27b1;',t,re.S).group()
  assign=re.search(r'assign o_cam_rst_p=.*?;',t).group()
  bench='''`timescale 1ns/1ps
module tb_camera_reset;
 reg CLK_5M=0,root_reset_n=0,soc_reset=1;always #5 CLK_5M=~CLK_5M;
 wire camera_reset_n=root_reset_n && !soc_reset;wire o_cam_rst_p;
'''+counter+'\n'+assign+'''
 initial begin
  repeat(3)@(negedge CLK_5M);root_reset_n=1;repeat(10)@(negedge CLK_5M);
  if(!o_cam_rst_p || config_delay!=0)$fatal(1,"Camera/config started while CSI held reset");
  soc_reset=0;repeat(4098)@(negedge CLK_5M);
  if(o_cam_rst_p || !config_delay[12])$fatal(1,"Config delay/release failed");
  soc_reset=1;#1;if(!o_cam_rst_p || config_delay!=0)$fatal(1,"SoC reset did not reinitialize camera");
  soc_reset=0;repeat(4098)@(negedge CLK_5M);if(!config_delay[12])$fatal(1,"Restart failed");
  root_reset_n=0;#1;if(!o_cam_rst_p || config_delay!=0)$fatal(1,"Root reset failed");
  $display("PASS tb_camera_reset hold_until_CSI_ready full_delay SoC_and_root_restart");$finish;
 end
endmodule
'''
  name='fixed' if fixed else 'red_original';f=O/(name+'.sv');f.write_text(bench,newline='\n');generated.append(f);exe=O/(name+'.vvp')
  q=subprocess.run([str(iv),'-g2012','-s','tb_camera_reset','-o',str(exe),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  q=subprocess.run([str(iv.with_name('vvp.exe')),str(exe)],capture_output=True,text=True);out=q.stdout+q.stderr;(O/(name+'.log')).write_text(out)
  assert (q.returncode==0 and 'PASS tb_camera_reset' in out) if fixed else (q.returncode!=0 and 'Camera/config started while CSI held reset' in out),out
  cases.append(dict(fixed=fixed,returncode=q.returncode,evidence=out));print(name+': '+out.splitlines()[0])
 files=[Path(__file__),R/'tools/prepare_c9_linebuffer_reset.py',source]
 report=dict(status='PASS',hardware_accessed=False,scope='Extracted actual top reset/configuration fragment; sensor/MIPI analog behavior not simulated.',cases=cases,source_sha256={p.relative_to(R).as_posix():sha(p) for p in files},generated_sha256={p.relative_to(R).as_posix():sha(p) for p in generated})
 (R/'logs/c9_camera_reset_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
