"""C10 SRAM configuration -> ROM reads existing Flash -> C1 six-sample check.
No CPU/RAM firmware loading and no Flash programming. This is a warm automatic
boot experiment; only a separate physical power cycle can establish cold boot.
"""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,time
import serial
from compare_c1_reference import compare
ROOT=Path(__file__).resolve().parents[1];EF=ROOT/'tools/efinity/2026.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 audit=json.loads((ROOT/'logs/soc_cold_audit.json').read_text());assert audit['status']=='PASS_OFFLINE_COLD_IMPLEMENTATION'
 assert sha(ROOT/'tools/audit_soc_live.py')==audit['auditor_sha256']
 for field in ['evidence_sha256','source_sha256']:
  for name,digest in audit[field].items():assert sha(ROOT/name)==digest,name
 out=ROOT/'logs/c10_warm_boot_20261101'/datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
 image=ROOT/'projects/10_soc_cold/outflow/soc_physical.bit'
 meta=dict(status='RUNNING',started=datetime.datetime.now().astimezone().isoformat(),fpga_image_sha256=sha(image),flash_written=False,cpu_loaded=False,ram_firmware_loaded=False,cold_boot_passed=False,warm_automatic_boot_passed=False,port='COM13',baud=115200)
 def save():(out/'attempt.json').write_text(json.dumps(meta,indent=2)+'\n')
 save();print('ATTEMPT_DIR='+str(out),flush=True)
 env=os.environ.copy();env.update(PYTHONHOME=str(EF/'python311'),PYTHONUTF8='1',EFX_HIFTDI_ENABLE='0',PROCESSOR_ARCHITECTURE='AMD64',EFINITY_USER_DIR_INI=(ROOT/'build/ddr_diag/efinity_user/user_dir.ini').as_posix())
 for k,p in [('EFINITY_HOME',EF),('EFXPGM_HOME',EF/'pgm'),('EFXDBG_HOME',EF/'debugger'),('EFXPT_HOME',EF/'pt'),('EFXIPM_HOME',EF/'ipm')]:env[k]=p.as_posix()
 port=serial.Serial(port=None,baudrate=115200,timeout=.1);port.dtr=False;port.rts=False;port.port='COM13';child=None
 try:
  port.open();port.reset_input_buffer();buffer=b'';done=False;start=time.monotonic();notice=start
  with (out/'uart.log').open('wb') as raw,(out/'configure.log').open('wb') as log:
   cmd=[str(EF/'python311/bin/python.exe'),str(EF/'pgm/bin/efx_pgm/ftdi_program.py'),str(image),'-m','jtag','-u','ftdi://0x0403:0x6011:0:ff/1','--jtag_clock_freq','1000000']
   child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
   while time.monotonic()-start<240:
    data=port.read(max(1,port.in_waiting))
    if data:
     raw.write(data);raw.flush();buffer+=data
     while b'\n' in buffer:
      line,buffer=buffer.split(b'\n',1);text=line.decode(errors='replace').strip('\r');print(text,flush=True)
      if 'C1|DONE ' in text or 'C1|FAIL ' in text or 'CRASH' in text:done=True
    if child.poll() is not None and child.returncode:raise RuntimeError('SRAM configuration failed')
    if done and child.poll() is not None:break
    if time.monotonic()-notice>30:print('WAIT automatic Flash firmware boot',flush=True);notice=time.monotonic()
  meta['programmer_returncode']=child.poll();assert child.poll()==0,'Configuration not completed'
  result=compare((out/'uart.log').read_text(errors='replace'),json.loads((ROOT/'firmware/c1_static_person_detect/C1_INPUT_MANIFEST.json').read_text()),json.loads((ROOT/'logs/pc_ai/c1_reference.json').read_text()))
  (out/'reference_check.json').write_text(json.dumps(result,indent=2)+'\n')
  meta['warm_automatic_boot_passed']=result['status']=='PASS';meta['uart_sha256']=sha(out/'uart.log');meta['status']='PASS_WARM_ROM_FLASH_BOOT' if meta['warm_automatic_boot_passed'] else 'FAIL_WARM_ROM_FLASH_BOOT'
 except Exception as exc:meta['status']='HOST_ERROR';meta['error']=repr(exc);print(repr(exc),flush=True)
 finally:
  if child and child.poll() is None:child.terminate();child.wait(timeout=10)
  port.close();meta['finished']=datetime.datetime.now().astimezone().isoformat();save()
 print(json.dumps(meta,indent=2),flush=True);return 0 if meta['warm_automatic_boot_passed'] else 1
if __name__=='__main__':raise SystemExit(main())
