"""Independent short-tail burst regression; no vendor/board dependencies."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
    files=['projects/06_soc_c2/rtl/c2_video_framebuffer.sv',
           'projects/06_soc_c2/rtl/c2_async_fifo.sv','projects/06_soc_c2/rtl/c2_cdc_mailbox.sv',
           'projects/06_soc_c2/sim/c2_ddr_model.sv','projects/06_soc_c2/sim/tb_c2_video_tail.sv',
           'tools/check_c2_video_tail.py']
    record={'status':'RUNNING','board_test_passed':False,
            'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files}}
    try:
        ivl=ROOT/'tools/iverilog/bin/iverilog.exe';vvp=ivl.with_name('vvp.exe')
        out=ROOT/'build/c2/tb_c2_video_tail.vvp'
        c=subprocess.run([str(ivl),'-g2012','-Wall','-s','tb_c2_video_tail','-o',str(out),*files[:-1]],
                         cwd=ROOT,capture_output=True,text=True,timeout=30)
        if c.returncode or c.stderr.strip():raise ValueError(c.stdout+c.stderr)
        r=subprocess.run([str(vvp),str(out)],cwd=ROOT,capture_output=True,text=True,timeout=30)
        (ROOT/'logs/c2/tb_c2_video_tail.log').write_text(r.stdout+r.stderr,encoding='utf-8')
        if r.returncode or 'PASS tb_c2_video_tail ' not in r.stdout:raise ValueError(r.stdout+r.stderr)
        record.update(status='PASS',evidence=r.stdout.splitlines())
    except Exception as e:record.update(status='FAIL',error=str(e))
    (ROOT/'logs/c2_video_tail.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record));return 0 if record['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
