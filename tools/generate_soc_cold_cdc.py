"""Apply the pinned C7 CDC binder to the isolated live project/output record."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'tools/generate_physical_cdc.py'
source=base.read_text();old="ROOT/'logs/soc_physical_cdc_binding.json'"
assert source.count(old)==1
source=source.replace(old,"ROOT/'logs/soc_cold_cdc_binding.json'")
ns={'__name__':'live_cdc_bound','__file__':str(base)};exec(compile(source,str(base),'exec'),ns)
ns['P']=ROOT/'projects/10_soc_cold'
if __name__=='__main__':
 ns['main']()
 p=ROOT/'logs/soc_cold_cdc_binding.json';record=json.loads(p.read_text())
 record['live_wrapper_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 record['executed_binder_sha256']=hashlib.sha256(source.encode()).hexdigest()
 p.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
