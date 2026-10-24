"""Analyse SOURCE capture logs, never HDMI refresh counters. Reject test evidence."""
import argparse
import csv
import json
from pathlib import Path


def analyse(rows, allow_synthetic=False):
    if len(rows) < 2:
        raise ValueError('At least two records required')
    for row in rows:
        if row['clock_source'] != 'camera_input' or row['evidence'] not in ('hardware', 'synthetic'):
            raise ValueError('Source/evidence must be explicit')
        if row['evidence'] != 'hardware' and not allow_synthetic:
            raise ValueError('Synthetic evidence rejected by default')
        if not 0 <= int(row['frame_id']) <= 0xffffffff or not 0 <= int(row['timestamp_ms']) <= 0xffffffff:
            raise ValueError('IDs/timestamps must be uint32')
        if int(row['width']) < 1 or int(row['height']) < 1 or int(row['complete']) not in (0, 1):
            raise ValueError('Invalid dimensions/completeness')
    elapsed, missing, backwards, incomplete, dimensions = 0, 0, 0, 0, set()
    for row in rows:
        dimensions.add((int(row['width']), int(row['height'])))
        incomplete += 1 - int(row['complete'])
    for a, b in zip(rows, rows[1:]):
        dt = (int(b['timestamp_ms']) - int(a['timestamp_ms'])) & 0xffffffff
        df = (int(b['frame_id']) - int(a['frame_id'])) & 0xffffffff
        if dt >= 0x80000000 or not 0 < df < 0x80000000:
            backwards += 1
        else:
            elapsed += dt
            missing += df - 1
    if backwards or elapsed == 0:
        raise ValueError('Duplicate/backward frame IDs or timestamp discontinuity/zero duration')
    hardware = all(r['evidence'] == 'hardware' for r in rows)
    fps = (len(rows) - 1) * 1000 / elapsed
    return dict(evidence='hardware_unverified' if hardware else 'synthetic',
                seconds=elapsed / 1000, observed_records=len(rows), observed_record_fps=fps,
                unobserved_frame_ids=missing, malformed_records=incomplete,
                dimensions=sorted(dimensions),
                continuous_720p30_candidate=hardware and missing == 0 and incomplete == 0
                and len(dimensions) == 1 and min(w for w, h in dimensions) >= 1280
                and min(h for w, h in dimensions) >= 720 and fps >= 30,
                note='Candidate only: verify source tap and complete capture logging; missing IDs may be telemetry loss, not camera loss.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv_file')
    p.add_argument('--output', required=True)
    p.add_argument('--allow-synthetic', action='store_true')
    args = p.parse_args()
    with open(args.csv_file, encoding='utf-8-sig', newline='') as f:
        result = analyse(list(csv.DictReader(f)), args.allow_synthetic)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
