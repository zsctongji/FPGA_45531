"""Export small, hash-bound offline implementation reports; no device access."""
from pathlib import Path
import hashlib,importlib.util,json,shutil
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    audit=json.loads((ROOT/'logs/soc_physical_audit.json').read_text())
    if audit['status']!='PASS_REFERENCE_AUDIT':raise ValueError('Current physical audit required')
    for name,digest in audit['evidence_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Changed audited evidence '+name)
    folder=ROOT/'logs/soc_physical_evidence';folder.mkdir(parents=True,exist_ok=True)
    files=['pinout.csv','pt.rpt','map.rpt','place.rpt','route.rpt','review_timing.rpt','bus_setup.rpt','bus_hold.rpt','clocks.rpt']
    index={'scope':'Offline tool reports only; no hardware signoff','physical_release_ready':False,'files':{},'exporter_sha256':sha(Path(__file__))}
    for name in files:
        src=ROOT/'projects/07_soc_physical/outflow'/('soc_physical.'+name)
        dst=folder/src.name;shutil.copyfile(src,dst)
        index['files'][dst.name]={'original':src.relative_to(ROOT).as_posix(),'sha256':sha(dst)}
    old=ROOT/'build/physical_20261031/cpu225_result/soc_physical.timing.rpt'
    if old.is_file():
        dst=folder/'cpu225_failed_setup.timing.rpt';shutil.copyfile(old,dst)
        spec=importlib.util.spec_from_file_location('physical_audit',ROOT/'tools/audit_soc_physical.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        index['cpu225_not_accepted']={'sha256':sha(dst),'primary_sta':module.timing_summary(dst)}
    (folder/'EVIDENCE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    print('PASS exported verified reports; large netlists and programmer files excluded.')

if __name__=='__main__':main()
