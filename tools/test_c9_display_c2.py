"""Run existing qualified C2 cases with only the candidate scanout substituted."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
def main():
 base=R/'tools/test_physical_c2.py';code=base.read_text(encoding='utf-8-sig')
 code=code.replace('build/physical_20261031/c2_regression','build/c9_display_c2_20261102')
 code=code.replace('logs/physical_c2','logs/c9_display_c2')
 old="            use=P/'overrides'/src.name if folder=='rtl' and (P/'overrides'/src.name).is_file() else src"
 assert code.count(old)==1
 code=code.replace(old,old+"\n            if folder=='rtl' and src.name=='c2_video_scanout.sv':use=ROOT/'team_work/03_ai_soc/c9_live/display_fix/c2_video_scanout.sv'",1)
 ns={'__name__':'display_c2_regression','__file__':str(Path(__file__))};exec(compile(code,str(base),'exec'),ns)
 result=ns['main']();p=R/'logs/c9_display_c2_selftest.json';report=json.loads(p.read_text(encoding='utf-8-sig'))
 report.update(display_scanout_fix=True,parent_wrapper_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),derived_wrapper_sha256=hashlib.sha256(code.encode()).hexdigest())
 p.write_text(json.dumps(report,indent=2)+'\n');return result
if __name__=='__main__':raise SystemExit(main())
