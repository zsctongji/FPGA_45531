"""Optional SRAM-only C8 control capture; --preflight-only never opens hardware.

Full capacity is accepted only by the existing strict UART checker. Always
attempt to restore the accepted C10 image after a hardware capture.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, subprocess, sys, time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from check_ddr_uart import validate

R=Path(__file__).resolve().parents[2]; E=R/'tools/efinity/2026.1'
P=R/'projects/08_ddr_diag'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def preflight():
    audit_path=R/'fpga_bitstreams/ddr_diag_100mhz/BUILD_RECORD.json'
    a=json.loads(audit_path.read_text())
    assert a['status']=='PASS_OFFLINE_DIAGNOSTIC'
    image=P/'outflow/ddr_diag.bit'
    for n,d in a['source_sha256'].items(): assert sha(R/n)==d,n
    for n,v in a['artifacts'].items(): assert sha(P/'outflow'/n)==v['sha256'],n
    for n,d in a['project_constraint_sha256'].items(): assert sha(P/n)==d,n
    assert sha(P/'work_pnr/ddr_diag.lbf')==json.loads((R/'logs/ddr_diag_build.json').read_text(encoding='utf-8-sig'))['steps'][-1]['routed_lbf_sha256']
    return image,audit_path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--preflight-only',action='store_true');ap.add_argument('--port',default='COM13')
    ap.add_argument('--seconds',type=int,default=120);args=ap.parse_args()
    image,audit_path=preflight()
    if args.preflight_only:
        print(json.dumps(dict(status='PASS_OFFLINE_PREFLIGHT',hardware_accessed=False,board_test_passed=False,
            flash_written=False,fpga_image_sha256=sha(image),implementation_audit_sha256=sha(audit_path)),indent=2));return 0
    import serial
    env=os.environ.copy()
    env.update(PYTHONHOME=str(E/'python311'),PYTHONUTF8='1',EFX_HIFTDI_ENABLE='0',PROCESSOR_ARCHITECTURE='AMD64',
        EFINITY_USER_DIR_INI=(R/'build/ddr_diag/efinity_user/user_dir.ini').as_posix(),EFINITY_USER_DIR=str(R/'build/ddr_diag/efinity_user'))
    for k,p in [('EFINITY_HOME',E),('EFXPGM_HOME',E/'pgm'),('EFXDBG_HOME',E/'debugger'),('EFXSVF_HOME',E/'svf'),('EFXPT_HOME',E/'pt'),('EFXIPM_HOME',E/'ipm')]:env[k]=p.as_posix()
    out=R/'logs/c8_comb4_baseline_20261102'/datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
    rec=dict(status='RUNNING',started=datetime.datetime.now().astimezone().isoformat(),flash_written=False,board_test_passed=False,
        fpga_image_sha256=sha(image),implementation_audit_sha256=sha(audit_path),capture_tool_sha256=sha(Path(__file__)))
    def save(): (out/'attempt.json').write_text(json.dumps(rec,indent=2)+'\n')
    def phase(name,cmd,timeout):
        with (out/(name+'.log')).open('wb') as f:
            q=subprocess.run(cmd,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
        return q.returncode
    save();print('ATTEMPT_DIR='+str(out),flush=True)
    port=serial.Serial(port=None,baudrate=115200,timeout=.1);port.dtr=False;port.rts=False;port.port=args.port
    try:
        port.open();port.reset_input_buffer()
        assert phase('configure',[str(E/'python311/bin/python.exe'),str(E/'pgm/bin/efx_pgm/ftdi_program.py'),str(image),'-m','jtag','-u','ftdi://0x0403:0x6011:0:ff/1','--jtag_clock_freq','1000000'],180)==0
        rec['fpga_configured']=True;save();data=b'';start=time.monotonic();notice=start
        with (out/'uart.log').open('wb') as f:
            while time.monotonic()-start<args.seconds:
                chunk=port.read(max(1,port.in_waiting))
                if chunk: data+=chunk;f.write(chunk);f.flush()
                report=validate(data.decode('utf-8',errors='replace'))
                if report['status']=='PASS_LOG': break
                if time.monotonic()-notice>30: print('WAIT C8 full-capacity UART',flush=True);notice=time.monotonic()
        rec['uart_check']=validate(data.decode('utf-8',errors='replace'));rec['uart_sha256']=sha(out/'uart.log')
        rec['board_test_passed']=rec['uart_check']['status']=='PASS_LOG'
        rec['status']='PASS_FULL_CAPACITY_CONTROL' if rec['board_test_passed'] else 'FAIL_OR_INCOMPLETE_CONTROL'
    except Exception as exc: rec['status']='HOST_ERROR';rec['error']=repr(exc)
    finally:
        port.close();save()
        try: rec['c10_restore_passed']=phase('restore_c10',[str(E/'python311/bin/python.exe'),str(R/'tools/capture_soc_cold_warm.py')],270)==0
        except Exception as exc: rec['c10_restore_passed']=False;rec['restore_error']=repr(exc)
        rec['finished']=datetime.datetime.now().astimezone().isoformat();save()
    print(json.dumps(rec,indent=2));return 0 if rec['board_test_passed'] and rec.get('c10_restore_passed') else 1

if __name__=='__main__': raise SystemExit(main())
