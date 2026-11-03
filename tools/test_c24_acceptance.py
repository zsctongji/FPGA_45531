"""Offline acceptance-tool tests; never opens a port or executes board firmware."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = {'status': 'RUNNING', 'board_inference_passed': False,
              'scope': 'Synthetic C24 parser/CLI fixtures, actual vendor formatter, PowerShell syntax and pre-open capture guard; no serial or board execution',
              'steps': [], 'source_sha256': {}}
    sources = ['tools/check_c24_uart.py', 'tools/capture_c24_uart.ps1',
               'tools/test_c24_acceptance.py', 'team_work/03_ai_soc/tests/test_c24_parser.py',
               'tools/test_c24_format.cmd','team_work/03_ai_soc/tests/test_c24_uart_format.cc',
               'team_work/03_ai_soc/c24/c24_log_format.h',
               'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/software/standalone/tinyml_pdti8/src/tensorflow/lite/micro/micro_string.cc']
    for name in sources:
        report['source_sha256'][name] = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    log = ROOT/'logs/c24_acceptance_tests.log'
    try:
        with log.open('w', encoding='utf-8') as stream:
            commands = [
                ('parser_fixtures', [sys.executable, str(ROOT/'team_work/03_ai_soc/tests/test_c24_parser.py')]),
                ('actual_vendor_formatter', ['cmd','/c',str(ROOT/'tools/test_c24_format.cmd')]),
                ('capture_syntax', ['powershell', '-NoProfile', '-Command',
                 "$parseTokens=$null;$parseErrors=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('tools/capture_c24_uart.ps1',[ref]$parseTokens,[ref]$parseErrors);if($parseErrors.Count){$parseErrors;exit 1};Write-Output 'PASS capture syntax'"]),
                ('capture_pre_open_guard', ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
                 "try {& './tools/capture_c24_uart.ps1' -Port COM1;exit 1} catch {if($_.Exception.Message -like '*Confirm the physical board UART*'){Write-Output 'PASS rejected before opening port';exit 0};throw}"]),
            ]
            for name, command in commands:
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                        encoding='utf-8', errors='replace', timeout=30)
                stream.write(name+'\n'+result.stdout+result.stderr)
                report['steps'].append({'name': name, 'status': 'PASS' if result.returncode == 0 else 'FAIL'})
                if result.returncode:
                    raise RuntimeError(name+': '+result.stdout+result.stderr)
            report['status'] = 'PASS'
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        report.update(status='FAIL', error=str(exc))
    (ROOT/'logs/c24_acceptance_tests.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
