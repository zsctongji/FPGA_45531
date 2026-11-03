"""Execute the vendor Makefile command plan using native Windows subprocesses."""
from pathlib import Path
import argparse,concurrent.futures,datetime,hashlib,json,os,shlex,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/software/standalone/tinyml_c9'
GCC=ROOT/'tools/riscv_gcc/13.4.0';MAKE=ROOT/'tools/windows_build_tools/4.4.1/bin/make.exe'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--jobs',type=int,default=2)
    parser.add_argument('--enable-live',action='store_true');parser.add_argument('--verified-map',action='store_true')
    parser.add_argument('--verified-shared-time',action='store_true')
    parser.add_argument('--shared-base',type=lambda s:int(s,0),default=0x09010000);args=parser.parse_args()
    if args.enable_live and not(args.verified_map and args.verified_shared_time):
        parser.error('Live mode requires verified mapping and shared time; no build or hardware access performed.')
    if not 1<=args.jobs<=8:parser.error('--jobs must be 1..8')
    log=ROOT/'logs/firmware_c9_live.log';report=ROOT/'logs/firmware_c9_live.json'
    record={'status':'RUNNING','started':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scope':'Linked C2/C4 firmware; synthetic self-test enabled; live MMIO disabled',
            'board_programmed':False,'board_inference_passed':False,'live_mmio_enabled':args.enable_live,'artifacts':[]}
    if args.enable_live:record['scope']='Linked C2/C4 live-mode firmware build; caller-verified mapping/time; no board execution'
    env=os.environ.copy();env['PATH']=';'.join(str(GCC/p) for p in ['bin','libexec/gcc/riscv-none-elf/13.4.0','riscv-none-elf/bin'])+';'+env.get('PATH','')
    def run(command,timeout=120):
        argv=[str(v) for v in command]
        if argv[0].startswith(str(GCC).replace('\\','/')) and not argv[0].endswith('.exe'):argv[0]+='.exe'
        result=subprocess.run(argv,cwd=APP,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        if result.returncode and 'cannot execute' in result.stderr and 'CreateProcess' in result.stderr and any(x in result.stderr for x in ['cc1.exe','cc1plus.exe','collect2.exe']):
            diagnostic=result.stderr
            record.setdefault('compiler_spawn_retries',[]).append({'command':argv,'diagnostic':diagnostic})
            result=subprocess.run(argv,cwd=APP,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
            result.stderr='RETRY unchanged command after compiler spawn failure:\n'+diagnostic+result.stderr
        return result
    def save():report.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    save()
    try:
        prepare_args=[sys.executable,str(ROOT/'tools/prepare_c9_tinyml.py'),'--shared-base',hex(args.shared_base)]
        for enabled,name in [(args.enable_live,'--enable-live'),(args.verified_map,'--verified-map'),(args.verified_shared_time,'--verified-shared-time')]:
            if enabled:prepare_args.append(name)
        prepared=subprocess.run(prepare_args,cwd=ROOT,capture_output=True,text=True,timeout=60)
        if prepared.returncode:raise RuntimeError(prepared.stdout+prepared.stderr)
        record['version']=json.loads((APP/'C9_PREPARATION.json').read_text())['version']
        prefix=(GCC/'bin/riscv-none-elf-').as_posix();crt=[]
        for name in ['crtbegin.o','crtend.o']:
            result=run([prefix+'gcc.exe','-march=rv32im_zicsr_zifencei','-mabi=ilp32','-print-file-name='+name])
            path=Path(result.stdout.strip())
            if result.returncode or not path.is_file():raise RuntimeError('Missing '+name)
            crt.append(path.as_posix())
        plan=run([MAKE,'-n','-B','all','BSP=efinix/EfxSapphireSoc','OBJDIR=build_ours',
                  'RISCV_BIN='+prefix,'RISCV_CC='+prefix+'gcc','RISCV_CXX='+prefix+'g++',
                  'MARCH=rv32im_zicsr_zifencei','MABI=ilp32',
                  'LIBS='+crt[0]+' ../common/tinyml_lib.a '+crt[1],'CFLAGS_ARGS=-g0',
                  'SHELL='+Path(os.environ['WINDIR'],'System32/cmd.exe').as_posix()])
        if plan.returncode:raise RuntimeError(plan.stdout+plan.stderr)
        (APP/'build_ours/command_plan.txt').write_text(plan.stdout,encoding='utf-8')
        commands=[shlex.split(line) for line in plan.stdout.splitlines() if line.startswith(prefix)]
        compilations=[c for c in commands if '-c' in c]
        links=[c for c in commands if '-c' not in c and c[0].endswith('g++')]
        if not compilations or len(links)!=1:raise RuntimeError('Vendor build plan not recognized')
        record['native_compile_units']=len(compilations);save()
        def compile_one(command):return command,run(command,180)
        with log.open('w',encoding='utf-8') as stream:
            stream.write('Vendor Makefile plan; native subprocesses; no make-shell compiler launch.\n')
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
                for count,(command,result) in enumerate(executor.map(compile_one,compilations),1):
                    stream.write('COMMAND '+subprocess.list2cmdline(command)+'\n'+result.stdout+result.stderr);stream.flush()
                    if result.returncode:raise RuntimeError('Compile failed: '+command[-1]+'\n'+result.stderr[-2000:])
                    if count%20==0 or count==len(compilations):print(f'C24 compile {count}/{len(compilations)}',flush=True)
            link=links[0];response=APP/'build_ours/link.rsp'
            response.write_text('\n'.join(subprocess.list2cmdline([arg]) for arg in link[1:]),encoding='utf-8')
            result=run([link[0],'@'+str(response)],180);stream.write(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError('Link failed: '+result.stderr[-2000:])
            elf=APP/'build_ours/tinyml_c9.elf'
            for fmt,suffix in [('ihex','hex'),('binary','bin')]:
                result=run([prefix+'objcopy.exe','-O',fmt,elf,elf.with_suffix('.'+suffix)])
                if result.returncode:raise RuntimeError(result.stderr)
            symbols=run([prefix+'nm.exe',elf]).stdout
            required=['c24_process_next','c2_poll_copy','c2_sapphire_bind','c4_tflm_infer','c3_shared_time_bind','c3_shared_now_ms']
            if not all(name in symbols for name in required):raise RuntimeError('Required linked entrypoint missing')
            record['linked_entrypoints']=required
            info=run([prefix+'readelf.exe','-h','-A',elf])
            if info.returncode or 'ELF32' not in info.stdout or 'RISC-V' not in info.stdout or '0x1000' not in info.stdout:raise RuntimeError('Unexpected ELF architecture/entry')
            (ROOT/'logs/firmware_c9_live_elf.txt').write_text(info.stdout,encoding='utf-8')
        if (APP/'build_ours/tinyml_c9.bin').stat().st_size>4194304:raise RuntimeError('Exceeds boot copy size')
        output=ROOT/'firmware/c9_live_person_detect';output.mkdir(exist_ok=True)
        for suffix in ['elf','bin','hex','map']:
            path=APP/('build_ours/tinyml_c9.'+suffix);dest=output/path.name;shutil.copy2(path,dest)
            record['artifacts'].append({'path':dest.relative_to(ROOT).as_posix(),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
        preparation=json.loads((output/'C9_INPUT_MANIFEST.json').read_text())
        sources=dict(preparation['source_hashes']);sources[Path(__file__).relative_to(ROOT).as_posix()]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        canonical=dict(status='PASS_COMPILE_ONLY',version=record['version'],entry='0x1000',source_sha256=sources,
            artifacts={Path(a['path']).name:{'bytes':a['bytes'],'sha256':a['sha256']} for a in record['artifacts']},board_test_passed=False,
            scope='C9 camera acceptance firmware; DDR mapping and shared time must pass runtime checks before source RUN')
        (output/'BUILD_RECORD.json').write_text(json.dumps(canonical,indent=2)+'\n')
        record['status']='PASS';print(f'PASS linked C9 firmware: ELF32 RV32IM entry 0x1000; live_enabled={args.enable_live}; runtime mapping/time gates; no board execution.')
    except Exception as exc:record['status']='FAIL';record['error']=str(exc);print(str(exc),file=sys.stderr)
    record['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
    return 0 if record['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
