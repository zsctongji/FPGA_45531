"""Compile C2 RX-only backend for the pinned RV32 core and audit its instructions."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]


def main():
    gcc=ROOT/'tools/riscv_gcc/13.4.0'
    out=ROOT/'build/c2/riscv';out.mkdir(parents=True,exist_ok=True)
    log=ROOT/'logs/c2_riscv_compile.log'
    report=ROOT/'logs/c2_riscv_compile.json'
    record={'status':'RUNNING','started':datetime.now(timezone.utc).isoformat(),
            'scope':'RV32 object compilation and instruction inspection; no firmware execution',
            'board_test_passed':False,'linked_firmware':False,'objects':[]}
    env=os.environ.copy()
    env['PATH']=';'.join(str(gcc/p) for p in ['bin','libexec/gcc/riscv-none-elf/13.4.0','riscv-none-elf/bin'])+';'+env.get('PATH','')
    sources=['team_work/shared/src/cooperation_v1.c','team_work/03_ai_soc/c2/c2_driver.c',
             'team_work/03_ai_soc/c2/c2_sapphire.c']
    bsp=ROOT/'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/bsp/efinix/EfxSapphireSoc/include'
    includes=['-I'+str(ROOT/'team_work/shared/include'),'-I'+str(ROOT/'team_work/03_ai_soc/c2'),'-I'+str(bsp)]
    try:
        report.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        with log.open('w',encoding='utf-8') as stream:
            for source in sources:
                path=ROOT/source;obj=out/(path.stem+'.o')
                command=[str(gcc/'bin/riscv-none-elf-gcc.exe'),'-c','-g0','-Os','-std=c11',
                         '-Wall','-Wextra','-Werror','-march=rv32im_zicsr_zifencei','-mabi=ilp32',*includes,
                         str(path),'-o',str(obj)]
                result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=60)
                stream.write(result.stdout+result.stderr)
                if result.returncode:raise RuntimeError('RISC-V compile failed: '+source)
                record['objects'].append({'source':source,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                          'object':obj.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(obj.read_bytes()).hexdigest()})
            dumped=subprocess.run([str(gcc/'bin/riscv-none-elf-objdump.exe'),'-d',str(out/'c2_sapphire.o')],
                                  env=env,capture_output=True,text=True,timeout=30)
            if dumped.returncode:raise RuntimeError(dumped.stderr)
            (out/'c2_sapphire.asm').write_text(dumped.stdout,encoding='utf-8')
            if not re.search(r'0ff0000f[^\n]*\n[^\n]*0000500f[^\n]*\n[^\n]*0ff0000f',dumped.stdout,re.I):
                raise RuntimeError('Missing fence / vendor whole-D-cache invalidate / fence sequence')
        record['cache_sequence']='fence iorw,iorw; .word 0x0000500f; fence iorw,iorw'
        record['status']='PASS'
        print('PASS C2 RV32: 3 objects; exact fence/invalidate/fence sequence verified; not executed on board.')
    except Exception as exc:
        record['status']='FAIL';record['error']=str(exc);print(str(exc))
    record['finished']=datetime.now(timezone.utc).isoformat()
    report.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return 0 if record['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
