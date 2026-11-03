"""Check a private, reset-observation derivative before temporary SRAM use."""
from pathlib import Path
import hashlib, json, re, datetime
from audit_soc_physical import timing_summary, bus_summary

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'projects/09_c7_live_acceptance'
P = ROOT / 'build/c9_reset_status_20261101'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest = json.loads((P / 'RESET_STATUS_RECORD.json').read_text())
    audit = json.loads((ROOT / 'logs/soc_live_audit.json').read_text())
    assert sha(ROOT / 'logs/soc_live_audit.json') == manifest['base_audit_sha256']
    assert sha(BASE / 'outflow/soc_physical.bit') == manifest['base_bit_sha256']
    assert audit['status'] == 'PASS_OFFLINE_LIVE_IMPLEMENTATION'
    for field in ['source_sha256', 'evidence_sha256']:
        for name, digest in audit[field].items():
            assert sha(ROOT / name) == digest, name
    expected_xml = (BASE / 'soc_physical.xml').read_text().replace(BASE.as_posix(), P.as_posix())
    seed = manifest.get('pnr_seed', 1)
    assert seed in [1, 2], 'Only recorded placement seeds are allowed'
    expected_xml = expected_xml.replace('<efx:param name="seed" value="1"', '<efx:param name="seed" value="%d"' % seed, 1)
    for name, digest in manifest['source_sha256'].items():
        if (ROOT / name) == P / 'soc_physical.xml':
            # efx_run rewrites XML with Windows newlines. Permit precisely
            # that serialization change, with no project-option changes.
            assert hashlib.sha256(expected_xml.encode()).hexdigest() == digest
            assert (ROOT / name).read_bytes() in [expected_xml.encode(), expected_xml.replace('\n', '\r\n').encode()]
        else:
            assert sha(ROOT / name) == digest, name
    for name, digest in audit['source_sha256'].items():
        path = ROOT / name
        if path.is_relative_to(BASE) and path.name not in ['physical_soc_core.v', 'soc_physical_top.sv']:
            assert sha(P / path.relative_to(BASE)) == digest, 'Copied dependency ' + name
    assert (P / 'soc_physical.xml').read_text() == expected_xml
    for name in ['soc_physical.peri.xml', 'soc_physical.sdc', 'review_timing.tcl', 'overrides/ddr3_parameter.vh', 'overrides/ddr3_top.v']:
        assert (P / name).read_bytes() == (BASE / name).read_bytes(), name
    core = (BASE / 'physical_soc_core.v').read_text()
    core = core.replace('output wire integrated_reset,', 'output wire integrated_reset,\noutput wire [1:0] c9_reset_status,', 1)
    core = core.replace('assign integrated_reset=io_systemReset;', 'assign integrated_reset=io_systemReset;\nassign c9_reset_status={io_systemReset,cal_done};', 1)
    assert (P / 'physical_soc_core.v').read_text() == core, 'Only expose two existing status signals'
    top = (BASE / 'soc_physical_top.sv').read_text()
    top = top.replace('physical_soc_core soc(\n', 'wire [1:0] c9_reset_status;\nphysical_soc_core soc(\n.c9_reset_status(c9_reset_status),\n', 1)
    top = top.replace("assign led={6'b0,c3_alarm,fault2};", "// Diagnostic only: confirmed LED0 cal_done, LED1 internal reset.\n// Preserve the other six outputs at their original constant value.\nassign led={6'b0,c9_reset_status};", 1)
    assert (P / 'soc_physical_top.sv').read_text() == top, 'Only confirmed LED0/LED1 change'
    for i in range(4):
        name = f'EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol{i}.bin'
        before = (BASE / name).read_text().split()
        after = (P / name).read_text().split()
        assert len(before) == len(after) == 1024
        assert before[1:] == after[1:] and int(after[0], 2) == (0x6f if i == 0 else 0)
    pinrows = lambda p: [line for line in p.read_text(encoding='utf-8-sig').splitlines() if line and not line.startswith('#')]
    assert pinrows(P / 'outflow/soc_physical.pinout.csv') == pinrows(BASE / 'outflow/soc_physical.pinout.csv')
    binding = json.loads((P / 'cdc_binding.json').read_text())
    assert binding['status'] == 'PASS' and binding['pointer_bits'] == 66
    assert sha(P / 'outflow/soc_physical.map.v') == binding['netlist_sha256']
    assert sha(P / 'soc_physical_cdc.sdc') == binding['constraint_sha256']
    timing = timing_summary(P / 'outflow/soc_physical.review_timing.rpt')
    assert all(not value['violations'] for value in timing.values()), timing
    cdc = {corner: bus_summary(P / f'outflow/soc_physical.bus_{corner}.rpt', binding) for corner in ['setup', 'hold']}
    for flow in ['map', 'pnr', 'sta_tclsh', 'pgm']:
        data = (P / (flow + '.log')).read_bytes()
        text = data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8-sig', errors='replace')
        assert 'FAIL' not in text and 'Failed to run command' not in text, flow
        if flow != 'sta_tclsh':
            assert re.search(r'\b' + flow + r'\s*:\s*PASS\b', text), flow
        else:
            assert 'No bus skew paths found' not in text
    evidence = [P / 'work_pnr/soc_physical.lbf', P / 'outflow/soc_physical.bit', P / 'outflow/soc_physical.hex', P / 'outflow/soc_physical.review_timing.rpt', P / 'outflow/soc_physical.bus_setup.rpt', P / 'outflow/soc_physical.bus_hold.rpt', P / 'RESET_STATUS_RECORD.json', Path(__file__)]
    source_time = max((ROOT / name).stat().st_mtime for name in manifest['source_sha256'] if (ROOT / name).suffix != '.xml')
    if manifest.get('retry_started'):
        source_time = max(source_time, datetime.datetime.fromisoformat(manifest['retry_started']).timestamp())
    assert all(p.stat().st_mtime >= source_time for p in evidence[:6]), 'Stale copied implementation output'
    result = dict(status='PASS_OFFLINE_RESET_STATUS_DIAGNOSTIC', board_test_passed=False,
                  flash_written=False, timing=timing, cdc=cdc,
                  base_audit_sha256=manifest['base_audit_sha256'],
                  diagnostic_only=True, source_sha256={name:sha(ROOT / name) for name in manifest['source_sha256']},
                  prepared_source_sha256=manifest['source_sha256'],
                  evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in evidence})
    (P / 'implementation_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
