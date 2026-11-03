"""Accept C9 calibration from identity-bound USER2 samples, never from capture exit code.

Reads saved files only. PASS does not prove CPU execution, AXI data integrity,
full capacity, clock frequency, or atomicity of native status banks.
"""
from pathlib import Path
import argparse, datetime, hashlib, json
from capture_c9_ddr_probe import decode

R=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def inspect(rows):
    banks={b:[] for b in range(4)};previous=None;last_time=None
    assert len(rows)>=48,'Insufficient samples'
    for row in rows:
        b=row['bank'];v=row['value']
        assert type(b) is int and type(v) is int and b in banks and 0<=v<2**32,'Invalid sample'
        assert int(row['raw_hex'],16)==(b<<32)|v,'Raw/bank/payload mismatch'
        if previous is not None: assert b==(previous+1)%4,'Discontinuous USER2 banks'
        stamp=datetime.datetime.fromisoformat(row['time'])
        assert stamp.tzinfo is not None,'Missing sample timezone'
        if last_time is not None: assert stamp>last_time,'Sample time not increasing'
        last_time=stamp;previous=b
        if b==3: assert v>>16==0xc9d2,'Missing USER2 signature'
        banks[b].append(row)
    assert min(map(len,banks.values()))>=12,'Too few observations per bank'
    span=(datetime.datetime.fromisoformat(rows[-1]['time'])-datetime.datetime.fromisoformat(rows[0]['time'])).total_seconds()
    assert span>=2,'Observation window too short'
    observed=decode(banks)
    failures=[]
    if not all((v['value']&15)==13 for v in banks[0][-8:]):
        failures.append('cal_done must remain 1, CPU reset 0, sys_rst/ddr_rstn 1 for last eight bank0 samples')
    if not all((v['value']&0x1f00)==0x1f00 for v in banks[3][-8:]):
        failures.append('Root reset and all four PLL locks must remain released/locked')
    if not all(observed['clock_activity_observed'].values()):
        failures.append('Activity not observed on all four clock probes')
    return observed,failures

def check(attempt_path,audit_path):
    attempt_path=Path(attempt_path);audit_path=Path(audit_path)
    a=json.loads(attempt_path.read_text());audit=json.loads(audit_path.read_text())
    assert a['status']=='CAPTURED_READONLY_DDR_STATUS' and a['fpga_configured'] is True,'No successful SRAM capture'
    assert a['flash_written'] is False and a['cpu_firmware_loaded'] is False,'Unexpected capture scope'
    assert audit['status']=='PASS_OFFLINE_READONLY_DDR_PROBE','Unqualified implementation'
    assert a['implementation_audit_sha256']==sha(audit_path),'Capture/audit identity mismatch'
    images=[(n,d) for n,d in audit['evidence_sha256'].items() if n.endswith('/outflow/soc_physical.bit')]
    assert len(images)==1 and images[0][1]==a['fpga_image_sha256'],'Capture/image identity mismatch'
    for field in ['source_sha256','evidence_sha256']:
        for n,d in audit[field].items(): assert sha(R/n)==d,'Changed implementation input: '+n
    captured_tool=attempt_path.parent/'capture_tool.py'
    assert captured_tool.is_file() and sha(captured_tool)==a['capture_tool_sha256'],'Missing/changed frozen capture tool'
    samples=attempt_path.parent/'samples.json';assert sha(samples)==a['samples_sha256'],'Changed raw samples'
    observed,failures=inspect(json.loads(samples.read_text()))
    assert observed==a['observed'],'Stored summary differs from raw data'
    return dict(status='FAIL_CALIBRATION_INCOMPLETE' if failures else 'PASS_CALIBRATION_ONLY',
        calibration_verified=not failures,failures=failures,observed=observed,
        cpu_execution_verified=False,full_capacity_verified=False,clock_frequency_verified=False,atomic_snapshot=False,
        hardware_accessed=False,c10_restore_passed=a.get('c10_restore_passed') is True,
        fpga_image_sha256=a['fpga_image_sha256'],attempt_sha256=sha(attempt_path),samples_sha256=sha(samples),
        audit_sha256=sha(audit_path),checker_sha256=sha(Path(__file__)))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('attempt',type=Path);ap.add_argument('--audit',type=Path,required=True)
    ap.add_argument('--output',type=Path);args=ap.parse_args()
    try: report=check(args.attempt,args.audit)
    except Exception as exc: report=dict(status='FAIL_EVIDENCE',calibration_verified=False,hardware_accessed=False,error=str(exc))
    if args.output: args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['calibration_verified'] else 1

if __name__=='__main__': raise SystemExit(main())
