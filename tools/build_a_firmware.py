"""Compile the portable adapter for the actual RISC-V ABI; no board execution."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

root=Path(__file__).resolve().parents[1]
record=dict(status='RUNNING',scope='cross_compile_only',hardware_executed=False,started=datetime.datetime.now(datetime.timezone.utc).isoformat())
out=root/'firmware/a_side/a_side.o'
status=root/'logs/a_side_firmware.json'
gcc=root/'tools/riscv_gcc/13.4.0/bin/riscv-none-elf-gcc.exe'
cmd=[str(gcc),'-march=rv32im_zicsr_zifencei','-mabi=ilp32','-Os','-std=c11','-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections','-c',str(out.with_suffix('.c')),'-o',str(out)]
record['command']=cmd
record['sources']={name:hashlib.sha256((root/'firmware/a_side'/name).read_bytes()).hexdigest() for name in ['a_side.c','a_side.h']}
try:
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=90)
    (root/'logs/a_side_firmware.log').write_text(p.stdout,encoding='utf-8')
    if p.returncode or not out.is_file():raise RuntimeError(p.stdout)
    record.update(status='PASS',object=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest())
except Exception as e:record.update(status='FAIL',error=str(e));raise
finally:
    record['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    status.write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
