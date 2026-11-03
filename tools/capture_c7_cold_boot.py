"""Read-only reconnect-aware UART capture. Never configures FPGA/CPU/Flash."""
from pathlib import Path
import argparse,datetime,hashlib,json,sys,time
import serial
from serial.tools import list_ports
ROOT=Path(__file__).resolve().parents[1]
from compare_c1_reference import compare
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--port',default='COM13');ap.add_argument('--initial-port');ap.add_argument('--seconds',type=int,default=600)
 ap.add_argument('--program-record',type=Path,default=ROOT/'logs/c7_cold_flash_program_20261101.json');a=ap.parse_args()
 program=json.loads(a.program_record.read_text())
 assert program['status']=='PASS_FLASH_WRITE_AND_TWO_FULL_VERIFICATIONS_COLD_BOOT_PENDING'
 assert program['readback_sha256']==program['expected_flash_sha256']
 out=ROOT/'logs/c7_cold_boot_20261101'/datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True,exist_ok=False)
 meta=dict(status='WAITING_FOR_USER_POWER_CYCLE',started=datetime.datetime.now().astimezone().isoformat(),port=a.port,baud=115200,dtr=False,rts=False,
  fpga_reconfigured_by_tool=False,cpu_loaded_by_tool=False,flash_written_by_tool=False,expected_flash_sha256=program['readback_sha256'],
  usb_disconnect_observed=False,usb_reconnect_observed=False,cold_boot_passed=False,program_record_sha256=hashlib.sha256(a.program_record.read_bytes()).hexdigest(),power_rail_scope='USB disconnect/reconnect plus user physical power-cycle confirmation; no rail waveform measurement')
 def save():(out/'attempt.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
 save();print('ATTEMPT_DIR='+str(out),flush=True)
 port=None;buffer=b'';done=False;start=time.monotonic();last_notice=start
 def open_port(name=None):
  p=serial.Serial(port=None,baudrate=115200,timeout=.1,xonxoff=False,rtscts=False,dsrdtr=False)
  p.dtr=False;p.rts=False;p.port=name or a.port;p.open();return p
 try:
  port=open_port(a.initial_port);meta['initial_port']=a.initial_port or a.port;port.reset_input_buffer();print('UART_ARMED; disconnect all board power and USB, then reconnect ORIGINAL USB port',flush=True)
  with (out/'uart.log').open('wb') as raw,(out/'pretrigger_uart.log').open('wb') as pre:
   while time.monotonic()-start<a.seconds:
    if port is None:
     if a.port in [p.device for p in list_ports.comports()]:
      try:
       port=open_port();meta['usb_reconnect_observed']=True;meta['reconnected']=datetime.datetime.now().astimezone().isoformat();save();print('USB_RECONNECTED; capturing Flash auto boot (no JTAG loading)',flush=True)
      except (serial.SerialException,OSError):time.sleep(.2);continue
     else:time.sleep(.2);continue
    try:
     data=port.read(max(1,port.in_waiting))
    except (serial.SerialException,OSError):
     port.close();port=None;buffer=b'';meta['usb_disconnect_observed']=True;meta['disconnected']=datetime.datetime.now().astimezone().isoformat();save();print('USB_DISCONNECTED',flush=True);continue
    if data:
     if not meta['usb_disconnect_observed']:pre.write(data);pre.flush();continue
     raw.write(data);raw.flush();buffer+=data
     while b'\n' in buffer:
      line,buffer=buffer.split(b'\n',1);text=line.decode('utf-8',errors='replace').strip('\r')
      if text.startswith('C1|') or 'CRASH' in text:print(text,flush=True)
      if 'C1|DONE ' in text or 'C1|FAIL ' in text or 'CRASH' in text:done=True
    if done:break
    if time.monotonic()-last_notice>45:
     print('WAIT cold_boot disconnect=%s reconnect=%s'%(meta['usb_disconnect_observed'],meta['usb_reconnect_observed']),flush=True);last_notice=time.monotonic()
  text=(out/'uart.log').read_text(encoding='utf-8',errors='replace')
  manifest=json.loads((ROOT/'firmware/c1_static_person_detect/C1_INPUT_MANIFEST.json').read_text())
  reference=json.loads((ROOT/'logs/pc_ai/c1_reference.json').read_text())
  result=compare(text,manifest,reference);result['log_sha256']=hashlib.sha256((out/'uart.log').read_bytes()).hexdigest()
  (out/'reference_check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
  meta['cold_boot_passed']=result['status']=='PASS' and meta['usb_disconnect_observed'] and meta['usb_reconnect_observed']
  meta['status']='PASS_FLASH_AUTOMATIC_COLD_BOOT' if meta['cold_boot_passed'] else 'FAIL_OR_INCOMPLETE_COLD_BOOT'
  meta['uart_sha256']=result['log_sha256']
 except Exception as exc:meta['status']='HOST_ERROR';meta['error']=repr(exc);print(repr(exc),flush=True)
 finally:
  if port is not None:port.close()
  meta['finished']=datetime.datetime.now().astimezone().isoformat();save()
 print(json.dumps(meta,indent=2),flush=True);return 0 if meta['cold_boot_passed'] else 1
if __name__=='__main__':raise SystemExit(main())
