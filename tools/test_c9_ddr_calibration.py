"""Replay real failed board captures; synthetic positive is host-only coverage."""
from pathlib import Path
import copy, datetime, hashlib, json
from check_c9_ddr_calibration import check,inspect

R=Path(__file__).resolve().parents[1]
def main():
    tests=[]
    for stamp,folder,state in [('20261101_205610','c9_ddr_probe_20261101',23),('20261101_213243','c9_ddr_probe_speed_20261101',3)]:
        result=check(R/'logs/c9_ddr_probe_20261101'/stamp/'attempt.json',R/'build'/folder/'implementation_audit.json')
        assert result['status']=='FAIL_CALIBRATION_INCOMPLETE' and result['observed']['init_state']==state
        tests.append(dict(name=stamp,status='EXPECTED_FAILURE_REPRODUCED',state=state))
    rows=[];start=datetime.datetime(2026,11,2,tzinfo=datetime.timezone.utc)
    for i in range(64):
        b=i%4;v=[0x16d,300000<<8,0x10000,0xc9d21f02|(((i//4)%2)*15<<4)][b]
        rows.append(dict(bank=b,value=v,raw_hex='%09x'%((b<<32)|v),time=(start+datetime.timedelta(seconds=i*.1)).isoformat()))
    assert inspect(rows)[1]==[]
    tests.append(dict(name='synthetic_ready',status='PASS_HOST_FIXTURE_ONLY'))
    for name,bank,mask,value in [('cal_low',0,1,0),('cpu_reset',0,2,2),('ddr_reset',0,8,0),('pll_unlock',3,0x100,0),('root_reset',3,0x1000,0),('clock_stopped',3,0xf0,0)]:
        bad=copy.deepcopy(rows)
        for row in bad:
            if row['bank']==bank:
                row['value']=(row['value']&~mask)|value;row['raw_hex']='%09x'%((bank<<32)|row['value'])
        assert inspect(bad)[1],name
        tests.append(dict(name=name,status='REJECTED_HOST_FIXTURE'))
    bad=copy.deepcopy(rows);bad[0]['raw_hex']='000000000'
    try: inspect(bad)
    except AssertionError: tests.append(dict(name='raw_tamper',status='REJECTED_HOST_FIXTURE'))
    else: raise AssertionError('raw_tamper accepted')
    files=[Path(__file__),R/'tools/check_c9_ddr_calibration.py',R/'tools/capture_c9_ddr_probe.py']
    report=dict(status='PASS_OFFLINE_CHECKER_TESTS',board_calibration_fixed=False,hardware_accessed=False,tests=tests,
        source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (R/'logs/c9_ddr_calibration_checker_tests_20261102.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
