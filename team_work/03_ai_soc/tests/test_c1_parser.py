"""Synthetic fixtures validate the parser only; never board evidence."""
from pathlib import Path
import importlib.util, json, unittest
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location("parser",ROOT/"tools/check_c1_uart.py")
parser=importlib.util.module_from_spec(spec); spec.loader.exec_module(parser)
M=json.loads((ROOT/"firmware/c1_static_person_detect/C1_INPUT_MANIFEST.json").read_text(encoding="utf-8"))
def fixture():
    lines=[f"C1|BOOT version={M['version']} clint_hz=100000000",
           "C1|HAL capabilities=1","C1|RAM_PROBE words=256 status=PASS",
           f"C1|MODEL fnv={M['model_fnv']} input_scale_bits=3c008081 input_zero=-1",
           "C1|OUTPUT scale_bits=3b800000 zero=-128 classes=2"]
    for i,s in enumerate(M["samples"]):
        p,n=(100,-100) if s["expected"] else (-100,100)
        lines += [f"C1|BEGIN sample={s['sample']} frame_id={i} input_fnv={s['input_fnv']}",
                  f"C1|RESULT sample={s['sample']} invoke=0 person={p} no_person={n} predicted={s['expected']} expected={s['expected']}",
                  f"C1|TIME sample={s['sample']} start_ms=100 end_ms=110 ticks_hi=0 ticks_lo=f4240"]
    lines += [f"C1|DONE samples=6 expected_matches=6 version={M['version']}"]
    return "\n".join(lines)
class ParserTests(unittest.TestCase):
    def test_valid_fixture(self): self.assertEqual(parser.check(fixture(),M)["status"],"PASS")
    def test_empty(self): self.assertEqual(parser.check("",M)["status"],"FAIL")
    def test_truncated(self): self.assertEqual(parser.check("\n".join(fixture().splitlines()[:-1]),M)["status"],"FAIL")
    def test_wrong_version(self): self.assertEqual(parser.check(fixture().replace(M["version"],"old"),M)["status"],"FAIL")
    def test_wrong_checksum(self):
        self.assertEqual(parser.check(fixture().replace("input_fnv="+M["samples"][0]["input_fnv"],"input_fnv=0"),M)["status"],"FAIL")
    def test_reboot(self): self.assertEqual(parser.check(fixture()+"\n"+fixture(),M)["status"],"FAIL")
    def test_fail_line(self): self.assertEqual(parser.check(fixture()+"\nC1|FAIL stage=trap",M)["status"],"FAIL")
    def test_timer(self): self.assertEqual(parser.check(fixture().replace("ticks_lo=f4240","ticks_lo=0"),M)["status"],"FAIL")
    def test_wrong_quantization(self):
        self.assertEqual(parser.check(fixture().replace("input_zero=-1","input_zero=-128"),M)["status"],"FAIL")
    def test_reordered(self):
        lines=fixture().splitlines(); lines[5],lines[6]=lines[6],lines[5]
        self.assertEqual(parser.check("\n".join(lines),M)["status"],"FAIL")
    def test_crlf(self): self.assertEqual(parser.check(fixture().replace("\n","\n\r"),M)["status"],"PASS")
if __name__=="__main__": unittest.main()

