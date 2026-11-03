"""Preflight by default; --capture measures DDR/camera then restores C10 SRAM.

No Flash programming. A captured geometry record never means video acceptance.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,shutil,subprocess
from c9_probe_image import select
R=Path(__file__).resolve().parents[1];E=R/'tools/efinity/2026.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--capture',action='store_true');ap.add_argument('--port',default='COM13');a=ap.parse_args()
 image,audit=select(R,'linebuffer_csr');fw=R/'firmware/c9_camera_geometry';manifest=json.loads((fw/'BUILD_RECORD.json').read_text())
 for n,d in manifest['source_sha256'].items():assert sha(R/n)==d,n
 for n,d in manifest['artifacts'].items():assert sha(fw/n)==d['sha256'],n
 capture=image.parents[1]/'capture_geometry.py';assert capture.relative_to(R).as_posix() in json.loads(audit.read_text())['evidence_sha256']
 command=[str(E/'python311/bin/python.exe'),str(R/'tools/run_ram_diagnostic.py'),'--record',str(fw/'BUILD_RECORD.json'),'--binary',str(fw/'c9_geometry.bin'),'--prefix','C9|','--configure-probe','linebuffer_csr','--seconds','40','--port',a.port]
 env=os.environ.copy();env.update(PYTHONHOME=str(E/'python311'),PYTHONUTF8='1')
 if not a.capture:
  q=subprocess.run(command+['--preflight-only'],cwd=R,env=env,capture_output=True,text=True,timeout=60);print(q.stdout+q.stderr)
  return q.returncode
 out=R/'logs/c9_linebuffer_csr_board_20261103'/datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
 result=dict(status='RUNNING',flash_written=False,board_acceptance_passed=False,real_camera_verified=False,runner_sha256=sha(Path(__file__)))
 def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 def run(name,cmd,timeout):
  print('START '+name,flush=True)
  with (out/(name+'.log')).open('wb') as log:q=subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
  text=(out/(name+'.log')).read_text(errors='replace');print(name+' exit='+str(q.returncode),flush=True)
  assert q.returncode==0,name+' failed; inspect '+str(out/(name+'.log'))
  paths=re.findall(r'^ATTEMPT_DIR=(.+)$',text,re.M);assert len(paths)==1,'Missing capture directory'
  folder=Path(paths[0].strip()).resolve();assert folder.is_relative_to(R/'logs')
  return folder
 save()
 try:
  folder=run('ddr_status',[str(E/'python311/bin/python.exe'),str(capture)],600)
  frozen=folder/'capture_tool.py'
  if frozen.exists():assert sha(frozen)==sha(capture)
  else:shutil.copyfile(capture,frozen)
  from check_c9_ddr_calibration import check as check_ddr
  ddr=check_ddr(folder/'attempt.json',audit);assert ddr['calibration_verified'] and ddr['c10_restore_passed'],'DDR capture/restore failed'
  result['ddr_status']=dict(attempt=(folder/'attempt.json').relative_to(R).as_posix(),result=ddr);save()
  # Inner limits are 180s configure + 420s readback + 30s resume + 40s UART.
  # Keep the outer deadline beyond their sum so it cannot cut off normal cleanup.
  folder=run('camera_geometry',command,900)
  for tool in ['run_ram_diagnostic.py','c9_probe_image.py','check_c9_geometry.py','check_c9_linebuffer_csr.py','check_c9_uart.py']:shutil.copyfile(R/'tools'/tool,folder/tool)
  from check_c9_linebuffer_csr import check as check_geometry
  observed=check_geometry(folder/'uart.log');(folder/'geometry_observation.json').write_text(json.dumps(observed,indent=2)+'\n')
  assert observed['status']=='CAPTURED_LINEBUFFER_STATUS_ONLY',observed['status']
  result.update(status='CAPTURED_LINEBUFFER_STATUS_ONLY',camera_attempt=(folder/'attempt.json').relative_to(R).as_posix(),observation=observed)
 except Exception as exc:result.update(status='FAIL_CAPTURE_OR_EVIDENCE',error=repr(exc))
 finally:
  # Always restore after a diagnostic attempt; no Flash modification is involved.
  try:
   restored=run('restore_c10',[str(E/'python311/bin/python.exe'),str(R/'tools/capture_soc_cold_warm.py')],300)
   result['c10_restore_passed']=True;result['restore_attempt']=(restored/'attempt.json').relative_to(R).as_posix()
  except Exception as exc:result['c10_restore_passed']=False;result['restore_error']=repr(exc)
  result['finished']=datetime.datetime.now().astimezone().isoformat();save()
 print(json.dumps(result,indent=2));return 0 if result['status']=='CAPTURED_LINEBUFFER_STATUS_ONLY' and result['c10_restore_passed'] else 1
if __name__=='__main__':raise SystemExit(main())
