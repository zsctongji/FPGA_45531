"""Compile the actual post-snapshot timing block with a UART-delay clock fixture."""
from pathlib import Path
import argparse,hashlib,json,subprocess
R=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--baseline',action='store_true');a=ap.parse_args()
 src=R/('team_work/03_ai_soc/c9_live/firmware/tinyml_main.cc' if a.baseline else 'team_work/03_ai_soc/c9_live/camera_time_fix/tinyml_main.cc')
 text=src.read_text();start=text.index(' if(c9_snapshot("before"))return fail("snapshot",-1);')
 start=text.index('\n',start)+1;end=text.index(' c9_put(4,',start);block=text[start:end]
 out=R/'build/c9_time_progress_20261102';out.mkdir(exist_ok=True)
 tag='baseline' if a.baseline else 'fixed';c=out/(tag+'.c');exe=out/(tag+'.exe')
 harness='''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define BSP_CLINT 0
#define BSP_CLINT_HZ 100000000ULL
static uint64_t ticks;static int mode;
static uint64_t clint_getTime(int ignored){(void)ignored;ticks+=100000;return ticks;}
static int c3_shared_now_ms(int *clock,uint32_t *out){(void)clock;if(mode==2)return -1;*out=mode==1?150u:(uint32_t)(ticks/100000)*(mode==3?20u:1u);return 0;}
static int fail(const char *stage,int status){(void)status;printf("FAIL %s\\n",stage);return 1;}
static void MicroPrintf(const char *format,...){(void)format;}
static int probe(void){int clock=0;uint32_t shared_now=0;
'''+block+'''return 0;}
int main(int argc,char **argv){unsigned overhead=argc>1?(unsigned)strtoul(argv[1],0,10):150;mode=argc>2?atoi(argv[2]):0;ticks=(uint64_t)overhead*100000;return probe();}
'''
 c.write_text(harness)
 cmd=out/(tag+'_build.cmd');cmd.write_text('@echo off\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\ncl /nologo /std:c11 /W4 /WX /TC "'+str(c)+'" /Fo"'+str(out/(tag+'.obj'))+'" /Fe"'+str(exe)+'"\nexit /b %errorlevel%\n')
 q=subprocess.run(['cmd','/c',str(cmd)],capture_output=True,text=True,cwd=R,timeout=45);assert q.returncode==0,q.stdout+q.stderr
 cases=[]
 for name,overhead,mode,want in [('no_log_delay',0,0,0),('uart_150ms',150,0,0),('frozen_shared_time',150,1,1),('read_failure',150,2,1),('wrong_clock_rate',150,3,1)]:
  q=subprocess.run([str(exe),str(overhead),str(mode)],capture_output=True,text=True,timeout=5)
  cases.append(dict(name=name,expected=want,actual=q.returncode,diagnostic=q.stdout.strip()))
 status='PASS' if all(v['expected']==v['actual'] for v in cases) else 'FAIL'
 result=dict(status=status,baseline=a.baseline,scope='Host fixture executes extracted actual post-snapshot source; no FPGA or sensor',cases=cases,
  source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,Path(__file__)]})
 (out/(tag+'_result.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
