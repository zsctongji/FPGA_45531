"""Run C6's 53 functional cases against C7 BRAM overrides in an isolated clone.
Original C6 HDL, baseline reports, generated native project and CPU firmware are
not rewritten. The source transformations and every cloned input are hashed.
"""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'projects/06_soc_c2'
P=ROOT/'projects/07_soc_physical'
B=ROOT/'build/physical_20261031/c2_regression'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    provenance={}
    for folder in ['rtl','sim','a_side']:
        (B/folder).mkdir(parents=True,exist_ok=True)
        for src in (BASE/folder).iterdir():
            if not src.is_file():continue
            use=P/'overrides'/src.name if folder=='rtl' and (P/'overrides'/src.name).is_file() else src
            dst=B/folder/src.name;shutil.copyfile(use,dst)
            provenance[dst.relative_to(ROOT).as_posix()]={'original':src.relative_to(ROOT).as_posix(),'original_sha256':sha(src),'compiled_from':use.relative_to(ROOT).as_posix(),'compiled_sha256':sha(use)}
    # A true independent logic reference, not the new BRAM-backed wrapper.
    ref=(BASE/'rtl/c2_async_fifo.sv').read_text(encoding='utf-8-sig').replace('module c2_async_fifo','module c2_logic_fifo_reference',1)
    (B/'sim/logic_reference.sv').write_text(ref,encoding='utf-8')
    f=B/'sim/tb_c2_bram_fifo.sv';s=f.read_text(encoding='utf-8-sig').replace('c2_async_fifo #','c2_logic_fifo_reference #');f.write_text(s,encoding='utf-8')
    # Explicit short/one-beat read-first collision tests before the long suite.
    tail=(BASE/'sim/tb_c2_video_tail.sv').read_text(encoding='utf-8-sig')
    tail=tail.replace('module tb_c2_video_tail;','module tb_physical_c2_tail #(parameter N=1);').replace('tb_c2_video_tail','tb_physical_c2_tail')
    for x,y in [('.WIDTH(32),.HEIGHT(3)','.WIDTH(16),.HEIGHT(N)'),('awlen!=5','awlen!=N-1'),('arlen!=5','arlen!=N-1'),('count>=6','count>=N'),('count!=6','count!=N'),('n<6','n<N'),('k<6','k<N'),('words!=12','words!=2*N')]:tail=tail.replace(x,y)
    tail=tail.replace('words=6 AWLEN=5 ARLEN=5 writes=1 scans=2 checked_bytes=192','words=%0d reads=%0d BRAM_read_first_safe')
    tail=tail.replace('display_backpressure repeat");','display_backpressure repeat",N,words);')
    (B/'sim/tb_physical_c2_tail.sv').write_text(tail,encoding='utf-8')
    sources=[*sorted((B/'rtl').glob('*.sv')),*sorted((B/'a_side').glob('*.v')),*sorted((B/'sim').glob('*.sv'))]
    filelist=B/'sources.f';filelist.write_text('\n'.join(p.relative_to(ROOT).as_posix() for p in sources)+'\n',encoding='utf-8')
    iv=ROOT/'tools/iverilog/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
    tail_checks=[]
    for beats in [1,6]:
        exe=B/f'tail{beats}.vvp'
        subprocess.run([str(iv),'-g2012','-Wall','-s','tb_physical_c2_tail',f'-Ptb_physical_c2_tail.N={beats}','-o',str(exe),'-f',str(filelist)],check=True,cwd=ROOT)
        r=subprocess.run([str(vvp),str(exe)],capture_output=True,text=True,encoding='utf-8',timeout=30,cwd=B)
        if r.returncode or 'PASS tb_physical_c2_tail ' not in r.stdout:raise ValueError(r.stdout+r.stderr)
        print(r.stdout,flush=True);tail_checks.append({'beats':beats,'status':'PASS','evidence':r.stdout})
    original=ROOT/'tools/run_c2_selftest.py';code=original.read_text(encoding='utf-8-sig')
    start=code.index('        prepared=subprocess.run([sys.executable,str(ROOT/\'tools/prepare_c2_vendor.py\')')
    end=code.index("        for name in ['a_c2_video_frame0.gray'",start)
    code=code[:start]+code[end:]
    start=code.index("        audited = subprocess.run([sys.executable, str(ROOT / 'tools/audit_c2_baselines.py')]")
    end=code.index("        for filename, expected in record['source_sha256'].items():",start)
    code=code[:start]+"        record['postchecks']='RTL-only alternate implementation; unchanged C software/native baseline not rebuilt'\n"+code[end:]
    old='            args += [str(p.relative_to(ROOT)) for p in [*rtl, *sim]]'
    assert old in code;code=code.replace(old,"            args += ['-f', str(INPUT_FILELIST)]")
    ns={'__name__':'isolated_physical_c2','__file__':str(original)};exec(compile(code,str(original),'exec'),ns)
    ns.update(PROJECT=B,BUILD=B/'outputs',LOGS=ROOT/'logs/physical_c2',REPORT=ROOT/'logs/physical_c2_selftest.json',INPUT_FILELIST=filelist)
    result=ns['main']()
    path=ns['REPORT'];record=json.loads(path.read_text(encoding='utf-8-sig'))
    record.update(physical_overrides=True,tail_checks=tail_checks,source_clone_provenance=provenance,
                  wrapper_sha256=sha(Path(__file__)),original_runner_sha256=sha(original),derived_runner_sha256=hashlib.sha256(code.encode()).hexdigest())
    path.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':raise SystemExit(main())
