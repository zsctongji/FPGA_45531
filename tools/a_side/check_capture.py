"""Validate a CPU-dumped GRAY8 image against its mailbox metadata."""
import argparse
import json
from pathlib import Path


def check(raw, metadata):
    if len(raw)!=9216:raise ValueError('Expected 9216 GRAY8 bytes')
    if any(raw[:2016]) or any(raw[7200:]):raise ValueError('Letterbox padding is not black')
    if sum(raw)&0xffffffff != metadata['checksum']:raise ValueError('Mailbox SUM32 mismatch')
    for field in ('frame_id','timestamp_ms','checksum'):
        if not isinstance(metadata[field],int) or not 0<=metadata[field]<=0xffffffff:raise ValueError(field)
    if metadata.get('evidence') not in ('hardware','synthetic'):raise ValueError('Explicit evidence label required')
    return dict(status='PASS',bytes=len(raw),frame_id=metadata['frame_id'],timestamp_ms=metadata['timestamp_ms'],
                checksum=metadata['checksum'],evidence=metadata['evidence'],physical_proven=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('raw');p.add_argument('metadata');p.add_argument('--output',required=True)
    a=p.parse_args();raw=Path(a.raw).read_bytes();meta=json.loads(Path(a.metadata).read_text(encoding='utf-8-sig'))
    result=check(raw,meta)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.with_suffix('.pgm').write_bytes(b'P5\n# '+meta['evidence'].encode()+b'\n96 96\n255\n'+raw)
    out.with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
