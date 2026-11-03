"""Recheck local C9/C8 control readiness. No device or serial access."""
from pathlib import Path
import datetime, hashlib, json, re, subprocess, sys
from c9_probe_image import select, select_current
from capture_c8_comb4_control import preflight as c8_preflight

R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    cases=[]
    for variant in ['cong','speed','nopack']:
        image,audit=select(R,variant);a=json.loads(audit.read_text())
        captured={'cong':'20261102_183619','speed':'20261101_213243'}
        observed={}
        if variant in captured:
            attempt=R/'logs/c9_ddr_probe_20261101'/captured[variant]/'attempt.json'
            meta=json.loads(attempt.read_text())
            assert meta['status']=='CAPTURED_READONLY_DDR_STATUS' and meta['fpga_image_sha256']==sha(image)
            assert meta['observed']['cal_done'] is False
            observed=dict(board_attempt=attempt.relative_to(R).as_posix(),board_attempt_sha256=sha(attempt),init_state=meta['observed']['init_state'])
        hardware='CALIBRATION_INCOMPLETE'
        if variant=='nopack':
            _,_,profile_path=select_current(R,profile_name='config/c9_board_profile_20261102.json');profile=json.loads(profile_path.read_text())
            hardware='PASS_CALIBRATION_ONLY';observed=dict(calibration_attempts=profile['calibration_attempts'])
        place=(image.parent/'soc_physical.place.rpt').read_text()
        xlr=re.search(r'^XLRs:\s*(\d+)\s*/\s*(\d+)',place,re.M)
        cases.append(dict(name='c9_'+variant,implementation='PASS',hardware_acceptance=hardware,
            setup_ns=a['timing']['setup']['minimum_slack_ns'],hold_ns=a['timing']['hold']['minimum_slack_ns'],xlrs=int(xlr[1]),
            image_path=image.relative_to(R).as_posix(),image_sha256=sha(image),audit_path=audit.relative_to(R).as_posix(),audit_sha256=sha(audit),**observed))
    image,audit=c8_preflight();a=json.loads(audit.read_text())
    c8_attempt=R/'logs/c8_comb4_control_20261102/20261102_183007/attempt.json'
    c8_meta=json.loads(c8_attempt.read_text());assert c8_meta['fpga_image_sha256']==sha(image) and c8_meta['board_test_passed'] is False
    cases.append(dict(name='c8_comb4_on',implementation='PASS',hardware_acceptance='FAIL_UART_NO_CAPACITY_PASS',
        board_attempt=c8_attempt.relative_to(R).as_posix(),board_attempt_sha256=sha(c8_attempt),
        setup_ns=a['timing']['setup']['minimum_slack_ns'],hold_ns=a['timing']['hold']['minimum_slack_ns'],
        image_path=image.relative_to(R).as_posix(),image_sha256=sha(image),audit_path=audit.relative_to(R).as_posix(),audit_sha256=sha(audit)))
    q=subprocess.run([sys.executable,'-X','utf8',str(R/'tools/test_c9_probe_preflight.py')],cwd=R,capture_output=True,text=True,timeout=120)
    assert q.returncode==0,q.stdout+q.stderr
    identity=json.loads(q.stdout);assert identity['status']=='PASS_OFFLINE_IDENTITY_CHECKS'
    rtl=json.loads((R/'logs/c9_ddr_probe_rtl.json').read_text());assert rtl['status']=='PASS'
    for n,d in rtl['source_sha256'].items():assert sha(R/n)==d,n
    dma_verified=False
    if (R/'config/c9_active_profile.json').exists():
        image,audit,profile_path=select_current(R);a=json.loads(audit.read_text());profile=json.loads(profile_path.read_text())
        proof=R/profile['dma_acceptance_attempt'];checked=proof.parent/'dma_check.json';v=json.loads(checked.read_text())
        assert v['status']=='PASS' and v['fpga_image_sha256']==sha(image)
        assert v['uart_sha256']==sha(proof.parent/'uart.log')
        dma_verified=True
        cases.append(dict(name='c9_active_display_fix',implementation='PASS',hardware_acceptance='PASS_PATTERN_DMA_VIDEO',
            setup_ns=a['timing']['setup']['minimum_slack_ns'],hold_ns=a['timing']['hold']['minimum_slack_ns'],
            image_path=image.relative_to(R).as_posix(),image_sha256=sha(image),audit_path=audit.relative_to(R).as_posix(),audit_sha256=sha(audit),
            dma_check_sha256=sha(checked)))
    report=dict(status='PASS_OFFLINE_IDENTITY_AND_SAVED_EVIDENCE',created=datetime.datetime.now().astimezone().isoformat(),
        hardware_accessed=False,board_connection_checked=False,flash_written=False,dma_cache_handoff_verified=dma_verified,real_camera_verified=False,
        cases=cases,identity_checks=identity['checks'],rtl_evidence_sha256=sha(R/'logs/c9_ddr_probe_rtl.json'),
        identity_report_sha256=sha(R/'logs/c9_preflight_tests_20261102.json'),tool_sha256=sha(Path(__file__)))
    (R/'logs/c9_offline_readiness_20261102.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
