"""Validate one boot session against the exact C1 build/input manifest.
Parser acceptance confirms log consistency, not provenance or PC-reference accuracy."""
import argparse, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check(text, manifest):
    # CR/LF may be delivered in either order by the existing UART library.
    lines=[s.strip() for s in re.split(r"[\r\n]+",text) if s.strip().startswith("C1|")]
    boots=[i for i,s in enumerate(lines) if s.startswith("C1|BOOT ")]
    errors=[]
    if len(boots)!=1: errors.append("Require exactly one boot session; capture a fresh single run")
    records={}
    for s in lines:
        kind=s.split()[0][3:]
        fields=dict(re.findall(r"(\w+)=([^\s]+)",s))
        records.setdefault(kind,[]).append(fields)
    for kind in ["BOOT","RAM_PROBE","MODEL","OUTPUT","DONE","HAL"]:
        if len(records.get(kind,[]))!=1: errors.append("Missing/duplicate "+kind)
    if records.get("FAIL"): errors.append("Firmware reported FAIL")
    try:
        boot=records["BOOT"][0]; done=records["DONE"][0]
        if boot["version"]!=manifest["version"] or done["version"]!=manifest["version"]:
            errors.append("Build version mismatch")
        if int(boot["clint_hz"])!=100000000: errors.append("CLINT frequency mismatch")
        if records["RAM_PROBE"][0]["status"]!="PASS": errors.append("RAM probe failed")
        if int(records["HAL"][0]["capabilities"])!=1: errors.append("Unexpected C1 HAL")
        if int(records["MODEL"][0]["fnv"],16)!=int(manifest["model_fnv"],16):
            errors.append("Model checksum mismatch")
        contract=manifest["model_contract"]
        if int(records["MODEL"][0]["input_scale_bits"],16)!=int(contract["input"]["scale_bits"],16) or int(records["MODEL"][0]["input_zero"])!=contract["input"]["zero"]:
            errors.append("Input quantization mismatch")
        if int(records["OUTPUT"][0]["scale_bits"],16)!=int(contract["output"]["scale_bits"],16) or int(records["OUTPUT"][0]["zero"])!=contract["output"]["zero"] or int(records["OUTPUT"][0]["classes"])!=2:
            errors.append("Output quantization mismatch")
        if int(done["samples"])!=6: errors.append("Incomplete inference set")
        begin=records.get("BEGIN",[]); results=records.get("RESULT",[]); times=records.get("TIME",[])
        names=[s["sample"] for s in manifest["samples"]]
        if [r["sample"] for r in begin]!=names or [r["sample"] for r in results]!=names or [r["sample"] for r in times]!=names:
            errors.append("Sample order, count or uniqueness mismatch")
        expected_order=["BOOT","HAL","RAM_PROBE","MODEL","OUTPUT"]+["BEGIN","RESULT","TIME"]*6+["DONE"]
        if [s.split()[0][3:] for s in lines]!=expected_order: errors.append("Record sequence mismatch")
        matches=0
        for i,sample in enumerate(manifest["samples"]):
            b,r,t=begin[i],results[i],times[i]
            if int(b["frame_id"])!=i or int(b["input_fnv"],16)!=int(sample["input_fnv"],16):
                errors.append("Input identity mismatch: "+sample["sample"])
            p,n=int(r["person"]),int(r["no_person"])
            pred=1 if p>n else (0 if n>p else -1)
            if not (-128<=p<=127 and -128<=n<=127) or int(r["invoke"])!=0:
                errors.append("Invalid output or failed Invoke")
            if int(r["predicted"])!=pred or int(r["expected"])!=sample["expected"]:
                errors.append("Class decision mismatch")
            matches+=int(pred==sample["expected"])
            ticks=(int(t["ticks_hi"],16)<<32)|int(t["ticks_lo"],16)
            elapsed_ms=(int(t["end_ms"])-int(t["start_ms"]))&0xffffffff
            if not ticks or elapsed_ms>=0x80000000 or abs(elapsed_ms-ticks/100000)>50:
                errors.append("Timer mismatch: "+sample["sample"])
        if int(done["expected_matches"])!=matches: errors.append("Summary match count mismatch")
        if matches!=6: errors.append("At least one static sample disagrees with its expected label; investigate")
    except (KeyError,ValueError,IndexError,TypeError) as exc:
        errors.append("Malformed/incomplete record: "+str(exc))
    return {"status":"PASS" if not errors else "FAIL","errors":errors,
            "scope":"UART log consistency and six static-label checks; not proof of capture provenance or PC golden-reference agreement"}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("log",type=Path)
    ap.add_argument("--manifest",type=Path,default=ROOT/"firmware/c1_static_person_detect/C1_INPUT_MANIFEST.json")
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    result=check(a.log.read_text(encoding="utf-8-sig",errors="replace"),json.loads(a.manifest.read_text(encoding="utf-8-sig")))
    if a.output: a.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    raise SystemExit(result["status"]!="PASS")
if __name__=="__main__": main()

