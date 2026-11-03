"""Build an isolated freestanding C2 DMA/cache/ownership board diagnostic."""
from pathlib import Path
import hashlib,json,os,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'firmware/c9_dma_diag';OUT.mkdir(parents=True,exist_ok=True)
BSP=ROOT/'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml';GCC=ROOT/'tools/riscv_gcc/13.4.0'
files=[ROOT/'team_work/03_ai_soc/c9_live/firmware/dma_main.c',ROOT/'team_work/03_ai_soc/c7_board/start.S',ROOT/'team_work/03_ai_soc/c7_board/link.ld',ROOT/'team_work/03_ai_soc/c2/c2_driver.c',ROOT/'team_work/03_ai_soc/c2/c2_sapphire.c',ROOT/'team_work/shared/src/cooperation_v1.c']
inputs=files+[ROOT/'team_work/03_ai_soc/c2/c2_driver.h',ROOT/'team_work/03_ai_soc/c2/c2_sapphire.h',ROOT/'team_work/shared/include/cooperation_v1.h',Path(__file__),*(BSP/'bsp/efinix/EfxSapphireSoc/include').glob('*.h'),*(BSP/'software/standalone/driver').glob('*.h')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();hashes={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
version='c9dma-'+hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
(OUT/'build_id.h').write_text('#define C9_DMA_BUILD_ID "'+version+'"\n')
env=os.environ.copy();env['PATH']=';'.join(str(GCC/p) for p in ['bin','libexec/gcc/riscv-none-elf/13.4.0','riscv-none-elf/bin'])+';'+env.get('PATH','');os.environ['PATH']=env['PATH']
elf=OUT/'c9_dma.elf';cmd=[str(GCC/'bin/riscv-none-elf-gcc.exe'),'-B'+(GCC/'libexec/gcc/riscv-none-elf/13.4.0').as_posix()+'/', '-B'+(GCC/'riscv-none-elf/bin').as_posix()+'/', '-march=rv32im_zicsr_zifencei','-mabi=ilp32','-O2','-g','-ffreestanding','-fno-builtin','-nostdlib','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
'-isystem',str(BSP/'bsp/efinix/EfxSapphireSoc/include'),'-isystem',str(BSP/'software/standalone/driver'),'-I'+str(ROOT/'team_work/03_ai_soc/c2'),'-I'+str(ROOT/'team_work/shared/include'),'-I'+str(OUT),'-T'+str(ROOT/'team_work/03_ai_soc/c7_board/link.ld'),'-Wl,-Map='+str(OUT/'c9_dma.map'),'-o',str(elf),*[str(p) for p in files if p.suffix!='.ld']]
r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(OUT/'build.log').write_bytes(r.stdout)
if r.returncode:raise SystemExit(r.stdout.decode(errors='replace'))
subprocess.run([str(GCC/'bin/riscv-none-elf-objcopy.exe'),'-O','binary',str(elf),str(OUT/'c9_dma.bin')],env=env,check=True)
record=dict(status='PASS_COMPILE_ONLY',version=version,entry='0x01000000',source_sha256=hashes,artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in [elf,OUT/'c9_dma.bin',OUT/'c9_dma.map']},board_test_passed=False,scope='Hardware test-pattern C2 DMA, stale-cache negative/positive and lease ownership; not a real camera test')
(OUT/'BUILD_RECORD.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:record[k] for k in ['status','version','artifacts']}))
