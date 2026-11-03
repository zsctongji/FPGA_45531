"""Offline-only C9 regression and evidence replay, retaining qualified reports.

No serial/JTAG/programmer entry point is called. Run from the original SDK tree.
Fresh reports go under logs/c9_pc_acceptance_*/; frozen root reports are restored
byte-for-byte after each existing test. Generated B/O paths are isolated where
the existing test exposes them. Physical acceptance is never inferred here.
"""
from pathlib import Path
import argparse, datetime, hashlib, importlib.util, json, os, shutil
import subprocess, sys, time, traceback

R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'tools'))

TESTS=[
 'test_c9_linebuffer','test_c9_linebuffer_csr','test_c9_receiver_quality',
 'test_c9_native_edges','test_c9_camera_reset','test_c9_camera_stream_gate',
 'test_c9_stage_chain',
 'test_c9_linebuffer_decode','test_c9_linebuffer_csr_decode',
 'test_c9_linebuffer_edges_decode','test_c9_linebuffer_reset_decode',
 'test_c9_linebuffer_stream_decode','test_c9_linebuffer_quality_decode',
 'test_c9_display_c2','test_c9_scanout_startup','test_c9_time_progress',
 'test_c9_uart_hex_format','test_c9_ddr_calibration','test_c9_probe_preflight']
REPLAYS=['report_c9_linebuffer_board','report_c9_linebuffer_csr_board',
 'report_c9_linebuffer_edges_board','report_c9_linebuffer_reset_board',
 'report_c9_linebuffer_stream_board','report_c9_linebuffer_quality_board']
VARIANTS=['nopack','display','sideband_seed3','stage_min','linebuffer',
 'linebuffer_csr','linebuffer_edges','linebuffer_reset','linebuffer_stream',
 'linebuffer_quality']

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

def worker(name,out):
 """Single existing test; capture reports and retain prior qualified bytes."""
 out.mkdir(parents=True,exist_ok=True)
 old={p:(p.read_bytes(),p.stat()) for p in (R/'logs').glob('*.json')}
 result=0
 try:
  script=R/'tools'/(name+'.py');sys.argv=[str(script)]
  spec=importlib.util.spec_from_file_location(name,script)
  mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  if name in ['test_c9_linebuffer','test_c9_linebuffer_csr',
              'test_c9_receiver_quality','test_c9_native_edges',
              'test_c9_camera_stream_gate','test_c9_stage_chain']:
   mod.B=R/'build'/out.parent.name/name;mod.B.mkdir(parents=True,exist_ok=True)
  if name=='test_c9_camera_reset':
   mod.O=R/'build'/out.parent.name/name;mod.O.mkdir(parents=True,exist_ok=True)
  value=mod.main();result=0 if value is None else value
 except BaseException:
  traceback.print_exc();result=1
 finally:
  fresh=[]
  for p in (R/'logs').glob('*.json'):
   if p not in old or p.stat().st_mtime_ns!=old[p][1].st_mtime_ns:
    target=out/p.name;shutil.copy2(p,target);fresh.append(target.relative_to(R).as_posix())
   if p in old and p.read_bytes()!=old[p][0]:
    p.write_bytes(old[p][0]);os.utime(p,ns=(old[p][1].st_atime_ns,old[p][1].st_mtime_ns))
  for rel in ['build/c9_scanout_startup_20261102/fixed_result.json',
              'build/c9_time_progress_20261102/fixed_result.json']:
   p=R/rel
   if p.exists() and name in ('test_c9_scanout_startup','test_c9_time_progress'):
    target=out/(name+'_result.json');shutil.copy2(p,target)
    fresh.append(target.relative_to(R).as_posix())
  write(out/'execution.json',dict(name=name,returncode=result,reports=fresh,
   script_sha256=sha(R/'tools'/(name+'.py')),hardware_accessed=False))
 return result

