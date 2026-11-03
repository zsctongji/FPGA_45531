"""Read-only UART capture of a KEY0 restart; no FPGA or flash programming."""
from pathlib import Path
import datetime, hashlib, json, re, sys, time
import serial

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools'))
from check_ddr_uart import LINE, validate
stamp=datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')
out=root/'logs/ddr_board_20261101'/('key0_'+stamp)
out.mkdir(parents=True,exist_ok=False)
prior=root/'logs/ddr_board_20261101/20261101_121928/attempt.json'
identity=json.loads(prior.read_text(encoding='utf-8'))
image=Path(identity['image'])
assert identity['board_test_passed']
assert hashlib.sha256(image.read_bytes()).hexdigest()==identity['image_sha256']
meta=dict(started=datetime.datetime.now().astimezone().isoformat(),
          trigger='KEY0/SW0 pressed by user',mode='uart_capture_only',
          uart='COM13',baud=115200,dtr=False,rts=False,flash_written=False,
          fpga_reprogrammed=False,prior_configuration_attempt=str(prior.relative_to(root)),
          image_sha256=identity['image_sha256'],
          identity_scope='Previous JTAG configuration and unchanged local image; no new hardware image attestation',
          reset_or_active_observed=False,reset_state_observed=False,
          board_test_passed=False,result='CAPTURING')
def save():
    (out/'attempt.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save();print('ATTEMPT_DIR='+str(out),flush=True)
port=serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,
                   timeout=0.1,xonxoff=False,rtscts=False,dsrdtr=False)
port.dtr=False;port.rts=False;port.port='COM13'
buf=b'';capture=bytearray();terminal=0;last_print=0;notified=False
try:
    port.open();port.reset_input_buffer()
    print('UART_READY; waiting for a fresh diagnostic run',flush=True)
    start=time.monotonic()
    with (out/'uart.log').open('wb') as raw, (out/'pretrigger_uart.log').open('wb') as pre:
        while time.monotonic()-start<180:
            chunk=port.read(max(1,port.in_waiting))
            if not chunk:continue
            buf+=chunk
            while b'\n' in buf:
                line,buf=buf.split(b'\n',1);full=line+b'\n'
                text=line.decode('ascii',errors='replace').rstrip('\r')
                match=LINE.fullmatch(text)
                if match:
                    status=int(match.group(1),16)
                    if status in (0,1,2,3):
                        meta['reset_or_active_observed']=True
                        if status==0:meta['reset_state_observed']=True
                    if not meta['reset_or_active_observed']:
                        pre.write(full);pre.flush()
                        if not notified:
                            print('PREVIOUS_TERMINAL_ONLY: '+text,flush=True)
                            notified=True
                        continue
                    if status in (6,0xe0,0xf0,0xf1):terminal+=1
                    else:terminal=0
                elif not meta['reset_or_active_observed']:
                    pre.write(full);pre.flush();continue
                raw.write(full);raw.flush();capture.extend(full)
                if time.monotonic()-last_print>=10 or terminal:
                    print(text,flush=True);last_print=time.monotonic()
            if terminal>=2:
                meta['result']='TERMINAL_RECORDS_CAPTURED';break
        else:meta['result']='CAPTURE_TIMEOUT'
except Exception as exc:
    meta['result']='HOST_EXCEPTION';meta['exception']=repr(exc)
    raise
finally:
    port.close();meta['finished']=datetime.datetime.now().astimezone().isoformat();save()
check=validate(bytes(capture).decode('utf-8',errors='replace'))
check['log_sha256']=hashlib.sha256(bytes(capture)).hexdigest()
(out/'uart_check.json').write_text(json.dumps(check,indent=2)+'\n',encoding='utf-8')
meta['board_test_passed']=check['status']=='PASS_LOG' and meta['reset_or_active_observed']
meta['uart_log_sha256']=check['log_sha256'];save()
print(json.dumps(check,ensure_ascii=False),flush=True)
print(json.dumps(meta,ensure_ascii=False,indent=2),flush=True)
sys.exit(0 if meta['board_test_passed'] else 1)
