"""Archive the verified RV32 backend objects; this is a link library, not a bitstream."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    report=json.loads((ROOT/'logs/c2_riscv_compile.json').read_text())
    assert report['status']=='PASS'
    stems=['cooperation_v1','c3_hal','c3_shared_time','c3_peripheral','c3_sapphire_peripheral','c3_thermal_publish']
    items=[x for x in report['objects'] if Path(x['object']).stem in stems]
    assert len(items)==6
    for x in items:
        assert sha(ROOT/x['source'])==x['source_sha256'] and sha(ROOT/x['object'])==x['sha256']
    out=ROOT/'firmware/c3_peripheral_backend';out.mkdir(exist_ok=True)
    lib=out/'libc3_peripheral_rv32.a';tool=ROOT/'tools/riscv_gcc/13.4.0/bin/riscv-none-elf-ar.exe'
    subprocess.run([str(tool),'rcs',str(lib),*[str(ROOT/x['object']) for x in items]],check=True)
    nm=tool.with_name('riscv-none-elf-nm.exe');r=subprocess.run([str(nm),'-g','--defined-only',str(lib)],check=True,capture_output=True,text=True)
    for symbol in ['c3_peripheral_bind','c3_peripheral_recover','c3_sapphire_peripheral_bind','c3_publish_thermal','c3_now_ms']:
        assert symbol in r.stdout,symbol
    headers=[*sorted((ROOT/'team_work/03_ai_soc/c3_hal').glob('*.h')),ROOT/'team_work/shared/include/cooperation_v1.h',ROOT/'team_work/03_ai_soc/c2/c2_driver.h']
    record={'status':'PASS','scope':'RV32IM link library, HAL C interface rev2, serialized ABI v1 unchanged',
            'hardware_executed':False,'objects':items,'artifact':{'path':lib.relative_to(ROOT).as_posix(),'bytes':lib.stat().st_size,'sha256':sha(lib)},
            'header_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in headers},
            'packager_sha256':sha(Path(__file__))}
    (out/'MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n')
    (ROOT/'logs/c3_backend_library.json').write_text(json.dumps(record,indent=2)+'\n')
    print('PASS RV32 C3 library: '+str(lib.stat().st_size)+' bytes; not a board configuration.')
if __name__=='__main__':main()
