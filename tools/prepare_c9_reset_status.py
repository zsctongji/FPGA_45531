"""Create a private reset-status derivative of qualified C9; no board access.

Only the two confirmed status LEDs and the boot-ROM first instruction
change. Keep C9's clocks, pin locations, DDR parameters and data path intact.
"""
from pathlib import Path
import hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'projects/09_c7_live_acceptance'
P = ROOT / 'build/c9_reset_status_20261101'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    audit = json.loads((ROOT / 'logs/soc_live_audit.json').read_text())
    assert audit['status'] == 'PASS_OFFLINE_LIVE_IMPLEMENTATION'
    for field in ['evidence_sha256', 'source_sha256']:
        for name, digest in audit[field].items():
            assert sha(ROOT / name) == digest, name
    assert not P.exists(), 'Preserve any existing diagnostic run'
    shutil.copytree(BASE, P)
    xml = P / 'soc_physical.xml'
    xml.write_text(xml.read_text().replace(BASE.as_posix(), P.as_posix()), newline='\n')
    core = P / 'physical_soc_core.v'
    text = core.read_text()
    needle = 'output wire integrated_reset,'
    assert text.count(needle) == 1
    text = text.replace(needle, needle + '\noutput wire [1:0] c9_reset_status,', 1)
    needle = 'assign integrated_reset=io_systemReset;'
    assert text.count(needle) == 1
    text = text.replace(needle, needle + '\nassign c9_reset_status={io_systemReset,cal_done};', 1)
    core.write_text(text, newline='\n')
    top = P / 'soc_physical_top.sv'
    text = top.read_text()
    needle = 'physical_soc_core soc(\n'
    assert text.count(needle) == 1
    text = text.replace(needle, 'wire [1:0] c9_reset_status;\n' + needle + '.c9_reset_status(c9_reset_status),\n', 1)
    needle = "assign led={6'b0,c3_alarm,fault2};"
    assert text.count(needle) == 1
    text = text.replace(needle, '''// Diagnostic only: confirmed LED0 cal_done, LED1 internal reset.
// Preserve the other six outputs at their original constant value.
assign led={6'b0,c9_reset_status};''', 1)
    top.write_text(text, newline='\n')
    for i in range(4):
        path = P / f'EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol{i}.bin'
        words = path.read_text().split()
        assert len(words) == 1024
        words[0] = format(0x6f if i == 0 else 0, '08b')
        path.write_text('\n'.join(words) + '\n')
    # Use the original mapped-name binder without changing the qualified report.
    source = (ROOT / 'tools/generate_physical_cdc.py').read_text()
    old = "ROOT/'logs/soc_physical_cdc_binding.json'"
    assert source.count(old) == 1
    source = source.replace(old, "ROOT/'build/c9_reset_status_20261101/cdc_binding.json'")
    (P / 'bind_cdc.py').write_text(
        "from pathlib import Path\n" +
        "ns={'__name__':'reset_status_binder','__file__':" + repr(str(ROOT / 'tools/generate_physical_cdc.py')) + "}\n" +
        'exec(compile(' + repr(source) + ",'reset_status_binder','exec'),ns)\n" +
        "ns['P']=Path(" + repr(str(P)) + ")\nns['main']()\n")
    record = dict(status='PREPARED_ONLY', flash_written=False, board_programmed=False,
                  base_audit_sha256=sha(ROOT / 'logs/soc_live_audit.json'),
                  base_bit_sha256=sha(BASE / 'outflow/soc_physical.bit'),
                  delta='Only LED0 cal_done, LED1 internal reset, ROM first instruction 0000006f',
                  source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [core, top, xml]})
    (P / 'RESET_STATUS_RECORD.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))

if __name__ == '__main__':
    main()
