"""Compare/apply prepared sources in a clean checkout of the named repository."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

root=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],text=True,encoding='utf-8',errors='replace').strip()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('checkout');p.add_argument('--apply',action='store_true')
args=p.parse_args();repo=Path(args.checkout).resolve()
origin=git(repo,'remote','get-url','origin')
if origin.removesuffix('.git').rstrip('/')!='https://github.com/zsctongji/FPGA_cooperation':raise ValueError('Unexpected destination repository')
if git(repo,'status','--porcelain'):raise ValueError('Checkout has uncommitted changes; refusing overwrite')
record=json.loads((root/'logs/github_upload_preparation.json').read_text(encoding='utf-8'))
snapshot=Path(record['snapshot'])
added=[];changed=[];same=[]
for item in record['manifest']:
    relative=Path(item['path']);source=snapshot/relative;dest=repo/relative
    if not dest.resolve().is_relative_to(repo):raise ValueError('Path escapes checkout')
    if sha(source)!=item['sha256']:raise ValueError('Snapshot source changed: '+str(relative))
    (added if not dest.exists() else same if sha(dest)==item['sha256'] else changed).append(item['path'])
summary=dict(destination=origin,branch=git(repo,'branch','--show-current'),base_commit=git(repo,'rev-parse','HEAD'),
             added=added,changed=changed,unchanged=len(same),applied=args.apply)
(root/'logs/github_source_comparison.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(added=len(added),changed=len(changed),unchanged=len(same),applied=args.apply),indent=2))
print('CHANGED_EXISTING_FILES',json.dumps(changed[:80],ensure_ascii=False))
if args.apply:
    for name in added+changed:
        dest=repo/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(snapshot/name,dest)
    shutil.copy2(snapshot/'SOURCE_MANIFEST_SHA256.txt',repo/'SOURCE_MANIFEST_SHA256.txt')
    guard=root/'build/github_publish/upload_gitignore.txt'
    existing=repo/'.gitignore'
    content=existing.read_text(encoding='utf-8') if existing.exists() else ''
    addition=guard.read_text(encoding='utf-8')
    if addition not in content:existing.write_text(content.rstrip()+'\n\n'+addition,encoding='utf-8')
    print('Prepared source files copied; no commit or network operation performed by this helper.')
