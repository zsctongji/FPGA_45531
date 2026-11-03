"""Read exact byte arrays from the supplied model sources; no app preparation side effects."""
from pathlib import Path
import re,hashlib
ROOT=Path(__file__).resolve().parents[1]
MODEL_DIR=ROOT/"projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/software/standalone/tinyml_pdti8/src/model"
SAMPLES=[("person","g_person_data",True,1),("no_person","g_no_person_data",True,0),
         ("people1","people1_data",False,1),("people2","people2_data",False,1),
         ("no_people1","no_people1_data",False,0),("no_people2","no_people2_data",False,0)]
def array(name):
    for p in MODEL_DIR.iterdir():
        if p.suffix not in (".h",".cc"): continue
        match=re.search(r"\b"+name+r"\s*\[[^\]]*\]\s*=\s*\{(.*?)\}",p.read_text(errors="replace"),re.S)
        if match:
            body=re.sub(r"/\*.*?\*/|//[^\n]*","",match[1],flags=re.S)
            return bytes(int(x.strip(),0)&255 for x in body.split(",") if x.strip())
    raise ValueError(name)
def fnv(data):
    result=2166136261
    for b in data: result=((result^b)*16777619)&0xffffffff
    return result
def tensor_bytes(data,prenormalized):
    return data if prenormalized else bytes((b-128)&255 for b in data)
def sha(data): return hashlib.sha256(data).hexdigest()

