"""Comparison fixtures are synthetic and must never be used as UART evidence."""
from pathlib import Path
import sys,json,unittest,copy
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"tools"))
sys.path.insert(0,str(ROOT/"build/pc_ai_packages"))
from compare_c1_reference import compare
from pc_model_data import array,sha
from pc_model_compat import desktop_compat
M=json.loads((ROOT/"firmware/c1_static_person_detect/C1_INPUT_MANIFEST.json").read_text(encoding="utf-8"))
R=json.loads((ROOT/"logs/pc_ai/c1_reference.json").read_text(encoding="utf-8"))
def fixture():
    lines=[f"C1|BOOT version={M['version']} clint_hz=100000000",
           "C1|HAL capabilities=1","C1|RAM_PROBE words=256 status=PASS",
           f"C1|MODEL fnv={M['model_fnv']} input_scale_bits=3c008081 input_zero=-1",
           "C1|OUTPUT scale_bits=3b800000 zero=-128 classes=2"]
    for i,s in enumerate(R["samples"]):
        lines += [f"C1|BEGIN sample={s['sample']} frame_id={i} input_fnv={s['input_fnv']}",
                  f"C1|RESULT sample={s['sample']} invoke=0 person={s['person']} no_person={s['no_person']} predicted={s['predicted']} expected={s['expected']}",
                  f"C1|TIME sample={s['sample']} start_ms=100 end_ms=110 ticks_hi=0 ticks_lo=f4240"]
    lines += [f"C1|DONE samples=6 expected_matches=6 version={M['version']}"]
    return "\n".join(lines)
class Tests(unittest.TestCase):
    def test_matching_synthetic_log(self): self.assertEqual(compare(fixture(),M,R)["status"],"PASS")
    def test_score_mismatch(self):
        r=copy.deepcopy(R);r["samples"][0]["person"]+=1
        self.assertEqual(compare(fixture(),M,r)["status"],"FAIL")
    def test_reference_identity(self):
        r=copy.deepcopy(R);r["model_sha256"]="wrong"
        self.assertEqual(compare(fixture(),M,r)["status"],"FAIL")
    def test_missing_session(self): self.assertEqual(compare("",M,R)["status"],"FAIL")
    def test_empty_reference(self):
        r=copy.deepcopy(R);r["samples"]=[]
        self.assertEqual(compare(fixture(),M,r)["status"],"FAIL")
    def test_wrong_reference_input(self):
        r=copy.deepcopy(R);r["samples"][0]["tensor_sha256"]="wrong"
        self.assertEqual(compare(fixture(),M,r)["status"],"FAIL")
    def test_compat_determinism_and_original_preserved(self):
        original=array("mobilenetv1_person_detect_model_data")
        before=sha(original)
        a,report=desktop_compat(original);b,_=desktop_compat(original)
        self.assertEqual(a,b);self.assertEqual(before,sha(original))
        self.assertEqual(len(report["patches"]),14)
        self.assertTrue(report["all_model_data_buffers_unchanged"])
        allowed=set()
        for p in report["patches"]: allowed.update(range(p["offset"],p["offset"]+4))
        self.assertTrue(all(i in allowed for i,(x,y) in enumerate(zip(original,a)) if x!=y))
        self.assertNotEqual(sha(a),sha(original))
if __name__=="__main__": unittest.main()

