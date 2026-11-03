"""Prepare/audit an isolated C8 COMB4 comparison. Never access hardware.

The accepted original C8 project, reports and image remain untouched.
"""
from pathlib import Path
import argparse, csv, datetime, hashlib, importlib.util, json, re, shutil
import xml.etree.ElementTree as ET

R = Path(__file__).resolve().parents[1]
B = R / 'projects/08_ddr_diag'
P = R / 'build/c8_comb4_on_20261102'
Q = '{http://www.efinixinc.com/enf_proj}'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p, data): p.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

def normalized_xml(text):
    node = ET.fromstring(text)
    return ET.tostring(node, encoding='unicode')

def timing():
    spec = importlib.util.spec_from_file_location('c8_baseline_check', R/'tools/check_ddr_diag.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.P = P
    mod.OUT = P/'outflow'
    result = mod.timing()
    assert all(v['rows'] == 9 for v in result.values()), 'Missing clock relationships'
    return result

def prepare():
    assert not P.exists(), 'Preserve existing experiment'
    baseline = read(B/'DIAG_MANIFEST.json')
    for n, d in baseline['source_sha256'].items(): assert sha(R/n) == d, n
    original = read(R/'fpga_bitstreams/ddr_diag_100mhz/BUILD_RECORD.json')
    assert original['status'] == 'PASS_OFFLINE_DIAGNOSTIC'
    for n, d in original['artifacts'].items():
        assert sha(B/'outflow'/n) == d['sha256'], n
    P.mkdir(parents=True)
    for n in ['ddr_diag_top.sv', 'ddr_diag.peri.xml', 'ddr_diag.sdc']:
        shutil.copyfile(B/n, P/n)
    shutil.copytree(B/'rtl', P/'rtl')
    text = (B/'ddr_diag.xml').read_text(encoding='utf-8').replace(B.as_posix(), P.as_posix())
    old = '<efx:param name="pack-luts-to-comb4" value="0"'
    assert text.count(old) == 1
    (P/'ddr_diag.xml').write_text(text.replace(old, old.replace('value="0"', 'value="1"')), encoding='utf-8')
    sources = {n.replace(B.relative_to(R).as_posix(), P.relative_to(R).as_posix()): d
               for n, d in baseline['source_sha256'].items()}
    write(P/'DIAG_MANIFEST.json', dict(source_sha256=sources))
    runner = (R/'tools/run_ddr_diag.ps1').read_text(encoding='utf-8-sig')
    runner = runner.replace("'projects/08_ddr_diag'", "'build/c8_comb4_on_20261102'")
    runner = runner.replace('build/ddr_diag/efinity_user', 'build/c8_comb4_on_20261102/efinity_user')
    runner = runner.replace('logs/ddr_diag_', 'build/c8_comb4_on_20261102/ddr_diag_')
    runner = runner.replace('tools/check_ddr_diag.py', 'tools/c8_comb4_control.py')
    runner_path = R/'tools/run_c8_comb4_control.ps1'
    assert not runner_path.exists(), 'Preserve existing runner'
    runner_path.write_text(runner, encoding='utf-8')
    frozen = {n: sha(B/n) for n in ['ddr_diag.xml','ddr_diag.peri.xml','ddr_diag.sdc','DIAG_MANIFEST.json']}
    frozen['tools/check_ddr_diag.py'] = sha(R/'tools/check_ddr_diag.py')
    write(P/'CONTROL_MANIFEST.json', dict(
        status='PREPARED_OFFLINE_ONLY', started=datetime.datetime.now().astimezone().isoformat(),
        controlled_change='C8 pack-luts-to-comb4 0 -> 1 only; original RTL, DDR parameters, pins, clocks and seed retained',
        board_test_passed=False, flash_written=False,
        baseline_project_sha256=frozen, baseline_build_record_sha256=sha(R/'fpga_bitstreams/ddr_diag_100mhz/BUILD_RECORD.json'),
        source_sha256=sources, prepared_xml_sha256=sha(P/'ddr_diag.xml'),
        tool_sha256=sha(Path(__file__)), runner_sha256=sha(runner_path)))
    print('PREPARED C8 COMB4 control; no hardware accessed')

def audit():
    m = read(P/'CONTROL_MANIFEST.json')
    assert sha(Path(__file__)) == m['tool_sha256']
    assert sha(R/'tools/run_c8_comb4_control.ps1') == m['runner_sha256']
    for n, d in m['baseline_project_sha256'].items():
        assert sha(R/n if n.startswith('tools/') else B/n) == d, n
    assert sha(R/'fpga_bitstreams/ddr_diag_100mhz/BUILD_RECORD.json') == m['baseline_build_record_sha256']
    for n, d in m['source_sha256'].items(): assert sha(R/n) == d, n
    current = (P/'ddr_diag.xml').read_text(encoding='utf-8')
    assert sha(P/'ddr_diag.xml') == m['prepared_xml_sha256'] or sha_bytes(current) == m['prepared_xml_sha256'], 'Project changed beyond line endings'
    node = ET.fromstring(current)
    pack = node.find('.//'+Q+'synthesis/'+Q+'param[@name="pack-luts-to-comb4"]')
    assert pack is not None and pack.get('value') == '1'
    reverted = current.replace(P.as_posix(), B.as_posix()).replace(
        '<efx:param name="pack-luts-to-comb4" value="1"', '<efx:param name="pack-luts-to-comb4" value="0"')
    assert normalized_xml(reverted) == normalized_xml((B/'ddr_diag.xml').read_text()), 'Uncontrolled XML changes'
    for n in ['ddr_diag.peri.xml','ddr_diag.sdc']: assert sha(P/n) == sha(B/n), n
    build = read(P/'ddr_diag_build.json')
    assert build['status'] == 'PASS'
    assert {s['path']:s['sha256'] for s in build['sources']} == m['source_sha256']
    assert [s['flow'] for s in build['steps']] == ['interface','map','pnr','pgm']
    for s in build['steps']:
        assert s['status'] == 'PASS'
        for n, d in s['inputs'].items(): assert sha(P/n) == d, n
        for n, d in s['artifacts'].items():
            f = P/'outflow'/n
            assert sha(f) == d and f.stat().st_mtime >= datetime.datetime.fromisoformat(s['started']).timestamp(), n
    assert sha(P/'work_pnr/ddr_diag.lbf') == build['steps'][-1]['routed_lbf_sha256']
    def pins(root):
        lines = [x for x in (root/'outflow/ddr_diag.pinout.csv').read_text(encoding='utf-8-sig').splitlines() if x and not x.startswith('#')]
        return {r['Signal Name']: (r['Pin Number'],r['I/O Bank Voltage']) for r in csv.DictReader(lines) if r['Signal Name']}
    assert pins(P) == pins(B), 'Pin/voltage mismatch'
    names = ['ddr_diag.bit','ddr_diag.hex','ddr_diag.timing.rpt','ddr_diag.place.rpt','ddr_diag.pinout.csv']
    report = dict(status='PASS_OFFLINE_C8_COMB4_ONLY', board_test_passed=False, flash_written=False,
        destructive_memory_test=True, controlled_change=m['controlled_change'], timing=timing(),
        source_sha256=m['source_sha256'], evidence_sha256={
            (P/'outflow'/n).relative_to(R).as_posix():sha(P/'outflow'/n) for n in names})
    for f in [P/'CONTROL_MANIFEST.json',P/'ddr_diag_build.json',Path(__file__),R/'tools/run_c8_comb4_control.ps1']:
        report['evidence_sha256'][f.relative_to(R).as_posix()] = sha(f)
    write(P/'implementation_audit.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['source_sha256','evidence_sha256']},indent=2))

def sha_bytes(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare',action='store_true'); g.add_argument('--timing-only',action='store_true'); g.add_argument('--audit',action='store_true')
    a = ap.parse_args()
    if a.prepare: prepare()
    elif a.timing_only: print('PASS private C8 timing:', timing())
    else: audit()
