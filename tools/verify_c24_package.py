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
    require(tests['status']=='PASS' and tests['passed']==42,'42 C2/A-source/shared-time RTL runs PASS')
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
    result={'status':'PASS','checks':len(checks),'version':inputs['version'],'board_executed':False,
            'source': 'synthetic A samples, actual A BRAM and C2 RTL, DDR model, PC inference; no physical camera',
            'reports':{name:sha(ROOT/name) for name in ['logs/c2_selftest.json','logs/c2_native_synthesis.json',
                       'logs/firmware_c24.json','logs/a_c2_pc_inference.json','logs/c24_acceptance_tests.json']}}
    (ROOT/'logs/c24_package_check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__':main()
