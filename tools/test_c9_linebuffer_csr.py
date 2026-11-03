"""Startup AXI model and unchanged rejection/order tests for CSR-gated variant."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parents[1];S=R/'team_work/03_ai_soc/c9_live/camera_geometry';B=R/'build/c9_linebuffer_csr_tests_20261103'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 B.mkdir(exist_ok=True);iv=R/'tools/iverilog/bin/iverilog.exe';cases=[]
 bench=(S/'tb_raw10_linebuffer.sv').read_text().replace('c9_raw10_linebuffer #','c9_raw10_linebuffer_csr #')
 bench=bench.replace('if(CASE==9)begin de=1;','if(CASE==9)begin transport=1;de=1;').replace('de=0;if(armed || sent || od)','de=0;transport=0;if(armed || sent || od)')
 test=B/'unit.sv';test.write_text(bench,newline='\n')
 for mode in range(16):
  top='tb_csi_capture_gate' if mode<5 else 'tb_raw10_linebuffer';param='MODE' if mode<5 else 'CASE';v=mode if mode<5 else mode-5
  files=[S/'c9_csi_capture_gate.sv',S/'tb_csi_capture_gate.sv'] if mode<5 else [S/'c9_raw10_linebuffer_csr.sv',test]
  exe=B/f'test{mode}.vvp';q=subprocess.run([str(iv),'-g2012','-s',top,f'-P{top}.{param}={v}','-o',str(exe),*[str(p) for p in files]],capture_output=True,text=True,timeout=30);assert q.returncode==0,q.stderr
  q=subprocess.run([str(iv.with_name('vvp.exe')),str(exe)],capture_output=True,text=True,timeout=30);out=q.stdout+q.stderr;(B/f'test{mode}.log').write_text(out);assert q.returncode==0 and 'PASS '+top in out,out
  cases.append(dict(top=top,case=v,evidence=out));print(out.splitlines()[0],flush=True)
 files=[Path(__file__),S/'c9_csi_capture_gate.sv',S/'tb_csi_capture_gate.sv',S/'c9_raw10_linebuffer_csr.sv',S/'tb_raw10_linebuffer.sv']
 report=dict(status='PASS',hardware_accessed=False,encrypted_CSI_behavior_simulated=False,cases=cases,source_sha256={p.relative_to(R).as_posix():sha(p) for p in files},generated_sha256={test.relative_to(R).as_posix():sha(test)})
 (R/'logs/c9_linebuffer_csr_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
if __name__=='__main__':main()
