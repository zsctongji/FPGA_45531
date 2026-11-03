"""Reuse an identical-RTL synthesis result for a seed-only PNR experiment."""
from pathlib import Path
import json,hashlib,shutil,xml.etree.ElementTree as E
R=Path(__file__).resolve().parents[1];A=R/'build/c9_sideband_raw10_image_20261103';B=R/'build/c9_sideband_seed3_image_20261103'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 old=json.loads((A/'SIDEBAND_MANIFEST.json').read_text())
 for n,d in old['source_sha256'].items():
  p=R/n;actual=hashlib.sha256(p.read_text().encode()).hexdigest() if p.name=='soc_physical.xml' else sha(p)
  assert actual==d,n
 x=(A/'soc_physical.xml').read_text();y=(B/'soc_physical.xml').read_text().replace(B.as_posix(),A.as_posix()).replace('name="seed" value="3"','name="seed" value="2"')
 assert E.canonicalize(x,strip_text=True)==E.canonicalize(y,strip_text=True),'Beyond seed/path change'
 fs=lambda p:[Path(e.get('name')) for e in E.parse(p).iter() if e.tag.endswith('}design_file')]
 a,b=fs(A/'soc_physical.xml'),fs(B/'soc_physical.xml');assert len(a)==len(b);pairs=[]
 for p,q in zip(a,b):assert sha(p)==sha(q),str(p);pairs.append((p.relative_to(R).as_posix(),q.relative_to(R).as_posix()))
 (B/'outflow').mkdir(exist_ok=True);evidence=[A/'SIDEBAND_MANIFEST.json',Path(__file__)];copied=[]
 names=['map.v','map.rpt','map.out','map.rdb','vdb','raminfo.pb','interface.csv','peri.cdo','peri.csi','peri.pbn','peri.qdelay','pinout.csv','pinout.rpt','pt.sdc','pt.rpt','pt.rpt.xml','pt_routing_hints','pt_timing.rpt','res.csv','rs','proj_state.ini']
 names=['soc_physical.'+n for n in names]+['debug_profile.mark_debug.json','soc_physical_or.ini']
 for name in names:
  p=A/'outflow'/name;q=B/'outflow'/name;assert p.is_file(),name
  shutil.copyfile(p,q);assert sha(p)==sha(q);evidence.extend([p,q]);copied.append(name)
 for name in ['interface.log','map.log']:
  shutil.copyfile(A/name,B/name);evidence.extend([A/name,B/name])
 m=dict(status='PASS_IDENTICAL_LOGIC_MAP_REUSE',controlled_change='PNR seed 2 to 3 and source directory paths only. No resynthesis claimed.',compiled_source_pairs=pairs,copied_files=copied,evidence_sha256={p.relative_to(R).as_posix():sha(p) for p in evidence})
 (B/'MAP_REUSE.json').write_text(json.dumps(m,indent=2)+'\n');print('PASS map reuse:',len(pairs),'compiled source files identical')
if __name__=='__main__':main()
