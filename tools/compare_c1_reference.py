"""Compare captured C1 raw scores to the desktop compatibility reference.
Passing is a log comparison, not proof of board provenance or real-camera accuracy."""
import argparse,json,re
from pathlib import Path
from pc_model_data import ROOT,sha
from check_c1_uart import check
def compare(text,manifest,reference):
    validation=check(text,manifest)
    errors=list(validation["errors"]); differences=[]
    if reference.get("status")!="PASS" or reference.get("model_sha256")!=manifest["model_sha256"] or \
       reference.get("c1_version")!=manifest["version"]:
        errors.append("Reference build/model identity mismatch")
    reference_samples=reference.get("samples",[])
    if [s.get("sample") for s in reference_samples]!=[s["sample"] for s in manifest["samples"]]:
        errors.append("Reference sample set incomplete or out of order")
    for row,expected in zip(reference_samples,manifest["samples"]):
        if row.get("tensor_sha256")!=expected["tensor_sha256"] or row.get("input_fnv")!=expected["input_fnv"]:
            errors.append("Reference input identity mismatch")
    records={}
    for line in re.split(r"[\r\n]+",text):
        if line.strip().startswith("C1|RESULT "):
            fields=dict(re.findall(r"(\w+)=([^\s]+)",line))
            records[fields.get("sample")]=fields
    for sample in reference_samples:
        row=records.get(sample["sample"])
        try:
            delta={key:int(row[key])-int(sample[key]) for key in ["person","no_person"]}
            differences.append({"sample":sample["sample"],"delta":delta})
            if any(delta.values()): errors.append("Raw INT8 score mismatch: "+sample["sample"])
        except (TypeError,KeyError,ValueError):
            errors.append("Missing/malformed score: "+sample["sample"])
    return {"status":"PASS" if not errors else "FAIL","scope":"Strict C1 log versus desktop reference comparison only",
            "errors":errors,"differences":differences,
            "source_model_sha256":manifest["model_sha256"],
            "runtime_model_sha256":reference.get("runtime_model_sha256"),
            "desktop_metadata_compatibility_copy":True,
            "board_capture_provenance_verified":False}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("log",type=Path)
    ap.add_argument("--reference",type=Path,default=ROOT/"logs/pc_ai/c1_reference.json")
    ap.add_argument("--output",type=Path,default=ROOT/"logs/pc_ai/c1_comparison.json")
    a=ap.parse_args()
    manifest=json.loads((ROOT/"firmware/c1_static_person_detect/C1_INPUT_MANIFEST.json").read_text(encoding="utf-8"))
    reference=json.loads(a.reference.read_text(encoding="utf-8"))
    raw=a.log.read_bytes()
    result=compare(raw.decode("utf-8-sig",errors="replace"),manifest,reference)
    result["log_sha256"]=sha(raw)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    raise SystemExit(result["status"]!="PASS")
if __name__=="__main__": main()

