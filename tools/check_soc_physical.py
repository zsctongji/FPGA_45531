"""Functional checks for the NEW physical pixel glue, never hardware access."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/07_soc_physical'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');args=ap.parse_args()
    build=ROOT/'build/physical_20261031';build.mkdir(parents=True,exist_ok=True)
    report={'status':'RUNNING','started':datetime.now(timezone.utc).isoformat(),'board_test_passed':False,
            'encrypted_CSI_HDMI_simulated':False,'full_soc_CPU_executed':False,'full_hd':not args.quick,
            'scope':'actual A unencrypted ISP plus pixel CDC/serialization/GRAY8/raster; not a physical MIPI/HDMI test',
            'tests':[],'source_sha256':{}}
    files=[ROOT/'projects/06_soc_c2/rtl/c2_bram_async_fifo.sv',P/'rtl/physical_video.sv',
           *sorted((P/'vendor_a/rtl/debayer').glob('*.v')),*sorted((P/'sim').glob('*.sv')),Path(__file__)]
    report['source_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    try:
        iv=ROOT/'tools/iverilog/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
        cases=[('tb_physical_video',{}),('tb_physical_isp',{})]
        if not args.quick:cases.append(('tb_physical_isp',{'WIDTH':1920,'HEIGHT':1080}))
        for top,params in cases:
            key=top+''.join('_'+k.lower()+str(v) for k,v in params.items());exe=build/(key+'.vvp')
            cmd=[str(iv),'-g2012','-Wall','-s',top,*[f'-P{top}.{k}={v}' for k,v in params.items()],'-o',str(exe),*[str(p.relative_to(ROOT)) for p in files if p.suffix in ['.v','.sv']]]
            c=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
            (build/(key+'_compile.log')).write_text(c.stdout+c.stderr,encoding='utf-8')
            if c.returncode:raise ValueError(c.stdout+c.stderr)
            # Retain original vendor inherited-timescale/unused wide constant
            # diagnostics; do not silence a functional error or implicit port.
            warnings=[l for l in c.stderr.splitlines() if 'warning:' in l]
            if any('inherited' not in l and 'Unsized expression' not in l for l in warnings):raise ValueError(c.stderr)
            r=subprocess.run([str(vvp),str(exe)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600)
            out=r.stdout+r.stderr;(build/(key+'.log')).write_text(out,encoding='utf-8')
            if r.returncode or 'PASS '+top+' ' not in out:raise ValueError(out)
            report['tests'].append({'name':key,'status':'PASS','vendor_compile_warnings':warnings,'evidence':[l for l in out.splitlines() if l.startswith('PASS ')]})
            print(key+': PASS',flush=True)
        for name,digest in report['source_sha256'].items():
            if sha(ROOT/name)!=digest:raise ValueError('Source changed during test: '+name)
        report['status']='PASS'
    except Exception as e:report.update(status='FAIL',error=str(e));print(str(e),file=sys.stderr)
    report['finished']=datetime.now(timezone.utc).isoformat()
    (ROOT/'logs/soc_physical_tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
