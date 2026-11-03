"""Offline ownership audit. Never configures GPIO, JTAG, UART or board power.

Separate complete audit execution from physical integration readiness. Existing
standalone images are alternatives, not simultaneous electrical drivers. Their
overlaps become conflicts only when merging their owners into one final image.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
A_SHA = '46fa61dcf79d6146f073ff8dc5b0095b6eb62b2691923e922ede3008290a1dfd'
B_SHA = '3fea1eeae8d124859ad1655ec68a81738d6f5cd26237210a1a0bd9d3aaf30c0c'
PADS = {'sensor_scl': ('B3', 'GPIOL_04'), 'sensor_sda': ('C3', 'GPIOL_06'),
        'buzzer': ('B5', 'GPIOL_10')}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def local(tag):
    return tag.split('}')[-1]


def package_lookup(data):
    result = {}
    for e in ET.fromstring(data).iter():
        if local(e.tag) != 'package_map':
            continue
        pad, ball = e.get('pad_name'), e.get('package_pin')
        result[pad] = ball
        # Package DB adds alternate-function suffixes (e.g. _CLK1_P,
        # _CDI31); the GPIO interface DB uses the unsuffixed resource name.
        alias = re.match(r'(GPIO[LRTB](?:_[PN])?_\d+)(?:_|$)', pad)
        if alias:
            base = alias[1]
            if base in result and result[base] != ball:
                raise ValueError(f'Ambiguous GPIO/package alias: {base}')
            result[base] = ball
    return result


def parse(data, package):
    tree = ET.fromstring(data)
    gpios = []
    for e in tree.iter():
        if local(e.tag) == 'comp_gpio':
            g = dict(e.attrib)
            g['package_pin'] = package.get(g.get('gpio_def'))
            gpios.append(g)
    owners = collections.defaultdict(list)
    for g in gpios:
        owners[g['gpio_def']].append(g)
    return {'device': tree.get('device_def'), 'gpios': gpios,
            'duplicate_gpio_owners': {k: v for k, v in owners.items() if len(v) > 1},
            'banks': {e.get('name'): e.get('iostd') for e in tree.iter() if local(e.tag) == 'iobank'},
            'plls': [dict(e.attrib) for e in tree.iter() if local(e.tag) == 'pll']}


def overlaps(a, b):
    # Caller rejects duplicate owners first; do not silently collapse duplicates.
    left = {g['gpio_def']: g for g in a['gpios']}
    right = {g['gpio_def']: g for g in b['gpios']}
    rows = []
    for pad in sorted(left.keys() & right.keys()):
        x, y = left[pad], right[pad]
        same = all(x.get(k) == y.get(k) for k in ('name', 'mode', 'io_standard'))
        rows.append({'gpio_def': pad, 'package_pin': x['package_pin'], 'a': x, 'b': y,
                     'classification': 'IDENTICAL_DECLARATION_MUST_COALESCE' if same else 'OWNER_CONFLICT_IF_MERGED'})
    return rows


def self_test():
    def xml(rows):
        return ('<design device_def="Ti60F225">' + ''.join(
            f'<comp_gpio name="{n}" gpio_def="{p}" mode="{m}" io_standard="{v}"/>'
            for n, p, m, v in rows) + '</design>').encode()
    p = {'GPIOR_27': 'D1'}
    a = parse(xml([('led[0]', 'GPIOR_27', 'output', '3.3 V LVCMOS')]), p)
    b = parse(xml([('i_arstn', 'GPIOR_27', 'input', '3.3 V LVCMOS')]), p)
    assert overlaps(a, b)[0]['classification'] == 'OWNER_CONFLICT_IF_MERGED'
    assert overlaps(a, a)[0]['classification'] == 'IDENTICAL_DECLARATION_MUST_COALESCE'
    d = parse(xml([('x', 'GPIOR_27', 'output', '3.3 V LVCMOS'),
                   ('y', 'GPIOR_27', 'input', '3.3 V LVCMOS')]), p)
    assert len(d['duplicate_gpio_owners']['GPIOR_27']) == 2
    v = parse(xml([('led[0]', 'GPIOR_27', 'output', '1.8 V LVCMOS')]), p)
    assert overlaps(a, v)[0]['classification'] == 'OWNER_CONFLICT_IF_MERGED'
    assert not overlaps(a, parse(xml([]), p))
    assert package_lookup(b'<p><package_map pad_name="GPIOL_P_08_CLK1_P" package_pin="J2"/></p>')['GPIOL_P_08'] == 'J2'
    try:
        package_lookup(b'<p><package_map pad_name="GPIOL_04" package_pin="B3"/><package_map pad_name="GPIOL_04_OTHER" package_pin="C3"/></p>')
    except ValueError:
        pass
    else:
        raise AssertionError('Ambiguous package alias accepted')
    return ['output_vs_reset_conflict', 'identical_owner_requires_coalescing',
            'duplicate_in_single_image', 'voltage_mismatch', 'unassigned_is_not_conflict_free',
            'alternate_function_package_alias', 'ambiguous_package_alias_rejected']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--a-archive', type=Path, default=ROOT/'build/team_real_20261031/A_video_source_20261029.zip')
    ap.add_argument('--b-archive', type=Path, default=ROOT/'build/team_real_20261031/B_thermal_dataset_20261030.zip')
    ap.add_argument('--require-ready', action='store_true', help='Exit 2 if physical integration is not ready')
    args = ap.parse_args()
    sources = {}

    def read(path):
        path = path.resolve()
        data = path.read_bytes()
        name = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        sources[name] = sha(data)
        return data

    db = ROOT/'tools/efinity/2026.1/pt/db'
    devicemap = read(db/'devicemap.csv').decode('utf-8-sig')
    device = next(line.split(',') for line in devicemap.splitlines() if line.startswith('Ti60F225,'))
    package_data = read(db/'package'/f'{device[1]}.xml')
    package = package_lookup(package_data)
    for ball, gpio in PADS.values():
        if package.get(gpio) != ball:
            raise ValueError(f'Device database mismatch: {gpio} / {ball}')

    images = {}
    for path, digest, label in [(args.a_archive, A_SHA, 'A_20261029'), (args.b_archive, B_SHA, 'B_20261030')]:
        if sha(read(path)) != digest:
            raise ValueError(f'Unreviewed archive identity: {path}')
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not name.endswith('.peri.xml'):
                    continue
                data = archive.read(name)
                sources[f'{label}:{name}'] = sha(data)
                images[f'{label}:{name}'] = parse(data, package)
    for name in ['01_led/LED_8bit_Test.peri.xml', '02_camera/ti60f225_oob.peri.xml',
                 '03_tinyml/Ti60F225_tinyml_helloworld.peri.xml',
                 '04_camera_preprocess/ti60f225_oob.peri.xml', '05_camera_motion/ti60f225_oob.peri.xml']:
        path = ROOT/'projects'/name
        images[f'local:{name}'] = parse(read(path), package)
    for name, image in images.items():
        if image['device'] != 'Ti60F225' or image['duplicate_gpio_owners']:
            raise ValueError(f'Unsupported device or duplicate GPIO owner: {name}')
        if any(not g['package_pin'] for g in image['gpios']):
            raise ValueError(f'Unresolved GPIO/package mapping in {name}')

    contract_path = ROOT/'projects/06_soc_c2/integration/c3_pad_contract.json'
    contract = json.loads(read(contract_path))
    for role, (ball, gpio) in PADS.items():
        row = next(p for p in contract['pins'] if p['role'] == role)
        if row['package_candidate'] != ball:
            raise ValueError(f'C3 contract changed; review {role}')
    native_path = ROOT/'projects/06_soc_c2/integration/c2_native.xml'
    native = ET.fromstring(read(native_path))
    native_constraints = [e.get('name') for e in native.iter() if local(e.tag) == 'inter_file' and e.get('name')]
    # This version deliberately does not certify arbitrary newly attached files.
    if native_constraints:
        raise ValueError('Native physical constraints added; extend and rerun the audit before acceptance')
    a_name = next(n for n in images if '13_a_display_test/' in n)
    c_name = 'local:03_tinyml/Ti60F225_tinyml_helloworld.peri.xml'
    a, c = images[a_name], images[c_name]
    ac = overlaps(a, c)
    bank_differences = [{'bank': k, 'A': a['banks'][k], 'C': c['banks'][k]}
                        for k in a['banks'].keys() & c['banks'].keys() if a['banks'][k] != c['banks'][k]]
    pll_overlaps = [{'pll_def': x['pll_def'], 'A': x, 'C': y} for x in a['plls'] for y in c['plls']
                    if x['pll_def'] == y['pll_def']]
    pad_owners = {}
    for role, (ball, gpio) in PADS.items():
        pad_owners[role] = {'package_pin': ball, 'gpio_def': gpio, 'owners_by_image': {
            n: [g for g in i['gpios'] if g['gpio_def'] == gpio] for n, i in images.items()}}
    blockers = [
        'Native C2 top has no applied physical interface file; C3 contract is reference only.',
        'GPIOR_27: A led[0], B diagnostic led_data[0], C baseline i_arstn must not be merged as separate owners.',
        'Old camera LCD_RST_P/LCD_POWER outputs conflict with sensor SCL/SDA on B3/C3.',
        'A sensor pins are inputs, not a C3 open-drain binding; replace pad owners and route real pad reads/OE.',
        'A/B buzzer_sig and C3 c3_buzzer require one final pad owner, polarity and cold-start verification.',
        'Alarm LED physical owner/polarity remains unassigned; existing A/B diagnostic LEDs already own candidate pads.',
        'A/C bank defaults differ on 2B/3A; verify actual supply and used pad standards before merging.',
        'PLL_TL0 and PLL_BR0 have A/C claims; build one reviewed clock/reset plan, not concatenated PLL constraints.',
        'Dedicated MIPI/DDR/clock resources, PCB voltage/pull-ups, continuity, PNR/CDC/timing and buzzer hardware behavior require physical closure.'
    ]
    result = {'audit_execution': 'PASS', 'status': 'REVIEW_REQUIRED', 'physical_constraints_ready': False,
              'board_programmed': False, 'scope': 'Offline comp_gpio ownership across alternative images; A13/C baseline merge comparison and C3 proposed pads. Not a full Interface Designer legality check.',
              'self_tests': self_test(), 'source_sha256': sources,
              'native_interface_files': native_constraints, 'contract_status': contract['status'],
              'pad_owners': pad_owners, 'A_C_gpio_overlaps': ac,
              'A_C_bank_differences': sorted(bank_differences, key=lambda x: x['bank']),
              'A_C_pll_overlaps': pll_overlaps, 'images': images, 'blockers': blockers}
    result['source_sha256']['tools/audit_pin_ownership.py'] = sha(Path(__file__).read_bytes())
    out = ROOT/'logs/pin_ownership_audit_20261031.json'
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    conflicts = [r for r in ac if r['classification'] == 'OWNER_CONFLICT_IF_MERGED']
    print(f'PASS offline audit: {len(images)} images, {len(ac)} A/C shared GPIO pads, {len(conflicts)} incompatible A/C owner; physical readiness REVIEW_REQUIRED. No board I/O.')
    return 2 if args.require_ready else 0


if __name__ == '__main__':
    raise SystemExit(main())
