"""Reproducible A-only tests; preserve the historical twelve-test baseline."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
build=root/'build/a_side'
build.mkdir(parents=True,exist_ok=True)
logs=root/'logs'
logs.mkdir(exist_ok=True)
record=dict(status='RUNNING',started=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            hardware_tested=False,tests=[],source_sha256={})
sources=['rtl/a_side_units.v','rtl/ai_frame_mailbox.v','rtl/video_a_capture.v','rtl/video_status_overlay.v','rtl/osd_font5x7.vh','rtl/video_grid_sampler.v']
sources += [str(p.relative_to(root)).replace('\\','/') for p in (root/'tools/a_side').glob('*.py')]
sources += ['tools/run_a_side.py']+['sim/'+p+'.sv' for p in ('tb_a_mailbox','tb_a_capture','tb_a_overlay','tb_a_pipeline')]
for name in sources:record['source_sha256'][name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
status=logs/'a_side_selftest.json'

def save():status.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
def run(name,command,cwd,expected=None):
    result=subprocess.run(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=180)
    (logs/(name+'.log')).write_text(result.stdout,encoding='utf-8')
    passed=result.returncode==0 and (expected is None or expected in result.stdout)
    record['tests'].append(dict(name=name,status='PASS' if passed else 'FAIL',exit_code=result.returncode,log=str(logs/(name+'.log'))))
    save();print(name,record['tests'][-1]['status'],flush=True)
    if not passed:raise RuntimeError(result.stdout[-5000:])

save()
try:
    run('a_python_tests',[sys.executable,'-X','utf8','-m','unittest','-v','test_a_side.py'],root/'tools/a_side')
    iv=root/'tools/iverilog/bin/iverilog.exe'
    vvp=iv.with_name('vvp.exe')
    for top,rtl in [('tb_a_mailbox',['ai_frame_mailbox']),('tb_a_capture',['video_a_capture','video_grid_sampler']),('tb_a_overlay',['video_status_overlay']),('tb_a_pipeline',['video_a_capture','video_grid_sampler','ai_frame_mailbox'])]:
        output=build/(top+'.vvp')
        run(top+'_compile',[str(iv),'-g2012','-Wall','-I',str(root/'rtl'),'-s',top,'-o',str(output),str(root/'sim'/(top+'.sv'))]+[str(root/'rtl'/(s+'.v')) for s in rtl],build)
        run(top,[str(vvp),str(output)],build,'PASS '+top)
    record['status']='PASS'
except Exception as exc:
    record['status']='FAIL';record['error']=str(exc);raise
finally:
    record['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
