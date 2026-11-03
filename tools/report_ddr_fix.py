"""Bind the reproduced COMB4 comparison and C9 CPU access evidence. No hardware."""
from pathlib import Path
import hashlib, json, shutil
from check_c9_ddr_calibration import check as calibration_check
from check_c9_uart import snapshots, check as concurrent_check
from check_ddr_uart import validate as capacity_check
from c9_probe_image import select_current

R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    evidence={}
    def bind(p):evidence[p.relative_to(R).as_posix()]=sha(p)
    image,audit,profile=select_current(R,profile_name='config/c9_board_profile_20261102.json')
    positive=[]
    for stamp in ['20261102_182836','20261102_183801']:
        p=R/'logs/c9_ddr_probe_20261101'/stamp/'attempt.json'
        v=calibration_check(p,audit);assert v['calibration_verified']
        positive.append(dict(attempt=p.relative_to(R).as_posix(),init_state=v['observed']['init_state'],status=v['status']))
        for f in ['attempt.json','samples.json','capture_tool.py']:bind(p.parent/f)
    bad=R/'logs/c9_ddr_probe_20261101/20261102_183619/attempt.json'
    negative=calibration_check(bad,R/'build/c9_ddr_probe_20261101/implementation_audit.json')
    assert negative['status']=='FAIL_CALIBRATION_INCOMPLETE' and negative['observed']['init_state']==23
    for f in ['attempt.json','samples.json','capture_tool.py']:bind(bad.parent/f)
    for folder,stamp,want in [('c8_comb4_control_20261102','20261102_183007',False),('c8_comb4_baseline_20261102','20261102_183426',True)]:
        p=R/'logs'/folder/stamp;meta=read(p/'attempt.json')
        assert meta['board_test_passed'] is want and meta['c10_restore_passed']
        assert sha(p/'uart.log')==meta['uart_sha256']
        assert (capacity_check((p/'uart.log').read_text(errors='replace'))['status']=='PASS_LOG') is want
        bind(p/'attempt.json');bind(p/'uart.log')
    cpu=R/'logs/ram_diagnostic_20261101/20261102_183914';meta=read(cpu/'attempt.json');fw=read(cpu/'firmware_build_record.json')
    assert meta['status']=='CAPTURED_DONE_REQUIRES_CHECKER' and meta['fpga_image_sha256']==sha(image)
    assert meta['readback_sha256']==meta['firmware_sha256']==sha(cpu/'readback.bin')
    assert sha(cpu/'firmware_build_record.json')==meta['build_record_sha256'] and sha(cpu/'run_ram_diagnostic.py')==meta['runner_sha256']
    assert meta['firmware_sha256']==fw['artifacts']['c9_dma.bin']['sha256']
    text=(cpu/'uart.log').read_text();assert 'C9|MAP status=PASS independent_locations=6 words=24 source_off=1' in text
    assert 'C9|CACHE_NEGATIVE stale_words=00000010 omit_invalidate=OLD_DATA' in text
    assert 'C9|CACHE_POSITIVE fresh_words=00000010 invalidate=FRESH_DATA' in text
    assert 'C9|OWNERSHIP status=PASS stale_token_rejected=1 leased_slot_preserved=1 other_slot=1' in text
    assert 'C9|DONE status=PASS mode=coherence version='+fw['version'] in text
    assert 'C9|FAIL' not in text and 'C9|TRAP' not in text
    try:concurrent_check(text,'dma')
    except AssertionError as exc:assert str(exc)=='Display underflow/missed scans'
    else:raise AssertionError('Concurrent acceptance unexpectedly changed')
    strict=read(cpu/'dma_check.json');assert strict['status']=='FAIL' and strict['uart_sha256']==sha(cpu/'uart.log')
    snap=snapshots(text);before=snap['before']['words'];after=snap['after']['words']
    assert before[2][4]==after[2][4]==1 and after[2][3]==0 and after[0][2:4]==[0,0]
    for f in ['attempt.json','firmware_build_record.json','readback.bin','uart.log','dma_check.json','run_ram_diagnostic.py']:bind(cpu/f)
    restore=R/'logs/c10_warm_boot_20261101/20261102_184015';last=read(restore/'attempt.json')
    assert last['status']=='PASS_WARM_ROM_FLASH_BOOT' and read(restore/'reference_check.json')['status']=='PASS'
    assert last['uart_sha256']==sha(restore/'uart.log')
    for f in ['attempt.json','uart.log','reference_check.json']:bind(restore/f)
    for f in [image,audit,profile,Path(__file__),R/'tools/check_c9_uart.py',R/'tools/check_ddr_uart.py',R/'tools/check_c9_ddr_calibration.py']:bind(f)
    report=dict(status='PASS_C9_DDR_CALIBRATION_CPU_ACCESS',remedy='pack-luts-to-comb4=0',
        tested_platform='Ti60F225 / Efinity 2026.1.132',vendor_root_cause_proven=False,
        reproduced_comb4_on_calibration_failure=True,comb4_off_calibration_passes=positive,
        independent_c8_comb4_on='FAIL_UART_NO_FULL_CAPACITY_PASS',independent_c8_comb4_off='PASS_256MIB_FOUR_PATTERNS_AND_ADDRESS_PROBES',
        c9_cpu_execution_verified=True,c9_firmware_readback_bytes=7836,c9_cpu_address_probe_words=24,
        c9_full_capacity_verified=False,cache_negative_and_positive_observed=True,
        complete_dma_video_acceptance_passed=False,remaining_failure=dict(display_missed_before=1,display_missed_after=1,display_underflows_after=0,axi_read_write_errors_after=[0,0]),
        real_camera_verified=False,hdmi_picture_verified=False,c3_present=False,flash_written=False,
        ddr_parameters_changed=False,calibration_algorithm_changed=False,acceptance_criteria_changed=False,
        fpga_image_sha256=sha(image),final_board='C10',final_c10_restore_passed=True,final_c10_attempt=(restore/'attempt.json').relative_to(R).as_posix(),evidence_sha256=evidence)
    (R/'logs/ddr_fix_20261102.json').write_text(json.dumps(report,indent=2)+'\n')
    target=R/'fpga_bitstreams/c9_nopack_100mhz';target.mkdir(exist_ok=True)
    names=['soc_physical.bit','soc_physical.hex','soc_physical.place.rpt','soc_physical.pinout.csv','soc_physical.review_timing.rpt','soc_physical.bus_setup.rpt','soc_physical.bus_hold.rpt']
    artifacts={}
    for n in names:
        shutil.copyfile(image.parent/n,target/n);artifacts[n]=dict(bytes=(target/n).stat().st_size,sha256=sha(target/n))
    shutil.copyfile(profile,target/'QUALIFIED_PROFILE.json')
    record=dict(status=report['status'],diagnostic_only=True,rom_entry_parked=True,flash_boot_image=False,
        c3_present=False,full_system_passed=False,artifacts=artifacts,qualified_profile_sha256=sha(profile),board_summary_sha256=sha(R/'logs/ddr_fix_20261102.json'),
        implementation_audit_sha256=sha(audit),source_sha256=read(audit)['source_sha256'])
    (target/'BUILD_RECORD.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='evidence_sha256'},indent=2))
if __name__=='__main__':main()
