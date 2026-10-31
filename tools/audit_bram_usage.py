"""Validate measured native map savings and the two physical RAM hierarchies."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    baseline_path = ROOT/'logs/c2_bram_baseline_20261031.json'
    native_path = ROOT/'logs/c2_native_synthesis.json'
    tests_path = ROOT/'logs/c2_selftest.json'
    base, native, tests = map(read, [baseline_path, native_path, tests_path])
    assert native['status'] == 'PASS' and tests['status'] == 'PASS' and tests['passed'] == 53
    for name, digest in tests['source_sha256'].items():
        assert sha(ROOT/name) == digest, f'Stale regression source: {name}'
    fifo_tests = [t for t in tests['tests'] if t['name'].startswith('tb_c2_bram_fifo_')]
    assert len(fifo_tests) == 3 and all(t['status'] == 'PASS' for t in fifo_tests)
    for item in native['sources']:
        allowed = {item['sha256'], item.get('post_tool_sha256', item['sha256'])}
        assert sha(Path(item['path'])) in allowed, f'Stale native input: {item["path"]}'
    for item in native['artifacts']:
        assert sha(Path(item['path'])) == item['sha256'], f'Stale map artifact: {item["path"]}'
    out = ROOT/'projects/06_soc_c2/integration/outflow'
    report_path, netlist_path = out/'c2_native.map.rpt', out/'c2_native.map.v'
    report, netlist = report_path.read_text(errors='replace'), netlist_path.read_text(errors='replace')
    resources = {k: int(re.findall(k+r'\s*:\s*(\d+)', report)[-1]) for k in base['resources']}
    assert resources == native['resources'], 'Native resource report mismatch'
    instances = re.findall(r'\bEFX_RAM10\s+\\(\S+)\s*\(', netlist)
    groups = {}
    for hierarchy in ['c2_full_video/ingress/crossing/memory', 'c2_full_video/framebuffer/output_cdc/memory']:
        groups[hierarchy] = [n for n in instances if n.startswith(hierarchy+'__')]
        assert len(groups[hierarchy]) == 7, f'Expected 7 RAM10 slices: {hierarchy}'
        assert not any(hierarchy in ln and 'Mapping into logic memory block' in ln for ln in report.splitlines())
    assert len(instances) == resources['EFX_RAM10']
    assert resources['EFX_RAM10'] - base['resources']['EFX_RAM10'] == 14
    assert resources['EFX_LUT4'] < base['resources']['EFX_LUT4']
    assert resources['EFX_FF'] < base['resources']['EFX_FF']
    assert resources['EFX_DSP48'] == base['resources']['EFX_DSP48']
    delta = {k: {'before': base['resources'][k], 'after': v,
                 'change': v-base['resources'][k],
                 'reduction_percent': round(100*(base['resources'][k]-v)/base['resources'][k], 3)}
             for k, v in resources.items()}
    result = {'status': 'PASS', 'scope': 'Efinity native map resource comparison and RAM hierarchy audit, plus RTL cycle equivalence/full concurrent regression; no post-map simulation or physical signoff.',
              'board_test_passed': False, 'pnr_passed': False, 'cdc_signoff': False,
              'resources': delta, 'ram_instances': groups,
              'capacity_per_fifo': {'width_bits': 130, 'depth': 64, 'payload_bits': 8320,
                                    'extra_queue_slots': 0, 'ram10_blocks': 7},
              'rtl_runs': tests['passed'], 'fifo_equivalence_cases': [t['name'] for t in fifo_tests],
              'remaining_logic_buffers': ['c2_attachment/core/pixels/memory',
                  'c2_attachment/core/hub/writer/buffer', 'c2_full_video/framebuffer/wbuf',
                  'c2_full_video/framebuffer/rbuf'],
              'source_sha256': {'tools/audit_bram_usage.py': sha(Path(__file__))},
              'report_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in [
                  baseline_path, native_path, tests_path, report_path, netlist_path]}}
    (ROOT/'logs/c2_bram_optimization_20261031.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print('PASS BRAM audit: 14 RAM10 slices, exact 64-word FIFO capacity; LUT/FF savings bound to current native map and 53-run regression.')


if __name__ == '__main__':
    main()
