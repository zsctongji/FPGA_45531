"""Prepare a separate C1 app; never overwrite the validated tinyml_pdti8 app."""
from pathlib import Path
import hashlib, json, re, shutil
ROOT = Path(__file__).resolve().parents[1]
STANDALONE = ROOT/"projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/software/standalone"
SOURCE = STANDALONE/"tinyml_pdti8"
TARGET = STANDALONE/"tinyml_c1"
def fnv(data):
    result = 2166136261
    for b in data:
        result = ((result ^ b)*16777619) & 0xffffffff
    return result
def array(name):
    for p in (SOURCE/"src/model").iterdir():
        if p.suffix not in (".h",".cc"): continue
        found = re.search(r"\b"+name+r"\s*\[[^\]]*\]\s*=\s*\{(.*?)\}", p.read_text(errors="replace"), re.S)
        if found:
            body = re.sub(r"/\*.*?\*/|//[^\n]*", "", found[1], flags=re.S)
            return bytes(int(x.strip(),0) & 255 for x in body.split(",") if x.strip())
    raise ValueError(name)
if TARGET.exists() and not (TARGET/"C1_PREPARATION.json").exists():
    raise SystemExit("Refusing to overwrite an unrelated existing app")
if not TARGET.exists():
    shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("build","build_ours",".settings"))
else:
    # Refresh vendored files in the generated app before applying the overlay.
    shutil.copytree(SOURCE/"src", TARGET/"src", dirs_exist_ok=True)
overlay = {
    ROOT/"team_work/03_ai_soc/c1/main.cc": "main.cc",
    ROOT/"team_work/shared/include/cooperation_v1.h": "cooperation_v1.h",
    ROOT/"team_work/shared/src/cooperation_v1.c": "cooperation_v1.c",
}
for name in ["c3_hal.h","c3_hal.c","c3_sapphire_time.c"]:
    overlay[ROOT/"team_work/03_ai_soc/c3_hal"/name] = name
for src,dest in overlay.items():
    shutil.copy2(src, TARGET/"src"/dest)
makefile=(SOURCE/"makefile").read_text()
makefile = makefile.replace("PROJ_NAME=tinyml_pdti8","PROJ_NAME=tinyml_c1")
makefile = makefile.replace("include ${STANDALONE}/common/tinyml_standalone.mk", "include c1_standalone.mk")
(TARGET/"makefile").write_text(makefile)
# Native Python creates object directories; no dependency on the packaged mkdir.exe.
local_mk=(STANDALONE/"common/tinyml_standalone.mk").read_text()
local_mk=local_mk.replace("@mkdir -p $(dir $(OBJS))", "@echo C1 object directories prepared")
(TARGET/"c1_standalone.mk").write_text(local_mk)
for p in (TARGET/"src").rglob("*"):
    if p.is_file(): (TARGET/"build_ours/out"/p.relative_to(TARGET).parent).mkdir(parents=True,exist_ok=True)
(TARGET/"build_ours/common").mkdir(parents=True,exist_ok=True)
contract_path=ROOT/"team_work/03_ai_soc/c1/model_contract.json"
contract=json.loads(contract_path.read_text(encoding="utf-8"))
hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in overlay}
hashes[str(contract_path.relative_to(ROOT))]=hashlib.sha256(contract_path.read_bytes()).hexdigest()
for p in (SOURCE/"src").rglob("*"):
    if p.is_file() and p.name != "main.cc":
        hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
for p in [STANDALONE/"common/tinyml_lib.a", STANDALONE/"../../bsp/efinix/EfxSapphireSoc/include/soc.h"]:
    hashes[str(p.resolve().relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
identity=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
(TARGET/"src/c1_build_id.h").write_text(
    '#define C1_BUILD_ID "c1-'+identity+'"\n' +
    '#define C1_INPUT_SCALE_BITS 0x'+contract["input"]["scale_bits"]+'u\n' +
    '#define C1_INPUT_ZERO ('+str(contract["input"]["zero"])+')\n' +
    '#define C1_OUTPUT_SCALE_BITS 0x'+contract["output"]["scale_bits"]+'u\n' +
    '#define C1_OUTPUT_ZERO ('+str(contract["output"]["zero"])+')\n')
samples=[]
for name,symbol,pre,expected in [
    ("person","g_person_data",True,1),("no_person","g_no_person_data",True,0),
    ("people1","people1_data",False,1),("people2","people2_data",False,1),
    ("no_people1","no_people1_data",False,0),("no_people2","no_people2_data",False,0)]:
    data=array(symbol)
    assert len(data)==9216, (name,len(data))
    tensor=data if pre else bytes((b-128)&255 for b in data)
    samples.append({"sample":name,"input_fnv":format(fnv(tensor),"x"),
                    "tensor_sha256":hashlib.sha256(tensor).hexdigest(),
                    "vendor_prenormalized":pre,"expected":expected,"bytes":len(data)})
model=array("mobilenetv1_person_detect_model_data")
assert hashlib.sha256(model).hexdigest()==contract["model_sha256"],"Model changed: re-inspect quantization"
record={"version":"c1-"+identity,"source":str(SOURCE),"app":str(TARGET),
        "model_fnv":format(fnv(model),"x"),"model_sha256":hashlib.sha256(model).hexdigest(),
        "samples":samples,"source_hashes":hashes,"model_contract":contract,"board_inference_passed":False}
(TARGET/"C1_PREPARATION.json").write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
out=ROOT/"firmware/c1_static_person_detect"
out.mkdir(parents=True,exist_ok=True)
(out/"C1_INPUT_MANIFEST.json").write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"app":str(TARGET),"version":record["version"],"samples":len(samples)}))

