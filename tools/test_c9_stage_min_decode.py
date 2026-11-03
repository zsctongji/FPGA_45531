"""Counter limits and decoding against real RTL simulation records."""
from pathlib import Path
import hashlib,json,re,subprocess
from check_c9_stage_min import decode,counter
R=Path(__file__).resolve().parents[1];B=R/'build/c9_stage_tests_20261103';S=R/'team_work/03_ai_soc/c9_live/camera_geometry'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 iv=R/'tools/iverilog/bin/iverilog.exe';exe=B/'counter.vvp';src=[S/'c9_stage_probe.sv',S/'tb_stage_counter.sv']
 q=subprocess.run([str(iv),'-g2012','-s','tb_stage_counter','-o',str(exe),*[str(p) for p in src]],capture_output=True,text=True,timeout=30);assert q.returncode==0,q.stderr
 q=subprocess.run([str(iv.with_name('vvp.exe')),str(exe)],capture_output=True,text=True,timeout=30);assert q.returncode==0 and 'PASS tb_stage_counter' in q.stdout,q.stdout+q.stderr
 print(q.stdout);(B/'counter.log').write_text(q.stdout+q.stderr)
 cases=json.loads((R/'logs/c9_stage_chain_tests_20261103.json').read_text())['cases'];observed=[]
 for row in cases:
  match=re.search(r'native=([0-9a-f]+) isp=([0-9a-f]+) video=([0-9a-f]+)',row['evidence']);n,i,v=[int(k,16) for k in match.groups()]
  phy=[n&0xffffffff,n>>32];isp=[(i>>(32*k))&0xffffffff for k in range(5)]+[0,0,0];video=[0]*8;video[6]=v
  d=decode(phy,isp,video);st=d['stages'];mode=row['mode']
  expected=[480,960,960,960,960,960,1920,1920] if mode==0 else [18,36,36,36,36,36,72,72] if mode==1 else [480,960,960,0,0,0,0,0] if mode==2 else [480,960,960,960,960,960,1920,0]
  names=['native_4ppc','raw_2ppc','rgb_de','rgb_valid','rgb_joint','gray_2ppc','pixel_1ppc','source_1ppc'];assert [st[k]['maximum_contiguous_cycles'] for k in names]==expected
  observed.append(dict(mode=mode,phase_ns=row['phase_ns'],maxima=dict(zip(names,expected))))
  if mode==0:
   for bad in ['native_signature','isp_signature','video_signature','reserved_native','camera_tail']:
    a=phy.copy();b=isp.copy();c=video.copy()
    if bad=='native_signature':a[1]^=1<<24
    if bad=='isp_signature':b[4]^=1
    if bad=='video_signature':c[6]^=1<<30
    if bad=='reserved_native':a[0]|=1<<24
    if bad=='camera_tail':b[5]=1
    try:decode(a,b,c)
    except AssertionError:pass
    else:raise AssertionError('Accepted '+bad)
 assert counter((2047<<12)|4095)['maximum_at_least'] and counter((2047<<12)|4095)['segments_at_least']
 report=dict(status='PASS',hardware_accessed=False,synthetic_only=True,cases=observed,source_sha256={p.relative_to(R).as_posix():sha(p) for p in [*src,Path(__file__),R/'tools/check_c9_stage_min.py',R/'logs/c9_stage_chain_tests_20261103.json']})
 (R/'logs/c9_stage_min_decode_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS stage decoder, protocol rejection and counter limits')
if __name__=='__main__':main()
