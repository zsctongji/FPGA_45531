"""Build a small camera-geometry observer; leave model/DMA firmware frozen."""
from pathlib import Path
import hashlib,json,os,subprocess
R=Path(__file__).resolve().parents[1];O=R/'firmware/c9_camera_geometry'
BSP=R/'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml';G=R/'tools/riscv_gcc/13.4.0'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 O.mkdir(exist_ok=True)
 base=R/'team_work/03_ai_soc/c9_live/firmware/dma_main.c'
 text=base.read_text();start=text.index('static int snapshot(');end=text.index('static int kick(')
 # Reuse exact bounded APB snapshots/map probe from the qualified DMA diagnostic.
 helpers=text[text.index('static void str('):text.index('static int snapshot(')]+text[start:end]
 header='#include <stdint.h>\n#include "bsp.h"\n#include "c2_driver.h"\n#include "build_id.h"\n#define C9BASE (IO_APB_SLAVE_0_INPUT+0xe000u)\n'
 body='''
int main(void){
 bsp_init();str("C9|BOOT mode=geometry version=" C9_GEOMETRY_BUILD_ID "\\r\\n");
 if(check_map() || snapshot("before"))return 1;
 put(4,0xc9a70001);if(reg(4)!=5)return fail("source_commit");
 str("C9|GEOMETRY protocol=1 synthetic=0 upper_flags=width12_height12_seen_complete_clip2\\r\\n");
 uint64_t start=clint_getTime(BSP_CLINT);
 while(clint_getTime(BSP_CLINT)-start<1000000000ULL){}
 if(snapshot("after"))return 1;
 str("C9|DONE mode=geometry version=" C9_GEOMETRY_BUILD_ID "\\r\\n");return 0;
}
'''
 source=O/'main.c';source.write_text(header+helpers+body,newline='\n')
 files=[source,R/'team_work/03_ai_soc/c7_board/start.S',R/'team_work/03_ai_soc/c7_board/link.ld']
 inputs=[*files,base,R/'team_work/03_ai_soc/c2/c2_driver.h',R/'team_work/shared/include/cooperation_v1.h',Path(__file__),*(BSP/'bsp/efinix/EfxSapphireSoc/include').glob('*.h'),*(BSP/'software/standalone/driver').glob('*.h')]
 hashes={p.relative_to(R).as_posix():sha(p) for p in inputs}
 version='c9geom-'+hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
 (O/'build_id.h').write_text('#define C9_GEOMETRY_BUILD_ID "'+version+'"\n')
 hashes[(O/'build_id.h').relative_to(R).as_posix()]=sha(O/'build_id.h')
 env=os.environ.copy();env['PATH']=';'.join(str(G/p) for p in ['bin','libexec/gcc/riscv-none-elf/13.4.0','riscv-none-elf/bin'])+';'+env.get('PATH','')
 def run(cmd):
  q=subprocess.run([str(x) for x in cmd],cwd=R,env=env,capture_output=True,text=True,timeout=180)
  with (O/'build.log').open('a') as f:f.write(subprocess.list2cmdline([str(x) for x in cmd])+'\n'+q.stdout+q.stderr)
  if q.returncode and 'cannot execute' in q.stderr and 'CreateProcess' in q.stderr and any(n in q.stderr for n in ['cc1.exe','cc1plus.exe','collect2.exe']):
   with (O/'build.log').open('a') as f:f.write('RETRY unchanged command after Windows compiler spawn failure\n')
   q=subprocess.run([str(x) for x in cmd],cwd=R,env=env,capture_output=True,text=True,timeout=180)
   with (O/'build.log').open('a') as f:f.write(q.stdout+q.stderr)
  assert q.returncode==0,q.stdout+q.stderr
 elf=O/'c9_geometry.elf'
 run([G/'bin/riscv-none-elf-gcc.exe','-B'+(G/'libexec/gcc/riscv-none-elf/13.4.0').as_posix()+'/', '-B'+(G/'riscv-none-elf/bin').as_posix()+'/',
  '-march=rv32im_zicsr_zifencei','-mabi=ilp32','-O2','-g','-ffreestanding','-fno-builtin','-nostdlib','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
  '-isystem',BSP/'bsp/efinix/EfxSapphireSoc/include','-isystem',BSP/'software/standalone/driver','-I'+str(R/'team_work/03_ai_soc/c2'),'-I'+str(R/'team_work/shared/include'),'-I'+str(O),
  '-T'+str(files[-1]),'-Wl,-Map='+str(O/'c9_geometry.map'),'-o',elf,files[0],files[1]])
 for fmt,suffix in [('binary','bin'),('ihex','hex')]:run([G/'bin/riscv-none-elf-objcopy.exe','-O',fmt,elf,O/('c9_geometry.'+suffix)])
 record=dict(status='PASS_COMPILE_ONLY',version=version,entry='0x01000000',board_test_passed=False,scope='Read-only camera geometry after 10s source RUN; DONE means capture complete, not camera acceptance',
  source_sha256=hashes,artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in [elf,*[O/('c9_geometry.'+s) for s in ['bin','hex','map']]]})
 (O/'BUILD_RECORD.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(status=record['status'],version=version,bin=record['artifacts']['c9_geometry.bin']),indent=2))
if __name__=='__main__':main()
