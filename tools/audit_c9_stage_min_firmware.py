"""Verify frozen RV32 diagnostic contains no custom-accelerator opcodes."""
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=R/'firmware/c9_camera_geometry/c9_geometry.elf';data=p.read_bytes();h=struct.unpack_from('<16sHHIIIIIHHHHHH',data)
 assert h[0][:6]==b'\x7fELF\x01\x01' and h[2]==243
 sections=[];count=0;cache=0;custom=[]
 for i in range(h[12]):
  s=struct.unpack_from('<IIIIIIIIII',data,h[6]+i*h[11])
  if s[1]!=1 or not(s[2]&4):continue
  code=data[s[4]:s[4]+s[5]];assert len(code)%4==0
  for offset in range(0,len(code),4):
   word=struct.unpack_from('<I',code,offset)[0];assert word&3==3,'Unexpected compressed/data encoding'
   count+=1;cache+=word==0x500f
   if word&127 in [0x0b,0x2b,0x5b,0x7b]:custom.append(hex(s[3]+offset))
  sections.append(dict(address=hex(s[3]),bytes=len(code)))
 assert count>0 and not custom
 record=dict(status='PASS_NO_CUSTOM_ACCELERATOR_OPCODE_IN_EXECUTABLE_SECTIONS',instruction_count=count,cache_invalidate_opcode_0000500f_count=cache,custom_opcode_addresses=custom,sections=sections,scope='Executable RV32 sections only. Board MAP/readback/CPU execution still required.',source_sha256={x.relative_to(R).as_posix():sha(x) for x in [p,p.parent/'c9_geometry.bin',Path(__file__)]})
 (R/'logs/c9_stage_min_firmware_audit_20261103.json').write_text(json.dumps(record,indent=2)+'\n',newline='\n')
 print(json.dumps(record,indent=2))
if __name__=='__main__':main()
