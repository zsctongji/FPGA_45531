"""Reproduce the frozen camera binary, then replace only its timing/main unit.

Old objects are reused only after relinking them reproduces every byte of the
qualified baseline BIN. All outputs stay outside the frozen original app.
"""
from pathlib import Path
import hashlib,json,os,shlex,subprocess
R=Path(__file__).resolve().parents[1]
APP=R/'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/software/standalone/tinyml_c9'
B=R/'build/c9_camera_timefix_20261102';OUT=R/'firmware/c9_camera_timefix'
SRC=R/'team_work/03_ai_soc/c9_live/camera_time_fix/tinyml_main.cc'
G=R/'tools/riscv_gcc/13.4.0'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 original=json.loads((R/'firmware/c9_live_person_detect/BUILD_RECORD.json').read_text())
 for n,d in original['source_sha256'].items():assert sha(R/n)==d,n
 for n,d in original['artifacts'].items():assert sha(R/'firmware/c9_live_person_detect'/n)==d['sha256'],n
 tests=json.loads((R/'build/c9_time_progress_20261102/fixed_result.json').read_text());assert tests['status']=='PASS'
 assert tests['source_sha256'][SRC.relative_to(R).as_posix()]==sha(SRC)
 B.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
 env=os.environ.copy();env['PATH']=';'.join(str(G/p) for p in ['bin','libexec/gcc/riscv-none-elf/13.4.0','riscv-none-elf/bin'])+';'+env.get('PATH','')
 prefix=(G/'bin/riscv-none-elf-').as_posix()
 def run(args):
  q=subprocess.run([str(x) for x in args],cwd=APP,env=env,capture_output=True,text=True,timeout=180)
  with (B/'build.log').open('a') as f:f.write(subprocess.list2cmdline([str(x) for x in args])+'\n'+q.stdout+q.stderr)
  if q.returncode and 'cannot execute' in q.stderr and 'CreateProcess' in q.stderr and any(n in q.stderr for n in ['cc1.exe','cc1plus.exe','collect2.exe']):
   with (B/'build.log').open('a') as f:f.write('RETRY unchanged command after Windows compiler spawn failure\n')
   q=subprocess.run([str(x) for x in args],cwd=APP,env=env,capture_output=True,text=True,timeout=180)
   with (B/'build.log').open('a') as f:f.write(q.stdout+q.stderr)
  assert q.returncode==0,q.stdout+q.stderr
 old=[]
 for line in (APP/'build_ours/link.rsp').read_text().splitlines():
  args=shlex.split(line);assert len(args)==1;old.append(args[0])
 def link(main_obj,stem):
  args=[]
  for arg in old:
   if arg=='build_ours/out/src/main.o':arg=main_obj.as_posix()
   elif arg=='build_ours/tinyml_c9.elf':arg=(B/(stem+'.elf')).as_posix()
   else:arg=arg.replace('build_ours/tinyml_c9.map',(B/(stem+'.map')).as_posix())
   args.append(arg)
  rsp=B/(stem+'.rsp');rsp.write_text('\n'.join(subprocess.list2cmdline([a]) for a in args)+'\n')
  run([prefix+'g++.exe','@'+str(rsp)])
  run([prefix+'objcopy.exe','-O','binary',B/(stem+'.elf'),B/(stem+'.bin')])
 link(APP/'build_ours/out/src/main.o','baseline_relink')
 assert sha(B/'baseline_relink.bin')==original['artifacts']['tinyml_c9.bin']['sha256'],'Existing objects do not reproduce qualified baseline'
 version='c9time-'+hashlib.sha256((sha(SRC)+sha(Path(__file__))).encode()).hexdigest()[:16]
 (B/'main.cc').write_bytes(SRC.read_bytes())
 header=(APP/'src/c24_build_id.h').read_text().replace(original['version'],version)
 assert version in header;(B/'c24_build_id.h').write_text(header)
 commands=[shlex.split(l) for l in (APP/'build_ours/command_plan.txt').read_text().splitlines() if l.startswith(prefix)]
 candidates=[c for c in commands if '-c' in c and c[-1]=='src/main.cc'];assert len(candidates)==1
 command=candidates[0];command[0]+='.exe'
 command=[(B/'main.cc').as_posix() if a=='src/main.cc' else (B/'main.o').as_posix() if a=='build_ours/out/src/main.o' else a for a in command]
 run(command);link(B/'main.o','tinyml_c9_timefix')
 run([prefix+'objcopy.exe','-O','ihex',B/'tinyml_c9_timefix.elf',B/'tinyml_c9_timefix.hex'])
 artifacts={}
 for suffix in ['elf','bin','hex','map']:
  src=B/('tinyml_c9_timefix.'+suffix);dst=OUT/src.name;dst.write_bytes(src.read_bytes());artifacts[dst.name]=dict(bytes=dst.stat().st_size,sha256=sha(dst))
 sources=dict(original['source_sha256'])
 for p in [SRC,Path(__file__),B/'main.cc',B/'c24_build_id.h']:sources[p.relative_to(R).as_posix()]=sha(p)
 objects={str((APP/a).relative_to(R)).replace('\\','/'):sha(APP/a) for a in old if a.endswith('.o') and not Path(a).is_absolute()}
 report=dict(status='PASS_COMPILE_ONLY',version=version,entry='0x1000',board_test_passed=False,source_sha256=sources,artifacts=artifacts,
  baseline_manifest_sha256=sha(R/'firmware/c9_live_person_detect/BUILD_RECORD.json'),baseline_relink_sha256=sha(B/'baseline_relink.bin'),reused_object_sha256=objects,
  controlled_change='Fresh shared-time read after snapshot UART output; original 5..100ms bounds retained',fpga_changed=False)
 (OUT/'BUILD_RECORD.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['source_sha256','reused_object_sha256']},indent=2))
if __name__=='__main__':main()
