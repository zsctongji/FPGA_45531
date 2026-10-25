"""Synthetic UART fixtures only. Never save these as measured board evidence."""
from pathlib import Path
import copy
import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('c24_parser', ROOT/'tools/check_c24_uart.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
DATA = bytes(n & 255 for n in range(9216))
RAW, TENSOR = parser.fnv(DATA), parser.fnv(bytes((n - 128) & 255 for n in DATA))
M = {'version': 'c24-parser-synthetic', 'source_policy': 'pad54_candidate',
     'model_fnv': '12345678', 'selftest_raw_fnv': f'{RAW:08x}', 'selftest_tensor_fnv': f'{TENSOR:08x}',
     'transport_version': 0x00020002, 'time_kind': 1, 'time_hz': 100000000,
     'config': {'enable_live': False, 'verified_map': False, 'verified_shared_time': False}}


def fixture(live=False, wrap=False):
    flags = int(live)
    lines = [f'C24|BOOT version={M["version"]} policy=pad54_candidate source=synthetic_selftest live={flags} map_verified={flags} shared_time_verified={flags} transport=20002 clint_hz=100000000',
             'C24|MODEL fnv=12345678',
             f'C24|SELFTEST_BEGIN raw_fnv={RAW:x} tensor_fnv={TENSOR:x} synthetic=1',
             f'C24|SELFTEST raw_fnv={RAW:x} tensor_fnv={TENSOR:x} no_person=-6 person=6 person_u8=134 ticks_hi=0 ticks_lo=f4240 synthetic=1']
    if not live:
        return '\n'.join(lines + ['C24|LIVE_DISABLED live=0 map_verified=0 shared_time_verified=0',
                                  f'C24|DONE version={M["version"]} mode=selftest'])
    origin = 0xfffffff0 if wrap else 100
    lines.append(f'C24|LIVE_READY version={M["version"]} capabilities=7 policy=pad54_candidate time_kind=1 time_hz=100000000 now_ms={origin} source=c2_samples')
    for i in range(3):
        stamp = (origin + i*20) & 0xffffffff
        received, start, end = [(stamp+n) & 0xffffffff for n in (1, 2, 10)]
        frame = ((0xfffffffe if wrap else 42) + i) & 0xffffffff
        lines += [f'C24|INFER_BEGIN sequence={i+1}', f'C24|INFER_END sequence={i+1} status=0',
                  f'C24|FRAME status=0 valid=1 frame_id={frame} timestamp_ms={stamp} raw_fnv={RAW:x} tensor_fnv={TENSOR:x} person=6 no_person=-6 person_u8=134 received_ms={received} start_ms={start} end_ms={end} sequence={i+1}']
    return '\n'.join(lines)


def validate(text=None, live=False, **kwargs):
    manifest = copy.deepcopy(M)
    if live:
        manifest['config'] = dict.fromkeys(manifest['config'], True)
    return parser.check(fixture(live) if text is None else text, manifest, 'live' if live else 'selftest', **kwargs)


class C24ParserTests(unittest.TestCase):
    def fails(self, text, live=False, **kwargs):
        self.assertEqual(validate(text, live, **kwargs)['status'], 'FAIL')

    def test_static_complete(self):
        result = validate()
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['board_inference_passed'])
        self.assertFalse(result['live_camera_passed'])
        self.assertIsNone(result['reference_agreement'])

    def test_live_complete(self):
        result = validate(live=True)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['frame_ids'], [42, 43, 44])
        self.assertEqual(result['inference_ms'], [8, 8, 8])

    def test_wrap_time_and_frame(self):
        self.assertEqual(validate(fixture(True, True), True)['status'], 'PASS')

    def test_crlf_and_noise(self):
        self.assertEqual(validate('vendor banner\n'+fixture().replace('\n', '\n\r'))['status'], 'PASS')

    def test_vendor_hex_prefix(self):
        text=fixture().replace('transport=20002','transport=0x20002').replace('fnv=12345678','fnv=0x12345678')
        text=text.replace(f'raw_fnv={RAW:x}',f'raw_fnv=0x{RAW:x}').replace(f'tensor_fnv={TENSOR:x}',f'tensor_fnv=0x{TENSOR:x}')
        text=text.replace('ticks_hi=0','ticks_hi=0x0').replace('ticks_lo=f4240','ticks_lo=0xf4240')
        self.assertEqual(validate(text)['status'],'PASS')

    def test_cli_manifest_and_log_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);log=path/'synthetic_fixture.log';manifest=path/'manifest.json';output=path/'result.json'
            log.write_text(fixture(),encoding='utf-8');manifest.write_text(json.dumps(M),encoding='utf-8')
            result=subprocess.run([sys.executable,str(ROOT/'tools/check_c24_uart.py'),str(log),'--manifest',str(manifest),'--output',str(output)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads(output.read_text())
            self.assertEqual(report['log_sha256'],hashlib.sha256(log.read_bytes()).hexdigest())
            self.assertEqual(report['manifest_sha256'],hashlib.sha256(manifest.read_bytes()).hexdigest())

    def test_empty(self): self.fails('')
    def test_truncated_selftest(self): self.fails('\n'.join(fixture().splitlines()[:3]))
    def test_missing_done(self): self.fails('\n'.join(fixture().splitlines()[:-1]))
    def test_double_boot(self): self.fails(fixture()+'\n'+fixture())
    def test_failed(self): self.fails(fixture()+'\nC24|FAIL stage=invoke status=-1')
    def test_version(self): self.fails(fixture().replace(M['version'], 'old'))
    def test_model(self): self.fails(fixture().replace('fnv=12345678', 'fnv=0'))
    def test_tensor(self): self.fails(fixture().replace(f'tensor_fnv={TENSOR:x}', 'tensor_fnv=0'))
    def test_raw(self): self.fails(fixture().replace(f'raw_fnv={RAW:x}', 'raw_fnv=0'))
    def test_synthetic_flag(self): self.fails(fixture().replace('synthetic=1', 'synthetic=0'))
    def test_ticks_zero(self): self.fails(fixture().replace('ticks_lo=f4240', 'ticks_lo=0'))
    def test_score_range(self): self.fails(fixture().replace('person=6 ', 'person=128 '))
    def test_score_mapping(self): self.fails(fixture().replace('person_u8=134', 'person_u8=1'))
    def test_duplicate_field(self): self.fails(fixture().replace('person_u8=134', 'person_u8=134 person_u8=134'))
    def test_unknown_record(self): self.fails(fixture()+'\nC24|MYSTERY value=1')
    def test_transport(self): self.fails(fixture().replace('transport=20002', 'transport=20001'))
    def test_clock(self): self.fails(fixture(True).replace('time_hz=100000000', 'time_hz=50000000'), True)
    def test_kind(self): self.fails(fixture(True).replace('time_kind=1', 'time_kind=2'), True)
    def test_capabilities(self): self.fails(fixture(True).replace('capabilities=7', 'capabilities=3'), True)
    def test_min_frames(self): self.fails(fixture(True), True, min_frames=4)
    def test_hung_inference(self): self.fails(fixture(True)+'\nC24|INFER_BEGIN sequence=4', True)
    def test_duplicate_sequence(self): self.fails(fixture(True).replace('sequence=2', 'sequence=1'), True)
    def test_rejected_frame(self): self.fails(fixture(True).replace('status=0 valid=1', 'status=-9 valid=0'), True)
    def test_duplicate_frame(self): self.fails(fixture(True).replace('frame_id=43', 'frame_id=42'), True)
    def test_stale(self): self.fails(fixture(True).replace('timestamp_ms=100', 'timestamp_ms=4294966000'), True)
    def test_future(self): self.fails(fixture(True).replace('timestamp_ms=100', 'timestamp_ms=103'), True)
    def test_time_reversal(self): self.fails(fixture(True).replace('end_ms=110', 'end_ms=101'), True)
    def test_negative_unsigned(self): self.fails(fixture(True).replace('frame_id=42', 'frame_id=-1'), True)
    def test_bad_hash_syntax(self): self.fails(fixture(True).replace(f'raw_fnv={RAW:x}', 'raw_fnv=xyz'), True)
    def test_wrong_manifest_mode(self):
        self.assertEqual(parser.check(fixture(True), M, 'live')['status'], 'FAIL')

    def test_optional_reference(self):
        reference = {'status': 'PASS', 'raw_fnv': M['selftest_raw_fnv'], 'tensor_fnv': M['selftest_tensor_fnv'], 'person': 6, 'no_person': -6}
        self.assertTrue(validate(reference=reference)['reference_agreement'])
        reference['person'] = 7
        self.fails(fixture(), reference=reference)

    def test_live_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            for frame in (42, 43, 44):
                (Path(directory)/f'frame_{frame}.gray').write_bytes(DATA)
            result = validate(live=True, frame_dir=directory)
            self.assertEqual(result['status'], 'PASS')
            self.assertTrue(result['live_input_bytes_verified'])
            (Path(directory)/'frame_43.gray').write_bytes(bytes(9216))
            self.fails(fixture(True), True, frame_dir=directory)


if __name__ == '__main__':
    unittest.main()
