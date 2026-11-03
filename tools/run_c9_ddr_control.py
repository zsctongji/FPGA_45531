"""Pinned C9 DDR control: offline preflight by default, --capture for the board.

Wraps the frozen capture, freezes its source, then checks calibration from raw
samples. A successful capture process is never itself a calibration PASS.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, time
from c9_probe_image import select
from check_c9_ddr_calibration import check

R=Path(__file__).resolve().parents[1];E=R/'tools/efinity/2026.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--variant',choices=['nopack','speed','display'],default='nopack')
    ap.add_argument('--capture',action='store_true',help='Access the connected board; temporary SRAM control, then C10 restore')
    args=ap.parse_args();image,audit=select(R,args.variant)
    capture={'speed':image.parents[1]/'capture_speed.py','nopack':image.parents[1]/'capture_nopack.py','display':image.parents[1]/'capture_display.py'}[args.variant]
    manifest=json.loads(audit.read_text());key=capture.relative_to(R).as_posix()
    assert key in manifest['evidence_sha256'] and sha(capture)==manifest['evidence_sha256'][key],'Unbound capture tool'
    if not args.capture:
        print(json.dumps(dict(status='PASS_OFFLINE_CONTROL_PREFLIGHT',hardware_accessed=False,board_calibration_fixed=False,
            variant=args.variant,image_sha256=sha(image),audit_sha256=sha(audit),capture_tool_sha256=sha(capture)),indent=2));return 0
    out=R/'logs/ddr_control_20261102'/datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
    report=dict(status='RUNNING',variant=args.variant,hardware_accessed=True,flash_written=False,calibration_verified=False,runner_sha256=sha(Path(__file__)))
    def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    env=os.environ.copy();env.update(PYTHONHOME=str(E/'python311'),PYTHONUTF8='1')
    save();child=None
    try:
        with (out/'capture.log').open('wb') as f:
            child=subprocess.Popen([str(E/'python311/bin/python.exe'),str(capture)],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
            start=time.monotonic();notice=start
            while child.poll() is None:
                if time.monotonic()-start>600:raise TimeoutError('Capture/restore timeout; inspect board state')
                if time.monotonic()-notice>=30:print('WAIT DDR capture and C10 restore',flush=True);notice=time.monotonic()
                time.sleep(.2)
        report['capture_returncode']=child.returncode
        text=(out/'capture.log').read_text(errors='replace');matches=re.findall(r'^ATTEMPT_DIR=(.+)$',text,re.M)
        assert len(matches)==1,'Missing/unexpected capture directory'
        attempt=Path(matches[0].strip()).resolve();assert attempt.is_relative_to((R/'logs/c9_ddr_probe_20261101').resolve())
        meta=json.loads((attempt/'attempt.json').read_text());assert sha(capture)==meta['capture_tool_sha256']
        frozen=attempt/'capture_tool.py'
        if frozen.exists():assert sha(frozen)==sha(capture)
        else:shutil.copyfile(capture,frozen)
        result=check(attempt/'attempt.json',audit)
        report.update(status=result['status'],attempt=(attempt/'attempt.json').relative_to(R).as_posix(),calibration=result,
            calibration_verified=result['calibration_verified'],c10_restore_passed=meta.get('c10_restore_passed') is True)
    except Exception as exc:report.update(status='FAIL_CONTROL_OR_EVIDENCE',error=repr(exc))
    finally:
        # Do not kill a child while it may be restoring C10 on an outer timeout.
        if child is not None and child.poll() is None:report['capture_still_running']=True
        save()
    print(json.dumps(report,indent=2));return 0 if report['calibration_verified'] and report.get('c10_restore_passed') else 1
if __name__=='__main__':raise SystemExit(main())
