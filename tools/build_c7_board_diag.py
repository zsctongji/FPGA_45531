"""Build the small C7 CPU DDR/cache diagnostic; no hardware is accessed."""
from pathlib import Path
import datetime,hashlib,json,subprocess,os
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'team_work/03_ai_soc/c7_board'
OUT=ROOT/'firmware/c7_board_diag';OUT.mkdir(parents=True,exist_ok=True)
BSP=ROOT/'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml'
TOOL=ROOT/'tools/riscv_gcc/13.4.0/bin/riscv-none-elf-'
files=[SRC/'main.c',SRC/'start.S',SRC/'link.ld',Path(__file__),ROOT/'team_work/03_ai_soc/c2/c2_driver.h',ROOT/'team_work/shared/include/cooperation_v1.h',*(BSP/'bsp/efinix/EfxSapphireSoc/include').glob('*.h'),*(BSP/'software/standalone/driver').glob('*.h')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
version='c7diag-'+hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
(OUT/'build_id.h').write_text('#define C7_DIAG_BUILD_ID "'+version+'"\n',encoding='utf-8')
elf=OUT/'c7_board_diag.elf';binary=elf.with_suffix('.bin')
env=os.environ.copy();gccroot=ROOT/'tools/riscv_gcc/13.4.0'
env['PATH']=';'.join(str(gccroot/p) for p in ['bin','libexec/gcc/riscv-none-elf/13.4.0','riscv-none-elf/bin'])+';'+env.get('PATH','')
os.environ['PATH']=env['PATH']
cmd=[str(TOOL)+'gcc.exe','-B'+(gccroot/'libexec/gcc/riscv-none-elf/13.4.0').as_posix()+'/', '-B'+(gccroot/'riscv-none-elf/bin').as_posix()+'/',
     '-march=rv32im_zicsr_zifencei','-mabi=ilp32','-O2','-g','-ffreestanding','-fno-builtin','-nostdlib','-Wall','-Wextra','-Werror','-Wno-unused-function',
     '-isystem',str(BSP/'bsp/efinix/EfxSapphireSoc/include'),'-isystem',str(BSP/'software/standalone/driver'),'-I'+str(ROOT/'team_work/03_ai_soc/c2'),'-I'+str(ROOT/'team_work/shared/include'),'-I'+str(OUT),
     '-T'+str(SRC/'link.ld'),'-Wl,-Map='+str(elf.with_suffix('.map')),'-o',str(elf),str(SRC/'start.S'),str(SRC/'main.c')]
r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(OUT/'build.log').write_bytes(r.stdout)
if r.returncode:raise SystemExit(r.stdout.decode(errors='replace'))
subprocess.run([str(TOOL)+'objcopy.exe','-O','binary',str(elf),str(binary)],cwd=ROOT,env=env,check=True)
record=dict(status='PASS_COMPILE_ONLY',version=version,started=datetime.datetime.now().astimezone().isoformat(),entry='0x01000000',stack_top='0x01010000',
            tested_ranges=[dict(base=hex(b),bytes=262144) for b in [0x02000000,0x04000000,0x06000000,0x07000000]],checked_words=1048576,
            flash_written=False,board_test_passed=False,source_sha256=hashes,
            artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in [elf,binary,elf.with_suffix('.map')]},command=cmd,
            scope='CPU-side four-pattern 1MiB DDR test with D-cache invalidate/refill and byte/halfword lanes; external-DMA stale-cache negative test remains separate')
(OUT/'BUILD_RECORD.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:record[k] for k in ['status','version','entry','artifacts']}))
