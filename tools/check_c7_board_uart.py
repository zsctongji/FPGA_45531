"""Validate the small CPU DDR/cache diagnostic, separate from TinyML acceptance."""
from pathlib import Path
import argparse,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def validate(text,build):
 lines=[s.strip() for s in re.split(r'[\r\n]+',text) if s.strip().startswith('C7|')]
 rows=[];errors=[]
 for line in lines:
  kind=line.split()[0][3:];row=dict(re.findall(r'(\w+)=([^\s]+)',line));rows.append((kind,row))
 kinds=[kind for kind,_ in rows]
 if kinds!=['BOOT','APB','TIME']+['MEMORY_PASS']*4+['LANES','CACHE','DONE']:errors.append('Incomplete, duplicate, failed or out-of-order diagnostic records')
 try:
  boot=rows[0][1];apb=rows[1][1];tm=rows[2][1];done=rows[-1][1]
  if boot['version']!=build['version'] or done['version']!=build['version']:errors.append('Build identity mismatch')
  if boot['cpu_hz']!='100000000' or boot['clint_hz']!='100000000':errors.append('Clock contract mismatch')
  if any(int(apb[k],16)!=v for k,v in [('id',0x43325332),('version',0x20002),('map',0),('errors',0),('shared',0x09010000)]):errors.append('APB contract or bus error')
  ticks=(int(tm['ticks_hi'],16)<<32)|int(tm['ticks_lo'],16);ms=int(tm['ms_delta'],16)
  if not 99<=ms<=102 or not 10000000<=ticks<=10200000:errors.append('CLINT/shared-time check failed')
  for i,(_,row) in enumerate(rows[3:7]):
   if int(row['pattern'],16)!=i or int(row['checked'],16)!=(i+1)*262144:errors.append('Memory pattern/count mismatch')
  lanes=rows[7][1];cache=rows[8][1]
  if any(lanes[k]!='PASS' for k in ['byte','halfword','cross16','cross64']):errors.append('Byte lane check failed')
  if cache!={'opcode':'0000500f','line_bytes':'64','cache_bytes':'4096','invalidate_refill':'PASS','dma_coherence':'UNTESTED'}:errors.append('Cache scope or result mismatch')
  if done['status']!='PASS' or int(done['checked'],16)!=build['checked_words']:errors.append('Missing complete memory terminal count')
 except (KeyError,ValueError,IndexError,TypeError) as exc:errors.append('Malformed diagnostic: '+str(exc))
 return dict(status='PASS_CPU_DDR_CACHE_LOG' if not errors else 'FAIL',records=len(rows),errors=sorted(set(errors)),
             scope='CPU-side tested DDR ranges, byte lanes and D-cache invalidate/refill; external DMA stale-cache behavior and TinyML are separate')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('log',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args()
 raw=a.log.read_bytes();build=json.loads((ROOT/'firmware/c7_board_diag/BUILD_RECORD.json').read_text())
 r=validate(raw.decode('utf-8',errors='replace'),build);r['log_sha256']=hashlib.sha256(raw).hexdigest()
 if a.output:a.output.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(r));return 0 if not r['errors'] else 1
if __name__=='__main__':raise SystemExit(main())
