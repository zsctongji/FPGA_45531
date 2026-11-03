"""Exercise native-clock snapshots and the actual A capture interface."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'team_work/03_ai_soc/c9_live';B=ROOT/'build/c7_live_20261101/rtl_tests';B.mkdir(parents=True,exist_ok=True)
iv=ROOT/'tools/iverilog/bin/iverilog.exe'
sources=[*sorted((SRC/'rtl').glob('*.sv')),*sorted((SRC/'sim').glob('*.sv')),ROOT/'projects/06_soc_c2/rtl/c2_cdc_mailbox.sv',ROOT/'projects/06_soc_c2/a_side/video_a_capture.v',ROOT/'projects/06_soc_c2/a_side/video_grid_sampler.v']
record=dict(status='RUNNING',tests=[],source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[Path(__file__)]})
for top in ['tb_c9_control','tb_c9_pattern']:
 exe=B/(top+'.vvp');r=subprocess.run([str(iv),'-g2012','-Wall','-s',top,'-o',str(exe),*[str(p) for p in sources]],cwd=ROOT,capture_output=True,text=True)
 (B/(top+'_compile.log')).write_text(r.stdout+r.stderr)
 if r.returncode:print(r.stderr);raise SystemExit(1)
 r=subprocess.run([str(iv.with_name('vvp.exe')),str(exe)],cwd=ROOT,capture_output=True,text=True,timeout=30)
 (B/(top+'.log')).write_text(r.stdout+r.stderr);print(r.stdout,flush=True)
 record['tests'].append(dict(name=top,returncode=r.returncode,output=r.stdout))
record['status']='PASS' if all(x['returncode']==0 and 'PASS ' in x['output'] for x in record['tests']) else 'FAIL'
(ROOT/'logs/soc_live_rtl_tests.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if record['status']=='PASS' else 1)
