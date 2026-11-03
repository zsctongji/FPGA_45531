"""Actual scanout/request CDC startup regression, including real missed-frame detection."""
from pathlib import Path
import argparse,hashlib,json,subprocess
R=Path(__file__).resolve().parents[1]
S=R/'team_work/03_ai_soc/c9_live/display_fix'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--baseline',action='store_true');a=ap.parse_args()
 scan=R/'projects/06_soc_c2/rtl/c2_video_scanout.sv' if a.baseline else S/'c2_video_scanout.sv'
 files=[scan,R/'projects/06_soc_c2/rtl/c2_cdc_mailbox.sv',S/'tb_scanout_startup.sv']
 out=R/'build/c9_scanout_startup_20261102';out.mkdir(exist_ok=True);cases=[]
 iv=R/'tools/iverilog/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 for mode in range(3):
  tag=('baseline' if a.baseline else 'fixed')+str(mode);binary=out/(tag+'.vvp')
  q=subprocess.run([str(iv),'-g2012','-Wall','-s','tb_scanout_startup',f'-Ptb_scanout_startup.START_MODE={mode}','-o',str(binary),*[str(p) for p in files]],capture_output=True,text=True,timeout=30)
  assert q.returncode==0,q.stdout+q.stderr
  q=subprocess.run([str(vvp),str(binary)],capture_output=True,text=True,timeout=30)
  log=q.stdout+q.stderr;(out/(tag+'.log')).write_text(log)
  cases.append(dict(mode=mode,returncode=q.returncode,evidence=log));print(log,flush=True)
 result=dict(status='PASS' if all(c['returncode']==0 for c in cases) else 'FAIL',baseline=a.baseline,board_test_passed=False,cases=cases,
  source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [*files,Path(__file__)]})
 (out/(('baseline' if a.baseline else 'fixed')+'_result.json')).write_text(json.dumps(result,indent=2)+'\n')
 return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
