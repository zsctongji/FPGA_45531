"""Small destructive JTAG DDR reproducer on an already-configured C7."""
from pathlib import Path
import argparse,datetime,json,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['bulk','word','byte'],default='bulk');ap.add_argument('--base',type=lambda x:int(x,0),default=0x02000000)
 a=ap.parse_args();assert a.base in [0x02000000,0x04000000]
 out=ROOT/'logs/c7_board_20261101'/('ddr_probe_'+a.mode+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir(parents=True,exist_ok=False)
 data=bytes(range(1,17));(out/'expected.bin').write_bytes(data)
 cfg=(ROOT/'logs/c7_board_20261101/probe_20261101_123338/probe.cfg').read_text().split('init\n')[0]+'init\nhalt\n'
 if a.mode=='bulk':cfg+='echo [load_image {%s} 0x%x bin]\n'%((out/'expected.bin').as_posix(),a.base)
 elif a.mode=='word':
  for i in range(0,16,4):cfg+='mww 0x%x 0x%x\n'%(a.base+i,int.from_bytes(data[i:i+4],'little'))
 else:
  for i,n in enumerate(data):cfg+='mwb 0x%x 0x%x\n'%(a.base+i,n)
 cfg+='echo [dump_image {%s} 0x%x 16]\nshutdown\n'%((out/'actual.bin').as_posix(),a.base)
 (out/'probe.cfg').write_text(cfg,encoding='utf-8')
 run=subprocess.run([str(ROOT/'tools/efinity/2026.1/debugger/openocd/bin/openocd.exe'),'-f',str(out/'probe.cfg')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
 (out/'openocd.log').write_bytes(run.stdout)
 got=(out/'actual.bin').read_bytes() if (out/'actual.bin').exists() else b''
 report=dict(status='PASS' if run.returncode==0 and got==data else 'FAIL',mode=a.mode,base=hex(a.base),expected=data.hex(),actual=got.hex(),openocd_returncode=run.returncode,flash_written=False,scope='Small CPU debug memory write/read, not full C7 acceptance')
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report));print('EVIDENCE='+str(out));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
