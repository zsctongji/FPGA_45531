from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parents[1];S=R/'team_work/03_ai_soc/c9_live/camera_geometry';B=R/'build/c9_native_edges_tests_20261103'
def main():
 B.mkdir(exist_ok=True);iv=R/'tools/iverilog/bin/iverilog.exe';exe=B/'test.vvp';files=[S/'c9_native_edges.sv',S/'tb_native_edges.sv']
 q=subprocess.run([str(iv),'-g2012','-s','tb_native_edges','-o',str(exe),*[str(p) for p in files]],capture_output=True,text=True);assert q.returncode==0,q.stderr
 q=subprocess.run([str(iv.with_name('vvp.exe')),str(exe)],capture_output=True,text=True);assert q.returncode==0 and 'PASS tb_native_edges' in q.stdout,q.stdout+q.stderr
 (B/'test.log').write_text(q.stdout+q.stderr);report=dict(status='PASS',hardware_accessed=False,evidence=q.stdout,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [*files,Path(__file__)]})
 (R/'logs/c9_native_edges_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(q.stdout)
if __name__=='__main__':main()
