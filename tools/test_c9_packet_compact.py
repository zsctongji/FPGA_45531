"""Packet observer regression, no hardware access."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parents[1];S=R/'team_work/03_ai_soc/c9_live/camera_geometry';B=R/'build/c9_packet_compact_tests_20261103'
def main():
 B.mkdir(exist_ok=True);files=[S/'c9_packet_probe_compact.sv',S/'tb_packet_compact.sv'];iv=R/'tools/iverilog/bin/iverilog.exe'
 q=subprocess.run([str(iv),'-g2012','-Wall','-s','tb_packet_compact','-o',str(B/'test.vvp'),*[str(p) for p in files]],capture_output=True,text=True,timeout=30);assert q.returncode==0,q.stderr
 q=subprocess.run([str(iv.with_name('vvp.exe')),str(B/'test.vvp')],capture_output=True,text=True,timeout=30)
 out=q.stdout+q.stderr;(B/'test.log').write_text(out);assert q.returncode==0 and 'PASS tb_packet_compact' in out,out
 report=dict(status='PASS',board_test_passed=False,hardware_accessed=False,evidence=out,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [*files,Path(__file__)]})
 (R/'logs/c9_packet_compact_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n');print(out)
if __name__=='__main__':main()
