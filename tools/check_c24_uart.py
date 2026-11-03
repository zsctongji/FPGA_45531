"""Check one C24 UART session. Acceptance proves consistency, not provenance.
Synthetic parser fixtures, PC model results and camera/board evidence stay separate.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASK = 0xffffffff


def fnv(data):
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & MASK
    return value


def check(text, manifest, mode='selftest', min_frames=3, reference=None, frame_dir=None):
    errors, records = [], []
    valid_frames, durations, ages = [], [], []
    result = {'status': 'FAIL', 'mode': mode, 'errors': errors,
              'scope': 'C24 UART consistency only; physical board, camera, preprocessing quality and timing signoff require separate evidence',
              'board_inference_passed': False, 'live_camera_passed': False,
              'preprocess_policy_approved': False, 'reference_agreement': None,
              'live_input_bytes_verified': False}
    try:
        if mode not in ('selftest', 'live') or not 1 <= min_frames <= 1000000:
            raise ValueError('Invalid mode/min_frames')
        for line in re.split(r'[\r\n]+', text):
            line = line.strip()
            if not line.startswith('C24|'):
                continue
            tokens = line.split()
            kind, fields = tokens[0][4:], {}
            for token in tokens[1:]:
                if not re.fullmatch(r'[a-z_][a-z0-9_]*=[^\s=]+', token):
                    raise ValueError('Malformed field: ' + token)
                key, value = token.split('=', 1)
                if key in fields:
                    raise ValueError('Duplicate field: ' + key)
                fields[key] = value
            records.append((kind, fields))

        def require(ok, message):
            if not ok:
                raise ValueError(message)

        def number(fields, name, hex_value=False, signed=False):
            raw = fields[name]
            pattern = r'(?:0x)?[0-9a-fA-F]{1,8}' if hex_value else (r'-?\d+' if signed else r'\d+')
            require(bool(re.fullmatch(pattern, raw)), 'Invalid number: ' + name)
            value = int(raw, 16 if hex_value else 10)
            low, high = (-2147483648, 2147483647) if signed else (0, MASK)
            require(low <= value <= high, 'Out of range: ' + name)
            return value

        def age(later, earlier):
            value = (later - earlier) & MASK
            require(value <= 1000, 'Future/expired/reversed shared timestamp')
            return value

        cursor = 0

        def take(kind):
            nonlocal cursor
            require(cursor < len(records), 'Missing record: ' + kind)
            actual, fields = records[cursor]
            require(actual == kind, 'Expected ' + kind + ', got ' + actual)
            cursor += 1
            return fields

        require(sum(k == 'BOOT' for k, _ in records) == 1, 'Require exactly one complete boot session')
        require(not any(k == 'FAIL' for k, _ in records), 'Firmware reported FAIL')
        boot = take('BOOT')
        require(boot['version'] == manifest['version'], 'Build version mismatch')
        require(boot['policy'] == manifest['source_policy'] and boot['source'] == 'synthetic_selftest', 'Input policy/source mismatch')
        config = manifest['config']
        for key, option in [('live', 'enable_live'), ('map_verified', 'verified_map'), ('shared_time_verified', 'verified_shared_time')]:
            require(number(boot, key) == int(config[option]), 'Build configuration mismatch: ' + key)
        require(number(boot, 'transport', True) == manifest['transport_version'] == 0x00020002, 'APB transport mismatch')
        require(number(boot, 'clint_hz') == 100000000, 'CLINT frequency mismatch')
        model = take('MODEL')
        require(number(model, 'fnv', True) == int(manifest['model_fnv'], 16), 'Model identity mismatch')
        begin, selftest = take('SELFTEST_BEGIN'), take('SELFTEST')
        for fields in (begin, selftest):
            require(number(fields, 'synthetic') == 1, 'Self-test must be identified as synthetic')
            for key in ('raw_fnv', 'tensor_fnv'):
                require(number(fields, key, True) == int(manifest['selftest_' + key], 16), 'Self-test input mismatch: ' + key)
        person, no_person = number(selftest, 'person', signed=True), number(selftest, 'no_person', signed=True)
        require(-128 <= person <= 127 and -128 <= no_person <= 127, 'Self-test INT8 output range')
        require(number(selftest, 'person_u8') == person + 128, 'Self-test display score mismatch')
        ticks = (number(selftest, 'ticks_hi', True) << 32) | number(selftest, 'ticks_lo', True)
        require(0 < ticks < (1 << 63), 'Missing/invalid self-test duration')
        result['selftest_ms'] = ticks / 100000
        result['version'] = boot['version']
        if reference is not None:
            require(reference['status'] == 'PASS', 'Reference report is not PASS')
            for key in ('raw_fnv', 'tensor_fnv'):
                require(int(reference[key], 16) == int(manifest['selftest_' + key], 16), 'Reference input differs')
            require(reference['person'] == person and reference['no_person'] == no_person, 'Raw INT8 differs from desktop compatibility-model reference')
            result['reference_agreement'] = True
        if mode == 'selftest':
            require(not config['enable_live'], 'Self-test-only acceptance requires a non-live build')
            disabled = take('LIVE_DISABLED')
            for key, option in [('live', 'enable_live'), ('map_verified', 'verified_map'), ('shared_time_verified', 'verified_shared_time')]:
                require(number(disabled, key) == int(config[option]), 'LIVE_DISABLED flags mismatch')
            done = take('DONE')
            require(done['version'] == manifest['version'] and done['mode'] == 'selftest', 'Completion identity mismatch')
        else:
            require(all(config[k] for k in ('enable_live', 'verified_map', 'verified_shared_time')), 'Live acceptance requires a live-build manifest')
            ready = take('LIVE_READY')
            require(ready['version'] == manifest['version'] and ready['policy'] == manifest['source_policy'], 'Live identity mismatch')
            require(number(ready, 'capabilities') == 7, 'Required RX/source/time capabilities missing')
            require(number(ready, 'time_kind') == manifest['time_kind'] == 1, 'Wrong shared clock')
            require(number(ready, 'time_hz') == manifest['time_hz'] == 100000000, 'Wrong shared clock frequency')
            require(ready['source'] == 'c2_samples', 'Wrong live input boundary')
            previous_end, previous_id = number(ready, 'now_ms'), None
            sequence = 0
            while cursor < len(records):
                started, ended, frame = take('INFER_BEGIN'), take('INFER_END'), take('FRAME')
                sequence += 1
                require(number(started, 'sequence') == number(ended, 'sequence') == number(frame, 'sequence') == sequence, 'Missing/duplicate/out-of-order inference')
                require(number(ended, 'status', signed=True) == number(frame, 'status', signed=True) == 0 and number(frame, 'valid') == 1, 'Rejected frame or inference error')
                fid = number(frame, 'frame_id')
                if previous_id is not None:
                    require(0 < ((fid - previous_id) & MASK) < 0x80000000, 'Duplicate/backwards frame id')
                stamp, received, start, end = [number(frame, key) for key in ('timestamp_ms', 'received_ms', 'start_ms', 'end_ms')]
                age(received, stamp);age(start, received);age(start, stamp)
                durations.append(age(end, start));ages.append(age(end, stamp))
                require(((received - previous_end) & MASK) < 0x80000000, 'Shared time went backwards')
                p, n = number(frame, 'person', signed=True), number(frame, 'no_person', signed=True)
                require(-128 <= p <= 127 and -128 <= n <= 127, 'Live INT8 output range')
                require(number(frame, 'person_u8') == p + 128, 'Live display score mismatch')
                raw_fnv, tensor_fnv = number(frame, 'raw_fnv', True), number(frame, 'tensor_fnv', True)
                if frame_dir is not None:
                    data = (Path(frame_dir) / f'frame_{fid}.gray').read_bytes()
                    require(len(data) == 9216 and fnv(data) == raw_fnv, 'Captured raw image identity differs')
                    require(fnv(bytes((v - 128) & 255 for v in data)) == tensor_fnv, 'Captured tensor identity differs')
                valid_frames.append(fid)
                previous_id, previous_end = fid, end
            require(len(valid_frames) >= min_frames, 'Insufficient complete live frames')
            result['live_input_bytes_verified'] = frame_dir is not None
        require(cursor == len(records), 'Unexpected trailing records')
        result.update(status='PASS', accepted_frames=len(valid_frames), frame_ids=valid_frames,
                      inference_ms=durations, frame_age_ms=ages)
    except (ValueError, KeyError, TypeError, IndexError, OSError) as exc:
        errors.append(str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--manifest', type=Path, default=ROOT/'firmware/c24_frame_person_detect/C24_INPUT_MANIFEST.json')
    parser.add_argument('--mode', choices=['selftest', 'live'], default='selftest')
    parser.add_argument('--min-frames', type=int, default=3)
    parser.add_argument('--reference', type=Path, help='Optional exact self-test INT8 comparison with PC compatibility-model report')
    parser.add_argument('--frame-dir', type=Path, help='Optional recorded frame_<id>.gray files for full live input identity checks')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
        reference = json.loads(args.reference.read_text(encoding='utf-8-sig')) if args.reference else None
        result = check(args.log.read_text(encoding='utf-8-sig', errors='replace'), manifest,
                       args.mode, args.min_frames, reference, args.frame_dir)
        result['log_sha256'] = hashlib.sha256(args.log.read_bytes()).hexdigest()
        result['manifest_sha256'] = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
        if args.reference:
            result['reference_sha256'] = hashlib.sha256(args.reference.read_bytes()).hexdigest()
    except (OSError, ValueError) as exc:
        result = {'status': 'FAIL', 'errors': [str(exc)], 'board_inference_passed': False}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
