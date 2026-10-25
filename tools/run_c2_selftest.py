"""Portable C2 RTL regression. No vendor IP, physical DDR or board programming."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/06_soc_c2'
BUILD = ROOT / 'build/c2'
LOGS = ROOT / 'logs/c2'
REPORT = ROOT / 'logs/c2_selftest.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    record = {
        'status': 'RUNNING', 'started': datetime.now(timezone.utc).isoformat(),
        'scope': 'portable RTL functional simulation with synthetic masters and DDR model',
        'board_test_passed': False, 'vendor_ddr_simulated': False,
        'full_soc_integrated': False, 'timing_or_bandwidth_passed': False,
        'tests': [], 'source_sha256': {},
        'host_driver_test': None, 'riscv_compile': None,
    }

    def save():
        REPORT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    save()
    try:
        ivl = ROOT / 'tools/iverilog/bin/iverilog.exe'
        vvp = ivl.with_name('vvp.exe')
        for binary in (ivl, vvp):
            if not binary.is_file():
                raise FileNotFoundError(binary)
        prepared=subprocess.run([sys.executable,str(ROOT/'tools/prepare_c2_vendor.py')],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
        (LOGS/'prepare_vendor.log').write_text(prepared.stdout+prepared.stderr,encoding='utf-8')
        if prepared.returncode:raise RuntimeError(prepared.stdout+prepared.stderr)
        prepared=subprocess.run([sys.executable,str(ROOT/'tools/prepare_a_c2.py')],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
        if prepared.returncode:raise RuntimeError(prepared.stdout+prepared.stderr)
        prepared=subprocess.run([sys.executable,str(ROOT/'tools/prepare_c2_video_test.py')],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
        if prepared.returncode:raise RuntimeError(prepared.stdout+prepared.stderr)
        prepared=subprocess.run([sys.executable,str(ROOT/'tools/prepare_c2_framebuffer.py')],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
        if prepared.returncode:raise RuntimeError(prepared.stdout+prepared.stderr)
        for name in ['a_c2_video_frame0.gray','a_c2_video_frame0.json']:
            (BUILD/name).unlink(missing_ok=True)
        rtl = sorted((PROJECT / 'rtl').glob('*.sv'))
        rtl += sorted((PROJECT / 'a_side').glob('*.v'))
        sim = sorted((PROJECT / 'sim').glob('*.sv'))
        extra=[*sorted((ROOT/'team_work/03_ai_soc/c2').glob('*.[ch]')),
               *sorted((ROOT/'team_work/03_ai_soc/c24').glob('*.[ch]')),
               ROOT/'team_work/03_ai_soc/c3_hal/c3_shared_time.c',ROOT/'team_work/03_ai_soc/c3_hal/c3_shared_time.h',
               ROOT/'team_work/03_ai_soc/tests/test_c3_shared_time.c',
               ROOT/'tools/prepare_a_c2.py',ROOT/'projects/06_soc_c2/a_side/SOURCE_MANIFEST.json',
               ROOT/'tools/prepare_c2_video_test.py',ROOT/'team_work/shared/a_interface_v1.md',
               ROOT/'tools/prepare_c2_framebuffer.py',
               ROOT/'team_work/03_ai_soc/tests/test_c2_driver.c',ROOT/'tools/prepare_c2_vendor.py',
               ROOT/'tools/audit_c2_vendor.py',ROOT/'tools/check_c2_riscv.py',ROOT/'tools/build_c2_host.cmd',
               ROOT/'projects/03_tinyml/ip/sapphire_soc/sapphire_soc.v',ROOT/'build/c2/vendor_datacache.v']
        for p in [*rtl, *sim, *extra, Path(__file__), ROOT / 'tools/audit_c2_baselines.py']:
            record['source_sha256'][p.relative_to(ROOT).as_posix()] = sha(p)
        version = subprocess.run([str(ivl), '-V'], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        record['iverilog_version'] = version.stdout.splitlines()[0]
        matrix = [('cdc', {}, [None]), ('fifo', {}, [None]), ('pool', {}, [None]),
                  ('axi', {}, [12345, 67891, 20261024]),
                  ('image', {}, [12345, 67891, 20261024]),
                  ('adapter', {}, [12345,67891,20261024]),('cache',{},[None])]
        matrix += [('source_fence',{},[None]),('a_errors',{},[None])]
        matrix += [('video_config',{},[None])]
        matrix += [('video',{'EXTENDED':0},[12345])]
        for mem,video in [(7,3),(5,19)]:
            matrix.append(('video',{'MEM_HALF':mem,'VIDEO_HALF':video,'FRAME_WIDTH':384,
                                   'FRAME_HEIGHT':216,'STEP_X':4,'STEP_Y':4},[12345]))
        # Real full-frame video writer/scanout share C2 with AI DMA and synthetic
        # CPU/TinyML masters. Padded width383 also checks per-line stride bytes.
        matrix.append(('framebuffer',{'FRAME_WIDTH':1920,'FRAME_HEIGHT':1080,
                                      'STEP_X':20,'STEP_Y':20,'EXTENDED':0},[12345]))
        matrix.append(('framebuffer',{},[12345]))
        matrix.append(('framebuffer',{'MEM_HALF':7,'VIDEO_HALF':11,'FRAME_WIDTH':383},[67891]))
        for p,v in [(5,7),(7,3),(5,131)]:
            matrix.append(('time',{'P_HALF':p,'VIDEO_HALF':v},[None]))
        for mem,video in [(5,7),(7,3),(5,19)]:
            matrix.append(('a_bridge',{'MEM_HALF':mem,'VIDEO_HALF':video},[12345]))
        for half in [3,7,131]:matrix.append(('apb',{'P_HALF':half},[None]))
        for mem, video in [(5, 7), (7, 3), (5, 131)]:
            matrix.append(('boundary', {'MEM_HALF': mem, 'VIDEO_HALF': video},
                           [12345, 67891, 20261024]))
            matrix.append(('vendor', {'MEM_HALF': mem, 'VIDEO_HALF': video},
                           [12345, 67891, 20261024]))
        for name, params, seeds in matrix:
            top = 'tb_c2_' + name
            suffix = ''.join('_' + k.lower() + str(v) for k, v in params.items())
            executable = BUILD / (top + suffix + '.vvp')
            args = [str(ivl), '-g2012', '-Wall', '-s', top, '-o', str(executable)]
            args += [f'-P{top}.{k}={v}' for k, v in params.items()]
            # Icarus spawns a Windows command internally. Relative source names
            # keep it below cmd.exe's 8191-character limit as the suite grows.
            args += [str(p.relative_to(ROOT)) for p in [*rtl, *sim]]
            if name=='cache':args.append('build/c2/vendor_datacache.v')
            compiled = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            compiler_log = LOGS / (top + suffix + '_compile.log')
            compiler_log.write_text(compiled.stdout + compiled.stderr, encoding='utf-8')
            if compiled.returncode or re.search(r'\bwarning\b|\berror\b', compiled.stderr, re.I):
                raise RuntimeError(f'{top} compile failure/warning: {compiler_log}')
            for seed in seeds:
                key = top + suffix + (f'_seed{seed}' if seed is not None else '')
                case = {'name': key, 'status': 'RUNNING', 'parameters': params, 'ddr_seed': seed,
                        'compiler_log': compiler_log.relative_to(ROOT).as_posix()}
                record['tests'].append(case)
                save()
                command = [str(vvp), str(executable)] + ([f'+SEED={seed}'] if seed is not None else [])
                result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900 if name=='framebuffer' else (300 if name=='video' else 90),cwd=BUILD)
                output = result.stdout + result.stderr
                logfile = LOGS / (key + '.log')
                logfile.write_text(output, encoding='utf-8')
                passed = result.returncode == 0 and f'PASS {top} ' in output and 'FATAL' not in output
                case.update(status='PASS' if passed else 'FAIL', exit_code=result.returncode,
                            log=logfile.relative_to(ROOT).as_posix(),
                            evidence=[line for line in output.splitlines() if line.startswith('PASS ')])
                save()
                print(key + ': ' + case['status'], flush=True)
                if not passed:
                    raise RuntimeError(output)
        audited = subprocess.run([sys.executable, str(ROOT / 'tools/audit_c2_baselines.py')],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        (LOGS / 'baseline_audit.log').write_text(audited.stdout + audited.stderr, encoding='utf-8')
        if audited.returncode:
            raise RuntimeError(audited.stdout + audited.stderr)
        record['baseline_audit'] = 'projects/06_soc_c2/BASELINE_AUDIT.json'
        for label,command,timeout in [
            ('vendor_audit',[sys.executable,str(ROOT/'tools/audit_c2_vendor.py')],30),
            ('host_driver_test',['cmd','/c',str(ROOT/'tools/build_c2_host.cmd')],60),
            ('riscv_compile',[sys.executable,str(ROOT/'tools/check_c2_riscv.py')],180)]:
            checked=subprocess.run(command,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout,cwd=ROOT)
            (LOGS/(label+'.log')).write_text(checked.stdout+checked.stderr,encoding='utf-8')
            record[label]='PASS' if checked.returncode==0 else 'FAIL'
            if checked.returncode:raise RuntimeError(checked.stdout+checked.stderr)
            print(label+': PASS',flush=True)
        for filename, expected in record['source_sha256'].items():
            if sha(ROOT / filename) != expected:
                raise RuntimeError('Source changed during regression: ' + filename)
        record['status'] = 'PASS'
        record['passed'] = len(record['tests'])
        print(f"PASS C2 regression: {record['passed']} runs. Board/PHY/performance remain unverified.")
    except Exception as exc:
        record['status'] = 'FAIL'
        record['error'] = str(exc)
        print(str(exc), file=sys.stderr)
    record['finished'] = datetime.now(timezone.utc).isoformat()
    save()
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
