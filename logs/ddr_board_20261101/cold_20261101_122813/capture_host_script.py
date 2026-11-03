"""One real board attempt: UART capture and JTAG SRAM configuration only."""
from pathlib import Path
import datetime, hashlib, json, os, re, subprocess, sys, time
import serial

root = Path(__file__).resolve().parents[2]
image = root / 'fpga_bitstreams/ddr_diag_100mhz/ddr_diag.bit'
expected_sha = '752d7855d7726ec61fdc1b863df381ff7fdac0f6577f0f59eeb8af812f9a6add'
actual_sha = hashlib.sha256(image.read_bytes()).hexdigest()
if actual_sha != expected_sha:
    raise SystemExit('STOP: bitstream identity changed')
efinity = root / 'tools/efinity/2026.1'
env = os.environ.copy()
env.update(EFINITY_HOME=efinity.as_posix(), EFXPGM_HOME=(efinity/'pgm').as_posix(),
           EFXDBG_HOME=(efinity/'debugger').as_posix(), EFXIPM_HOME=(efinity/'ipm').as_posix(),
           EFXPT_HOME=(efinity/'pt').as_posix(), PYTHONHOME=str(efinity/'python311'),
           PYTHONUTF8='1', PYTHONUNBUFFERED='1', EFX_HIFTDI_ENABLE='0',
           EFINITY_USER_DIR_INI=(root/'build/ddr_diag/efinity_user/user_dir.ini').as_posix(),
           PROCESSOR_ARCHITECTURE='AMD64')
python = str(efinity/'python311/bin/python.exe')
programmer = str(efinity/'pgm/bin/efx_pgm/ftdi_program.py')
url = 'ftdi://0x0403:0x6011:0:ff/1'
stamp = datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')
out = root / 'logs/ddr_board_20261101' / ('cold_'+stamp)
out.mkdir(parents=True, exist_ok=False)
meta = dict(started=datetime.datetime.now().astimezone().isoformat(), image=str(image),
            image_sha256=actual_sha, mode='jtag', flash_written=False, destructive_ddr_test=True,
            uart='COM13', baud=115200, dtr=False, rts=False, jtag_url=url, jtag_hz=1000000,
            expected_idcode='0x10660a79', board_test_passed=False, result='PRECHECK')
meta.update(test_kind='cold_power_on_then_jtag_reload',
            power_cycle_evidence='User reported all-power disconnection/reconnection in this conversation; not independently measured',
            user_reported_power_cycle=True, flash_boot_validated=False,
            usb_port_recovery='Initial reconnect used USB(5), B bound to FTDIBUS; no programming attempted there. User returned to original USB(1), B libusbK and C COM13 restored.')
def save():
    (out/'attempt.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
save()
print('ATTEMPT_DIR='+str(out), flush=True)
scan = subprocess.run([python,programmer,'--scan_usb'],cwd=root,env=env,
                      stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
(out/'jtag_scan.log').write_bytes(scan.stdout)
meta['scan_returncode'] = scan.returncode
devices = json.loads(scan.stdout.decode('utf-8-sig').strip()) if scan.returncode == 0 else []
if len(devices)!=1 or devices[0].get('idcode')!=['0x10660a79']:
    meta['result']='IDENTITY_REJECTED';save();raise SystemExit('STOP: unexpected JTAG identity')
meta['jtag_scan']=devices
port = serial.Serial(port=None,baudrate=115200,bytesize=8,parity='N',stopbits=1,
                     timeout=0.1,xonxoff=False,rtscts=False,dsrdtr=False)
port.dtr=False;port.rts=False;port.port='COM13'
proc=None
try:
    port.open();port.reset_input_buffer()
    meta['uart_opened']=datetime.datetime.now().astimezone().isoformat();save()
    print('UART_READY; loading verified SRAM image via JTAG',flush=True)
    command=[python,programmer,str(image),'-m','jtag','-u',url,'--jtag_clock_freq','1000000']
    meta['command']=command;meta['result']='RUNNING';save()
    with (out/'programmer.log').open('wb') as plog, (out/'uart.log').open('wb') as raw:
        proc=subprocess.Popen(command,cwd=root,env=env,stdout=plog,stderr=subprocess.STDOUT)
        start=time.monotonic();buf=b'';terminal=[];last_print=0;latest='';last_state=None
        while time.monotonic()-start < 600:
            chunk=port.read(max(1,port.in_waiting))
            if chunk:
                raw.write(chunk);raw.flush();buf+=chunk
                while b'\n' in buf:
                    line,buf=buf.split(b'\n',1)
                    latest=line.decode('ascii',errors='replace').rstrip('\r')
                    match=re.fullmatch(r'DDR\|S=([0-9A-F]{2}) L=([0-3]) C=([01]) I=([0-9A-F]{2}) E=([0-9A-F]{2}) A=([0-9A-F]{8}) N=([0-9A-F]{8}) P=([0-9A-F]{8})',latest)
                    if match:
                        state=match.group(1)
                        if state!=last_state or time.monotonic()-last_print>=10:
                            print(latest,flush=True);last_print=time.monotonic();last_state=state
                        if state in ['06','E0','F0','F1']:terminal.append(latest)
                        else:terminal=[]
            code=proc.poll()
            if code is not None:
                meta['programmer_returncode']=code
                if code!=0:
                    meta['result']='PROGRAMMER_FAILED';break
                if len(terminal)>=2:
                    meta['result']='TERMINAL_RECORDS_CAPTURED';break
            elif time.monotonic()-start>120:
                proc.terminate();meta['result']='PROGRAMMER_TIMEOUT';break
            if time.monotonic()-last_print>=30:
                print('WAIT elapsed_s=%d programmer=%s latest=%s'%(time.monotonic()-start,code,latest),flush=True)
                last_print=time.monotonic()
        else:meta['result']='CAPTURE_TIMEOUT'
        if proc.poll() is None:
            proc.terminate();proc.wait(timeout=10)
        meta['programmer_returncode']=proc.returncode
        meta['elapsed_seconds']=round(time.monotonic()-start,3)
except Exception as exc:
    meta['result']='HOST_EXCEPTION';meta['exception']=repr(exc)
    if proc is not None and proc.poll() is None:proc.terminate();proc.wait(timeout=10)
    raise
finally:
    port.close();meta['finished']=datetime.datetime.now().astimezone().isoformat();save()
check=subprocess.run([python,str(root/'tools/check_ddr_uart.py'),str(out/'uart.log'),
                      '--output',str(out/'uart_check.json')],cwd=root,env=env,capture_output=True)
meta['uart_check_returncode']=check.returncode
meta['board_test_passed']=(meta.get('programmer_returncode')==0 and check.returncode==0)
meta['programmer_log_sha256']=hashlib.sha256((out/'programmer.log').read_bytes()).hexdigest()
meta['uart_log_sha256']=hashlib.sha256((out/'uart.log').read_bytes()).hexdigest()
save()
print((out/'programmer.log').read_text(encoding='utf-8',errors='replace'),flush=True)
print(check.stdout.decode('utf-8',errors='replace'),flush=True)
print(json.dumps(meta,ensure_ascii=False,indent=2),flush=True)
sys.exit(0 if meta['board_test_passed'] else 1)