def identities():
 from c9_probe_image import select,select_current
 rows=[];pinned={}
 for variant in VARIANTS:
  image,audit=select(R,variant);a=json.loads(audit.read_text())
  rows.append(dict(variant=variant,image_sha256=sha(image),audit_sha256=sha(audit),
   setup_ns=a['timing']['setup']['minimum_slack_ns'],
   hold_ns=a['timing']['hold']['minimum_slack_ns']))
  for field in ['source_sha256','evidence_sha256']:
   for rel,digest in a[field].items():
    assert rel not in pinned or pinned[rel]==digest,rel
    pinned[rel]=digest
  pinned[audit.relative_to(R).as_posix()]=sha(audit)
 select_current(R)
 return rows,pinned

def handoff():
 mf=R/'logs/c9_linebuffer_handoff_20261103.json';m=json.loads(mf.read_text(encoding='utf-8'))
 d=Path(m['destination']);fail=[];files={v['path']:v['sha256'] for v in m['files']}
 latest=R/'logs/c9_pc_acceptance_handoff_20261103.json'
 if latest.exists():
  for v in json.loads(latest.read_text(encoding='utf-8'))['files']:files[v['path']]=v['sha256']
 for rel,digest in files.items():
  try: assert sha(R/rel)==digest==sha(d/rel)
  except (AssertionError,OSError): fail.append(rel)
 assert not fail,'Handoff mismatches: '+str(fail)
 q=subprocess.run(['git','diff','--check'],cwd=d,capture_output=True,text=True)
 assert q.returncode==0,q.stdout+q.stderr
 return dict(files=len(files),manifest_sha256=sha(mf),git_diff_check='PASS',
  latest_manifest_sha256=sha(latest) if latest.exists() else None)

