"""Read-only component, boot-ROM and layout checks. Never opens board devices."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/07_soc_physical'
SDK=ROOT/'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def defines(p):
    return {k:int(v,0) for k,v in re.findall(r'^\s*(?:`define|#define)\s+(\w+)\s+(0x[\da-fA-F]+|\d+)\b',p.read_text(encoding='utf-8-sig'),re.M)}

def main():
    checks=[];evidence=[]
    def require(ok,label):
        if not ok:raise ValueError(label)
        checks.append(label)
    identity=read(ROOT/'logs/hardware_identity_20261031.json')
    evidence.append(ROOT/'logs/hardware_identity_20261031.json')
    header=P/'overrides/ddr3_parameter.vh';v=defines(header);evidence.append(header)
    capacity=2**(v['BANK_WIDTH']+v['ROW_WIDTH']+v['COL_WIDTH'])*(v['DQ_WIDTH']//8)*v['RANKS']
    require(capacity==identity['ddr']['capacity_bytes']==268435456,'Physical x16 address geometry equals 256MiB')
    require(v['tCK']==2500,'DDR CK is 400MHz, not 800MHz CK')
    require(v['tFAW']>=50000,'Conservative x16 tFAW is at least 50ns')
    core=(P/'physical_soc_core.v').read_text(encoding='utf-8-sig')
    require(header.as_posix() in core,'Integrated core uses the actual private timing header')
    project=(P/'soc_physical.xml').read_text(encoding='utf-8-sig')
    require((P/'overrides/ddr3_top.v').as_posix() in project,'Project compiles the private-header DDR wrapper')
    # These are configuration identities, not a proof of the protected DDR
    # scheduler, MRS sequencing, temperature refresh or physical margins.
    cfg=SDK/'bsp/efinix/EfxSapphireSoc/app/bootloaderConfig.h';b=defines(cfg);evidence.append(cfg)
    start=b['USER_SOFTWARE_FLASH'];size=b['USER_SOFTWARE_SIZE'];end=start+size
    require((start,size,b['USER_SOFTWARE_MEMORY'])==(0x380000,0x400000,0x1000),'ROM source has the verified 3.5MiB / 4MiB copy contract')
    require(b['SINGLE_SPI']==1,'CPU boot selects single-data-line SPI')
    require(end<=identity['flash']['capacity_bytes']==0x800000,'Boot copy ends at 0x780000 within 8MiB Flash')
    boot=SDK/'software/standalone/bootloader/build_ours/bootloader.bin'
    if boot.is_file():
        data=boot.read_bytes();require(sha(boot)==read(ROOT/'logs/bootloader_build.json')['binary_sha256'].lower(),'Actual boot binary matches recorded cross-compile hash');evidence.append(boot)
    else:
        # The handoff includes the ROM lanes even when build_ours is excluded.
        # Validate the reconstructed prefix against the original build digest.
        data=None
    lanes=[]
    for n in range(4):
        f=P/f'EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol{n}.bin';evidence.append(f)
        rows=f.read_text().splitlines();require(len(rows)==1024 and all(re.fullmatch('[01]{8}',s) for s in rows),'ROM lane has 1024 binary bytes '+str(n))
        lanes.append([int(s,2) for s in rows])
    rom=bytes(lanes[i%4][i//4] for i in range(4096));record=read(ROOT/'logs/bootloader_build.json');n=record['binary_bytes']
    require(hashlib.sha256(rom[:n]).hexdigest()==record['binary_sha256'].lower() and not any(rom[n:]),'All compiled boot-ROM lanes reconstruct the exact boot binary')
    fw=ROOT/'firmware/c24_frame_person_detect/tinyml_c24.bin';evidence.append(fw)
    require(fw.stat().st_size<=size,'Current raw C24 application fits the boot-copy capacity')
    expected=next(a for a in read(ROOT/'logs/firmware_c24.json')['artifacts'] if a['path']==fw.relative_to(ROOT).as_posix())
    require(sha(fw)==expected['sha256'],'Current CPU binary matches the linked C24 artifact')
    configuration=P/'outflow/soc_physical.hex';configuration_bytes=None;layout=False
    if configuration.is_file():
        generation=read(ROOT/'logs/soc_physical_pgm_check.json')
        require(generation['status']=='PASS' and generation['completed_flow']=='pgm','Offline configuration generation completed')
        require(sha(configuration)==generation['step']['configuration_sha256'],'Configuration stream identity matches generation record')
        require(sha(P/'work_pnr/soc_physical.lbf')==generation['step']['routed_lbf_sha256'],'Configuration generated from current routed design')
        audit=read(ROOT/'logs/soc_physical_audit.json')
        require(audit['status']=='PASS_REFERENCE_AUDIT' and sha(P/'work_pnr/soc_physical.lbf')==audit['evidence_sha256']['projects/07_soc_physical/work_pnr/soc_physical.lbf'],'Configuration uses the STA-reviewed routed design')
        for name,digest in audit['evidence_sha256'].items():require(sha(ROOT/name)==digest,'Current implementation evidence '+name)
        rows=configuration.read_text(encoding='ascii').splitlines()
        require(bool(rows) and all(re.fullmatch('[0-9A-Fa-f]{2}',s) for s in rows),'Efinity configuration stream is a strict byte-per-line hex dump')
        # Count even the encoded container metadata, giving a conservative
        # upper bound rather than mistaking ASCII file size for Flash usage.
        configuration_bytes=len(rows);require(configuration_bytes<=start,'Whole configuration stream fits before CPU reservation')
        layout=True;evidence.extend([configuration,ROOT/'logs/soc_physical_pgm_check.json',ROOT/'logs/soc_physical_audit.json'])
    report={'status':'PASS_STATIC_CHECKS_RELEASE_REVIEW_REQUIRED','checks':len(checks),'physical_release_ready':False,'board_programmed':False,
      'voltage_observation':identity.get('voltage_observation',{'status':'NOT_REPORTED'}),
      'ddr':{'capacity_bytes':capacity,'clock_MHz':1000000/v['tCK'],'tFAW_ns':v['tFAW']/1000,'CL':v['CL'],'CWL':v['CWL'],
        'tRCD_ns':v['tRCD']/1000,'tRP_ns':v['tRP']/1000,'tRAS_ns':v['tRAS']/1000,'tRFC_ns':v['tRFC']/1000,'tREFI_ns':v['tREFI']/1000,
        'full_timing_or_hardware_signoff':False},
      'flash':{'capacity_bytes':identity['flash']['capacity_bytes'],'cpu_reserved_start':start,'cpu_copy_end_exclusive':end,
        'raw_application_bytes':fw.stat().st_size,'raw_application_end_exclusive':start+fw.stat().st_size,
        'fpga_configuration_must_end_at_or_before':start,'configuration_stream_upper_bound_bytes':configuration_bytes,
        'fpga_actual_size_known':configuration_bytes is not None,'static_non_overlap_verified':layout,'combined_board_boot_verified':False},
      'remaining':['Real DDR calibration, address-alias/data-pattern tests and repeated cold boot',
        'Encrypted controller scheduling/MRS, full timing and operating-temperature refresh review',
        'Flash JEDEC/SFDP identity and external SPI timing',
        'Final programming-tool address interpretation, readback and repeated combined cold boot',
        'Camera/FPC and buzzer identity/polarity plus live sensor/AI validation'],
      'tool_sha256':sha(Path(__file__)),'evidence_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in evidence}}
    (ROOT/'logs/board_preflight_20261031.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PASS {len(checks)} static checks. User-reported voltage accepted; release remains REVIEW_REQUIRED.')

if __name__=='__main__':main()
