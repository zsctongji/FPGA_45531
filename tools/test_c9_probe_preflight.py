"""Offline identity checks: reject modified/misbound images before USB access."""
from pathlib import Path
import hashlib, json, subprocess, sys, tempfile
from c9_probe_image import select, VARIANTS

R=Path(__file__).resolve().parents[1]
def main():
    checks=[]
    for folder,binary in [('c7_board_diag','c7_board_diag.bin'),('c9_dma_diag','c9_dma.bin'),('c9_live_person_detect','tinyml_c9.bin')]:
        cmd=[sys.executable,'-X','utf8',str(R/'tools/run_ram_diagnostic.py'),'--record',str(R/'firmware'/folder/'BUILD_RECORD.json'),
             '--binary',str(R/'firmware'/folder/binary),'--prefix','C9|','--configure-probe','nopack','--preflight-only']
        q=subprocess.run(cmd,cwd=R,capture_output=True,text=True,timeout=30)
        assert q.returncode==0,q.stderr
        a=json.loads(q.stdout);assert a['status']=='PASS_OFFLINE_PREFLIGHT' and a['hardware_accessed'] is False
        checks.append(folder+': frozen firmware and no hardware access')
    with tempfile.TemporaryDirectory(prefix='c9_identity_') as td:
        root=Path(td);p=root/VARIANTS['nopack'];(p/'outflow').mkdir(parents=True)
        image=p/'outflow/soc_physical.bit';image.write_bytes(b'control image')
        source=p/'input.v';source.write_bytes(b'original RTL')
        a=dict(status='PASS_OFFLINE_READONLY_DDR_PROBE',board_test_passed=False,flash_written=False,
            source_sha256={source.relative_to(root).as_posix():hashlib.sha256(source.read_bytes()).hexdigest()},
            evidence_sha256={image.relative_to(root).as_posix():hashlib.sha256(image.read_bytes()).hexdigest()})
        manifest=p/'implementation_audit.json';manifest.write_text(json.dumps(a))
        assert select(root,'nopack')[0]==image
        for case in ['image_tamper','source_tamper','missing_image_binding','pending_audit']:
            image.write_bytes(b'control image');source.write_bytes(b'original RTL')
            changed=json.loads(json.dumps(a))
            if case=='image_tamper': image.write_bytes(b'different image')
            if case=='source_tamper': source.write_bytes(b'changed RTL')
            if case=='missing_image_binding': changed['evidence_sha256']={}
            if case=='pending_audit': changed['status']='PENDING'
            manifest.write_text(json.dumps(changed))
            try: select(root,'nopack')
            except AssertionError: checks.append(case+': rejected before hardware')
            else: raise AssertionError(case+' was accepted')
    files=[Path(__file__),R/'tools/c9_probe_image.py',R/'tools/run_ram_diagnostic.py']
    report=dict(status='PASS_OFFLINE_IDENTITY_CHECKS',hardware_accessed=False,board_test_passed=False,checks=checks,
        source_sha256={f.relative_to(R).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    (R/'logs/c9_preflight_tests_20261102.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
