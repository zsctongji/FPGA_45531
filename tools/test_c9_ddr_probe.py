"""Verify actual USER2 RTL before using its observations on the board."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parents[1]
files=[R/'team_work/03_ai_soc/c9_live/debug/c9_ddr_probe.sv',R/'team_work/03_ai_soc/c9_live/debug/tb_c9_ddr_probe.sv']
out=R/'build/c9_ddr_probe_rtl';out.mkdir(exist_ok=True)
args=[str(R/'tools/iverilog/bin/iverilog.exe'),'-g2012','-s','tb_c9_ddr_probe','-o',str(out/'probe.vvp'),*[str(p) for p in files]]
text=''
for command in [args,[str(R/'tools/iverilog/bin/vvp.exe'),str(out/'probe.vvp')]]:
 p=subprocess.run(command,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
 text+=p.stdout.decode(errors='replace');assert p.returncode==0,text
assert 'PASS USER2 banks, CPU-reset independence, TAP isolation, running/stopped clock observation' in text
(out/'test.log').write_text(text)
record=dict(status='PASS',source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[Path(__file__)]},checks=['Four bank contents and cycling','Readable while application reset held','Unselected TAP cannot capture/advance','All four running clocks change phase','Stopped clocks do not change phase'])
(R/'logs/c9_ddr_probe_rtl.json').write_text(json.dumps(record,indent=2)+'\n');print(text)
