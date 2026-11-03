"""Run the pinned C1 ELF/BIN on the already SRAM-configured C7 via JTAG."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
import serial
root=Path(__file__).resolve().parents[2];ef=root/'tools/efinity/2026.1'
out=root/'logs/c7_board_20261101'/('c1_'+datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S'))
out.mkdir(parents=True,exist_ok=False)
fw=root/'firmware/c1_static_person_detect/tinyml_c1.bin'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(fw)=='73401bb622454d06fd9fdc57ea799a0191cbd852574ccec9442f19006346307e'
probe=root/'logs/c7_board_20261101/probe_20261101_123338'
assert json.loads((probe/'attempt.json').read_text())['result']=='PROBE_COMPLETED'
cfg=(probe/'probe.cfg').read_text().split('init\n')[0]+'''init
halt
echo C7_CPU_PC_BEFORE
echo [reg pc]
echo [load_image {%s} 0x1000 bin]
echo C7_LOAD_COMPLETED
echo [verify_image {%s} 0x1000 bin]
echo C7_VERIFY_COMPLETED
resume 0x1000
echo C7_CPU_RESUMED_AT_1000
shutdown
'''%(fw.as_posix(),fw.as_posix())
(out/'load_c1.cfg').write_text(cfg,encoding='utf-8')
meta=dict(started=datetime.datetime.now().astimezone().isoformat(),stage='C7_C1_STATIC_INFERENCE',
 firmware_sha256=sha(fw),firmware=str(fw),configuration_attempt=probe.relative_to(root).as_posix(),
 fpga_image_sha256='962079f839a2f0348142e87fd83dd841f1534e30de42d71f5edb6de52d1ea26b',
 uart='COM13',baud=115200,dtr=False,rts=False,flash_written=False,board_inference_passed=False)
def save():(out/'attempt.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
save();print('ATTEMPT_DIR='+str(out),flush=True)
port=serial.Serial(port=None,baudrate=115200,timeout=.1);port.dtr=False;port.rts=False;port.port='COM13'
child=None
try:
 port.open();port.reset_input_buffer()
 with (out/'uart.log').open('wb') as raw,(out/'openocd.log').open('wb') as olog:
  child=subprocess.Popen([str(ef/'debugger/openocd/bin/openocd.exe'),'-f',str(out/'load_c1.cfg')],cwd=root,stdout=olog,stderr=subprocess.STDOUT)
  start=time.monotonic();buf=b'';last_notice=start;done=False
  while time.monotonic()-start<600:
   data=port.read(max(1,port.in_waiting))
   if data:
    raw.write(data);raw.flush();buf+=data
    # BSP may send LF followed by CR; normalize display only, preserve raw file.
    while b'\n' in buf:
     line,buf=buf.split(b'\n',1);text=line.decode('utf-8',errors='replace').strip('\r')
     print(text,flush=True)
     if 'C1|DONE ' in text or 'C1|FAIL ' in text:done=True
   if child.poll() is not None:
    meta['openocd_returncode']=child.returncode
    if child.returncode:raise RuntimeError('OpenOCD load failed')
    if done:break
   elif time.monotonic()-start>240:
    raise TimeoutError('OpenOCD firmware loading exceeded 240s')
   if time.monotonic()-last_notice>25:
    print('WAIT elapsed_s=%d openocd=%s'%(time.monotonic()-start,child.poll()),flush=True)
    print((out/'openocd.log').read_text(encoding='utf-8',errors='replace')[-800:],flush=True)
    last_notice=time.monotonic()
  meta['result']='UART_TERMINAL_CAPTURED' if done else 'UART_TIMEOUT'
  meta['elapsed_seconds']=time.monotonic()-start
except Exception as exc:
 meta['result']='HOST_OR_DEBUG_ERROR';meta['error']=repr(exc);print(repr(exc),flush=True)
finally:
 if child and child.poll() is None:child.terminate();child.wait(timeout=10)
 port.close();meta['finished']=datetime.datetime.now().astimezone().isoformat();save()
env=os.environ.copy();env['PYTHONHOME']=str(ef/'python311');env['PYTHONUTF8']='1'
result=subprocess.run([str(ef/'python311/bin/python.exe'),str(root/'tools/check_c1_uart.py'),str(out/'uart.log'),'--output',str(out/'uart_check.json')],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
meta['checker_returncode']=result.returncode
meta['board_inference_passed']=result.returncode==0 and meta.get('openocd_returncode')==0
for name in ['uart.log','openocd.log']:meta[name.replace('.','_')+'_sha256']=sha(out/name)
save();print((out/'openocd.log').read_text(encoding='utf-8',errors='replace'),flush=True)
print(result.stdout.decode('utf-8',errors='replace'),flush=True)
print(json.dumps(meta,indent=2),flush=True)
sys.exit(0 if meta['board_inference_passed'] else 1)
