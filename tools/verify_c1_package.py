"""Verify local C1 artifacts against build records and the existing FPGA/ROM.
No hardware communication, Flash writes, or inference."""
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    fw=ROOT/"firmware/c1_static_person_detect"
    build=read(ROOT/"logs/firmware_c1.json")
    inputs=read(fw/"C1_INPUT_MANIFEST.json")
    checks=[]
    def require(condition,label):
        if not condition: raise ValueError(label)
        checks.append(label)
    require(build["status"]=="PASS","C1 compiler report PASS")
    require(not build["board_inference_passed"],"Build report does not claim board inference")
    artifacts=[]
    for item in build["artifacts"]:
        p=fw/Path(item["path"]).name
        require(p.is_file() and p.stat().st_size==item["bytes"] and sha(p)==item["sha256"].lower(),
                "CPU artifact "+p.name)
        artifacts.append({"path":str(p.relative_to(ROOT)),"sha256":sha(p),"bytes":p.stat().st_size})
    elf=(fw/"tinyml_c1.elf").read_bytes()
    require(elf[:6]==b"\x7fELF\x01\x01" and struct.unpack_from("<H",elf,18)[0]==243 and
            struct.unpack_from("<I",elf,24)[0]==0x1000,"ELF32 little-endian RISC-V entry 0x1000")
    require((fw/"tinyml_c1.bin").stat().st_size<=4194304,"BIN within boot copy capacity")
    hashes={n.replace('\\','/'):d for n,d in inputs['source_hashes'].items()}
    selected={};frozen=fw/'C1_FROZEN_SOURCES.json'
    release=read(frozen) if frozen.is_file() else {'files':{}}
    for name,digest in hashes.items():
        original=ROOT/name;resolved=original
        if sha(original)!=digest:
            allowed={"team_work/03_ai_soc/c3_hal/"+n for n in ["c3_hal.h","c3_hal.c","c3_sapphire_time.c"]}
            item=release.get('files',{}).get(name)
            if name not in allowed or not item or release.get('version')!=inputs['version'] or item['sha256']!=digest:
                raise ValueError('No matching release source: '+name)
            resolved=(ROOT/item['path']).resolve()
            if not resolved.is_relative_to((fw/'frozen_c3_hal').resolve()):raise ValueError('Snapshot path escapes C1 release')
        require(sha(resolved)==digest,"Release source identity "+name)
        selected[name]=resolved
    # Critical generated overlay must match its primary source.
    app=Path(inputs["app"])
    for original,dest in {
        ROOT/"team_work/03_ai_soc/c1/main.cc":"main.cc",
        ROOT/"team_work/shared/include/cooperation_v1.h":"cooperation_v1.h",
        ROOT/"team_work/shared/src/cooperation_v1.c":"cooperation_v1.c",
        **{ROOT/"team_work/03_ai_soc/c3_hal"/name:name for name in ["c3_hal.h","c3_hal.c","c3_sapphire_time.c"]}
    }.items():
        require(sha(selected[original.relative_to(ROOT).as_posix()])==sha(app/"src"/dest),"Release overlay "+dest)
    require(inputs["version"] in (app/"src/c1_build_id.h").read_text(),"Generated build version")
    structure=read(ROOT/"logs/c1_model_structure.json")
    for key in ["schema_version","input","output"]:
        require(structure[key]==inputs["model_contract"][key],"Model structure "+key)
    fpga_dir=ROOT/"fpga_bitstreams/tinyml_225mhz"
    fpga=read(fpga_dir/"BUILD_RECORD.json")
    for item in fpga["artifacts"]:
        p=fpga_dir/Path(item["file"]).name
        require(sha(p)==item["sha256"].lower(),"FPGA baseline "+p.name)
        artifacts.append({"path":str(p.relative_to(ROOT)),"sha256":sha(p),"bytes":p.stat().st_size})
    boot=read(ROOT/"logs/bootloader_build.json")
    for item in boot["lanes"]:
        p=ROOT/"projects/03_tinyml/ip/sapphire_soc"/Path(item["path"]).name
        require(sha(p)==item["sha256"].lower(),"Boot ROM "+p.name)
    require(boot["flash_offset"]=="0x00380000" and boot["application_ram_address"]=="0x00001000" and
            boot["application_copy_capacity"]==4194304,"Recorded boot layout")
    result={"status":"PASS","scope":"Local file/build/model/ROM consistency only",
            "version":inputs["version"],"checks":len(checks),"artifacts":artifacts,
            "release_source_snapshots":{n:p.relative_to(ROOT).as_posix() for n,p in selected.items() if p!=ROOT/n},
            "flash_offset":"0x00380000","ram_entry":"0x00001000","boot_copy_bytes":4194304,
            "physical_flash_verified":False,"board_inference_passed":False,
            "pc_golden_inference_compared":False,"live_camera_inference_passed":False}
    (fw/"C1_PACKAGE.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    (ROOT/"logs/c1_package_check.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"status":"PASS","checks":len(checks),"version":inputs["version"]}))
if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        failure={"status":"FAIL","scope":"Local package verification only",
                 "error":str(exc),"board_inference_passed":False}
        for p in [ROOT/"logs/c1_package_check.json",ROOT/"firmware/c1_static_person_detect/C1_PACKAGE.json"]:
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(failure,indent=2),encoding="utf-8")
        print(json.dumps(failure))
        raise SystemExit(1)

