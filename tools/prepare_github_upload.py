"""Prepare auditable source-only snapshot; never modify the working projects."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'build/github_publish/source_snapshot'
SKIP_DIRS={'outflow','build','build_ours','__pycache__','.git','.svn','.metadata','node_modules','Debug','Release','.cache','handoff'}
SKIP_EXT={'.exe','.dll','.so','.o','.a','.elf','.obj','.pdb','.pyc','.zip','.7z','.rar','.gz','.tar','.mp4','.avi','.gif','.pdf','.vdb','.log','.rpt','.asm','.bak','.lic','.key','.pem','.p12','.pfx'}
SECRET=[re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(rb'github_pat_[A-Za-z0-9_]{40,}'),re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}')]
BASES=['rtl','sim','tools','projects','firmware','docs','team_work']

def candidates():
    for base in BASES:
        for p in sorted((ROOT/base).rglob('*')):
            if not p.is_file():continue
            rel=p.relative_to(ROOT)
            if any(x in SKIP_DIRS or x.startswith('work_') for x in rel.parts):continue
            if base=='tools' and len(rel.parts)>2 and rel.parts[1]!='a_side':continue
            if p.suffix.lower() in SKIP_EXT:continue
            if p.name.lower() in {'.env','user_dir.ini','workspace.xml'} or p.name.endswith('.user'):continue
            # Generated CPU application exports are not source. ROMs inside projects stay.
            if base=='firmware' and p.suffix.lower() in {'.hex','.bin'}:continue
            yield p
    for p in ROOT.glob('*.cmd'):yield p
    for name in ['README.md','00_开始这里.txt','config/hardware.json','references/SOURCES.md','references/a1_protocol_vectors.json']:
        p=ROOT/name
        if p.is_file():yield p
    for name in ['selftest.json','selftest_events.json','a_side_selftest.json','a_side_synthesis.json','a_side_firmware.json','verified_artifacts.json']:
        p=ROOT/'logs'/name
        if p.is_file():yield p

def prepare():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    files=[];totals=Counter();findings=[]
    for source in candidates():
        rel=source.relative_to(ROOT)
        data=source.read_bytes()
        if len(data)>95_000_000:raise ValueError(f'File exceeds repository source limit: {rel}')
        for pattern in SECRET:
            if pattern.search(data):findings.append(str(rel))
        dest=OUTPUT/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dest)
        sha=hashlib.sha256(data).hexdigest()
        assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
        files.append(dict(path=rel.as_posix(),bytes=len(data),sha256=sha))
        totals[rel.parts[0]]+=len(data)
    if findings:raise RuntimeError('Credential-like content found (values withheld): '+', '.join(findings))
    report=dict(status='PREPARED_NOT_UPLOADED',repository='https://github.com/zsctongji/FPGA_cooperation',
                source_root=str(ROOT),snapshot=str(OUTPUT),files=len(files),bytes=sum(x['bytes'] for x in files),
                by_folder_bytes=dict(totals),credential_pattern_findings=findings,
                excludes=['Installed development tools and local settings','Vendor download archives and source-only handoff zip','Reproducible build intermediates','Credentials/license keys','Generated application binaries; project ROM initialisation retained'],
                manifest=files)
    (ROOT/'logs/github_upload_preparation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUTPUT/'SOURCE_MANIFEST_SHA256.txt').write_text(''.join(f"{f['sha256']}  {f['path']}\n" for f in files),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='manifest'},ensure_ascii=False,indent=2))

if __name__=='__main__':prepare()