def chain(out):
 old=R/'logs/c9_receiver_quality_chain_tests_20261103.json';m=json.loads(old.read_text())
 for field in ['source_sha256','generated_sha256']:
  for rel,digest in m[field].items():assert sha(R/rel)==digest,rel
 bench=R/'build/c9_receiver_quality_tests_20261103/chain.sv'
 sources=[bench]+[R/rel for rel in m['source_sha256'] if not rel.endswith('/green_chain.sv')]
 iv=R/'tools/iverilog/bin/iverilog.exe';folder=R/'build'/out.name/'quality_isp_chain';folder.mkdir(parents=True)
 rows=[]
 for mode,phase in [(0,0),(0,3),(1,0),(1,3)]:
  tag=f'mode{mode}_phase{phase}';binary=folder/(tag+'.vvp')
  c=[str(iv),'-g2012','-s','tb_linebuffer_chain',f'-Ptb_linebuffer_chain.MODE={mode}',
     f'-Ptb_linebuffer_chain.PHASE={phase}','-o',str(binary),*[str(p) for p in sources]]
  q=subprocess.run(c,capture_output=True,text=True,timeout=45);assert q.returncode==0,q.stderr
  q=subprocess.run([str(iv.with_name('vvp.exe')),str(binary)],capture_output=True,text=True,timeout=60)
  log=q.stdout+q.stderr;(out/(tag+'.log')).write_text(log,encoding='utf-8')
  assert q.returncode==0 and 'PASS tb_linebuffer_chain' in log and 'complete_records=3' in log,log
  rows.append(dict(mode=mode,phase_ns=phase,passed=True,log=tag+'.log'))
 return dict(status='PASS',cases=rows,source_report_sha256=sha(old),hardware_accessed=False)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--worker');ap.add_argument('--out',type=Path)
 ap.add_argument('--resume',type=Path);ap.add_argument('--await-worker-pid',type=int);a=ap.parse_args()
 if a.worker:
  assert a.worker in TESTS+REPLAYS
  return worker(a.worker,a.out)
 os.chdir(R)
 out=a.resume.resolve() if a.resume else R/'logs'/('c9_pc_acceptance_'+datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S'))
 if not a.resume:out.mkdir()
 assert out.is_relative_to((R/'logs').resolve())
 report=json.loads((out/'result.json').read_text()) if a.resume else dict(status='RUNNING',started=datetime.datetime.now().astimezone().isoformat(),
  hardware_accessed=False,flash_written=False,ddr_parameters_changed=False,
  real_camera_verified=False,board_acceptance_passed=False,steps=[])
 failures=[v['name'] for v in report['steps'] if v['returncode']!=0]
 def save():write(out/'result.json',report)
 save();print('ACCEPTANCE_DIR='+str(out),flush=True)
 try:
  if a.await_worker_pid:
   # Preserve an already-running long full-HD test when replacing its supervisor.
   # Open only a synchronization handle; never signal or terminate the worker.
   import ctypes
   k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p
   k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
   k.CloseHandle.argtypes=[ctypes.c_void_p]
   handle=k.OpenProcess(0x00100000,False,a.await_worker_pid)
   if handle:
    print('WAIT existing offline worker '+str(a.await_worker_pid),flush=True)
    deadline=time.monotonic()+7200
    try:
     while k.WaitForSingleObject(handle,1000)==0x102:
      assert time.monotonic()<deadline,'Existing worker deadline exceeded'
    finally:k.CloseHandle(handle)
   execution=out/'test_c9_display_c2/execution.json';e=json.loads(execution.read_text())
   assert e['name']=='test_c9_display_c2'
   log=out/'test_c9_display_c2.log'
   report['steps'].append(dict(name=e['name'],returncode=e['returncode'],seconds=None,
    log=log.relative_to(R).as_posix(),log_sha256=sha(log),resumed_existing_worker=True))
   if e['returncode']:failures.append(e['name'])
   save();print('COMPLETED existing full-HD worker',flush=True)
  rows,pinned=identities();report['identities_before']=rows
  report['handoff_before']=handoff()
  report['frozen_files']=len(pinned);save()
  for name in TESTS+REPLAYS:
   if any(v['name']==name for v in report['steps']):continue
   begin=time.monotonic();print('START '+name,flush=True)
   log=out/(name+'.log')
   with log.open('wb') as f:
    q=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__)),
       '--worker',name,'--out',str(out/name)],cwd=R,stdout=f,stderr=subprocess.STDOUT,
       timeout=7200 if name=='test_c9_display_c2' else 600)
   row=dict(name=name,returncode=q.returncode,seconds=round(time.monotonic()-begin,2),
    log=log.relative_to(R).as_posix(),log_sha256=sha(log))
   report['steps'].append(row);save()
   print(('PASS ' if q.returncode==0 else 'FAIL ')+name,flush=True)
   if q.returncode:failures.append(name)
  report['quality_isp_chain']=chain(out)
  # The saved failing camera trial must remain a failure after offline replay.
  from check_c9_linebuffer_quality import check
  m=json.loads((R/'logs/c9_linebuffer_quality_board_20261103/20261103_181949/result.json').read_text())
  seen=check((R/m['camera_attempt']).parent/'uart.log')
  assert not seen['geometry_verified'] and seen['after']['csr']['phy_active_error_seen']
  report['camera_failure_preserved']=True
  report['identities_after'],after=identities();assert pinned==after
  report['handoff_after']=handoff()
  assert report['handoff_before']==report['handoff_after']
  profile=R/'config/c9_active_profile.json'
  report['active_profile_sha256']=sha(profile)
  assert report['active_profile_sha256']=='29d90baa2c3721a2e440518b5aa4e20282003718408be57d0403f020dbe449fb'
  report['frozen_files_unchanged']=True
  report['status']='PASS_OFFLINE_REGRESSION_HARDWARE_PENDING' if not failures else 'FAIL_OFFLINE_REGRESSION'
 except BaseException as exc:
  traceback.print_exc();report['status']='FAIL_OFFLINE_REGRESSION';report['error']=repr(exc)
 report['failures']=failures;report['finished']=datetime.datetime.now().astimezone().isoformat();save()
 print(json.dumps(dict(status=report['status'],failures=failures,report=str(out/'result.json')),ensure_ascii=False),flush=True)
 return 0 if report['status'].startswith('PASS_') else 1

if __name__=='__main__':raise SystemExit(main())
