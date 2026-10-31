"""Bind the A/C2 test run, linked C24 firmware and current source identities."""
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    checks=[]
    def require(ok,label):
        if not ok:raise ValueError(label)
        checks.append(label)
    build=read(ROOT/'logs/firmware_c24.json')
    inputs=read(ROOT/'firmware/c24_frame_person_detect/C24_INPUT_MANIFEST.json')
    require(build['status']=='PASS' and not build['board_inference_passed'],'Firmware build scope PASS, no board claim')
    require(not any(inputs['config'][k] for k in ['enable_live','verified_map','verified_shared_time']),
            'Default firmware keeps live C2 MMIO disabled')
    for name,digest in inputs['source_hashes'].items():require(sha(ROOT/name)==digest,'Firmware source '+name)
    for item in build['artifacts']:
        p=ROOT/item['path'];require(p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],'Firmware artifact '+p.name)
    elf=(ROOT/'firmware/c24_frame_person_detect/tinyml_c24.elf').read_bytes()
    require(elf[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',elf,18)[0]==243 and
            struct.unpack_from('<I',elf,24)[0]==0x1000,'ELF32 little-endian RISC-V entry 0x1000')
    require(inputs['version'].encode() in elf,'Linked build identifier')
    require((ROOT/'firmware/c24_frame_person_detect/tinyml_c24.bin').stat().st_size<=4194304,'Fits existing 4 MiB boot-copy limit')
    tests=read(ROOT/'logs/c2_selftest.json')
    require(tests['status']=='PASS' and tests['passed']==50,'50 C2/C3/source-pixel/framebuffer/shared-time RTL runs PASS')
    for name,digest in tests['source_sha256'].items():require(sha(ROOT/name)==digest,'RTL/driver test identity '+name)
    native=read(ROOT/'logs/c2_native_synthesis.json')
    require(native['status']=='PASS','Current native overlay logic synthesis PASS')
    for item in native['sources']:
        path=Path(item['path'])
        allowed={item.get('post_tool_sha256',item['sha256'])}
        # Efinity normalizes XML in place. The deterministic generator restores
        # its exact compiler-input XML on regression; both recorded identities
        # are reproducible, while HDL and binary inputs must remain exact.
        if path.suffix=='.xml':allowed.add(item['sha256'])
        require(sha(path) in allowed,'Native source '+item['path'])
    for item in native['artifacts']:require(sha(Path(item['path']))==item['sha256'],'Native artifact '+item['path'])
    inference=read(ROOT/'logs/a_c2_pc_inference.json')
    require(inference['status']=='PASS' and inference['firmware_selftest_input_equal'],
            'A -> C2 DDR readback equals firmware self-test input and desktop reference')
    require(sha(ROOT/'build/c2/a_c2_frame1.gray')==inputs['selftest_sha256'],'Actual simulated DDR image identity')
    require(inputs['transport_version']==0x00020002 and inputs['time_kind']==1 and inputs['time_hz']==100000000,
            'APB v2.2 and shared APB millisecond counter contract')
    for name in [b'c3_shared_time_bind',b'c3_shared_now_ms']:
        require(name in elf,'Linked checked shared-clock backend '+name.decode())
    acceptance=read(ROOT/'logs/c24_acceptance_tests.json')
    require(acceptance['status']=='PASS' and not acceptance['board_inference_passed'],'Offline C24 acceptance-tool tests PASS')
    for name,digest in acceptance['source_sha256'].items():require(sha(ROOT/name)==digest,'Acceptance source '+name)
    video=read(ROOT/'logs/a_c2_video_pc_inference.json')
    require(video['status']=='PASS' and not video['live_camera'] and video['firmware_selftest_input_equal'],
            'Full source pixels -> A capture -> C2 DDR readback -> desktop reference PASS')
    require(video['rtl_report_sha256']==sha(ROOT/'logs/c2_selftest.json'),'Full-video desktop report bound to current RTL run')
    require(video['source_sha256']==sha(ROOT/'tools/check_a_c2_pc.py'),'Full-video desktop checker identity')
    require(video['raw_sha256']==sha(ROOT/'build/c2/a_c2_video_frame0.gray')==inputs['selftest_sha256'],
            'Full-video DDR image equals pinned firmware self-test bytes')
    require(video['capture_metadata_sha256']==sha(ROOT/'build/c2/a_c2_video_frame0.json') and
            video['capture_metadata']['timestamp_origin']=='first_source_DE','Source timestamp metadata identity')
    require('c2_a_video_source #(' in (ROOT/'projects/06_soc_c2/integration/c2_tinyml_soc_top.v').read_text(),
            'Native overlay instantiates full source-pixel A capture')
    require('c2_video_pipeline #(' in (ROOT/'projects/06_soc_c2/integration/c2_tinyml_soc_top.v').read_text(),
            'Native overlay instantiates full-frame video writer and raster scanout')
    fb_cases=[t for t in tests['tests'] if t['name'].startswith('tb_c2_framebuffer')]
    require(len(fb_cases)==3 and all(t['status']=='PASS' for t in fb_cases),
            '1080p video DDR read/write and two concurrent fault/recovery cases PASS')
    tail=read(ROOT/'logs/c2_video_tail.json')
    require(tail['status']=='PASS' and not tail['board_test_passed'],'Independent short video burst and scan backpressure PASS')
    for name,digest in tail['source_sha256'].items():require(sha(ROOT/name)==digest,'Short video burst source '+name)
    c3=read(ROOT/'logs/c3_backend_check.json')
    require(c3['status']=='PASS' and not c3['board_verified'],'C3 actual peripheral RTL/host/RV32 and thermal checks PASS')
    for name,digest in c3['source_sha256'].items():require(sha(ROOT/name)==digest,'C3 backend source '+name)
    require(c3['thermal']['B_C_ABI_policies']['C_masked_accepted']==100,'C3 known-bad-pixel policy accepts 100 saved real B records')
    lib=read(ROOT/'logs/c3_backend_library.json')
    require(lib['status']=='PASS' and sha(ROOT/lib['artifact']['path'])==lib['artifact']['sha256'],'RV32 C3 link library identity')
    for name,digest in lib['header_sha256'].items():require(sha(ROOT/name)==digest,'C3 library header '+name)
    result={'status':'PASS','checks':len(checks),'version':inputs['version'],'board_executed':False,
            'source': 'synthetic full GRAY8 source frames, pinned A capture/BRAM and C2 RTL, DDR model, PC inference; no physical camera',
            'reports':{name:sha(ROOT/name) for name in ['logs/c2_selftest.json','logs/c2_native_synthesis.json',
                       'logs/firmware_c24.json','logs/a_c2_pc_inference.json','logs/a_c2_video_pc_inference.json','logs/c24_acceptance_tests.json','logs/c2_video_tail.json','logs/c3_backend_check.json','logs/c3_backend_library.json']}}
    (ROOT/'logs/c24_package_check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__':main()
