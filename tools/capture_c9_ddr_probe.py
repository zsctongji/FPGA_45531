"""Configure the audited diagnostic in SRAM, read USER2, restore passing C10.

Run with the bundled SDK Python/PYTHONHOME. No Flash programming or EXTEST.
Native status banks are best-effort observations, never an atomic snapshot.
"""
from pathlib import Path
import datetime,hashlib,json,os,re,subprocess,sys,time
R=Path(__file__).resolve().parents[1];E=R/'tools/efinity/2026.1';P=R/'build/c9_ddr_probe_20261101'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def decode(banks):
 values={b:[r['value'] for r in banks[b]] for b in range(4)}
 a=values[0][-1];b=values[1][-1];d=values[3][-1]
 phases=[(v>>4)&15 for v in values[3]]
 return dict(cal_done=bool(a&1),system_reset=bool(a&2),controller_reset_released=bool(a&8),root_reset_released=bool(d&0x1000),
             pll_locks=(d>>8)&15,sys_rst=bool(a&4),init_state=(a>>4)&127,wrlvl_check=(a>>11)&255,read_level_check=(a>>19)&255,
             init_delay_counter=(b>>8)&0xfffff,rdlvl_shift=(b>>5)&7,wrlvl_shift=(b>>2)&7,mpr_rdlvl_dly=bool(b&2),idelay_ld=bool(b&1),
             ddr_debug_port_hex='%09x'%(((d&15)<<32)|values[2][-1]),
             status0_last8_identical=len(set(values[0][-8:]))==1,
             status1_last8_identical=len(set(values[1][-8:]))==1,
             clock_activity_observed={name:len({(v>>i)&1 for v in phases})==2 for i,name in enumerate(['core_clk','i_sysclk','tx_cal_clk','rx_cal_clk'])},
             atomic_snapshot=False,clock_frequency_verified=False)

def main():
 audit=json.loads((P/'implementation_audit.json').read_text());assert audit['status']=='PASS_OFFLINE_READONLY_DDR_PROBE'
 for key in ['source_sha256','evidence_sha256']:
  for n,d in audit[key].items():assert sha(R/n)==d,n
 env=os.environ.copy();env.update(PYTHONHOME=str(E/'python311'),PYTHONUTF8='1',EFX_HIFTDI_ENABLE='0',PROCESSOR_ARCHITECTURE='AMD64',EFINITY_USER_DIR_INI=(R/'build/ddr_diag/efinity_user/user_dir.ini').as_posix(),EFINITY_USER_DIR=str(R/'build/ddr_diag/efinity_user'))
 for k,p in [('EFINITY_HOME',E),('EFXPGM_HOME',E/'pgm'),('EFXDBG_HOME',E/'debugger'),('EFXSVF_HOME',E/'svf'),('EFXPT_HOME',E/'pt'),('EFXIPM_HOME',E/'ipm')]:env[k]=p.as_posix()
 os.environ.update(env);sys.path[:0]=[str(E/'pgm/bin'),str(E/'debugger/bin')]
 from efx_pgm.efx_hw_manager import EfxHwManager
 from efx_pgm.define import JtagParameters
 from pyftdi.bits import BitSequence
 class Console:
  def write(self,msg):print(msg,flush=True)
  write_error_msg=write;write_warning_msg=write
 out=R/'logs/c9_ddr_probe_20261101'/datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
 image=P/'outflow/soc_physical.bit'
 record=dict(status='RUNNING',started=datetime.datetime.now().astimezone().isoformat(),flash_written=False,cpu_firmware_loaded=False,
             fpga_image_sha256=sha(image),implementation_audit_sha256=sha(P/'implementation_audit.json'),capture_tool_sha256=sha(Path(__file__)))
 def save():(out/'attempt.json').write_text(json.dumps(record,indent=2)+'\n')
 def phase(name,args,timeout):
  print('START '+name,flush=True)
  with (out/(name+'.log')).open('wb') as f:q=subprocess.run(args,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  return q.returncode
 save();print('ATTEMPT_DIR='+str(out),flush=True)
 try:
  command=[str(E/'python311/bin/python.exe'),str(E/'pgm/bin/efx_pgm/ftdi_program.py'),str(image),'-m','jtag','-u','ftdi://0x0403:0x6011:0:ff/1','--jtag_clock_freq','1000000']
  assert phase('configure',command,180)==0,'SRAM configuration failed'
  record['fpga_configured']=True;save()
  bsdl=(P/'outflow/soc_physical-post.bsd').read_text();assert 'USER2          (01001)' in bsdl
  params=JtagParameters(frequency=1000000,url='ftdi://0x0403:0x6011:0:ff/1',target_num=1,devices=None,jtag_user='USER2',jtag_backend='pyftdi',plain_jtag=True)
  banks={b:[] for b in range(4)};rows=[];previous=None;start=time.monotonic()
  manager=EfxHwManager(Console())
  with manager._get_jtag_session(params) as session:
   with session.get_engine() as eng:
    while time.monotonic()-start<12 or min(map(len,banks.values()))<12:
     assert time.monotonic()-start<45,'Not enough valid USER2 samples'
     eng.reset();bits=repr(eng.read_dr_with_ir(length=36,instruction=BitSequence(value='01001',msb=True,length=5)))
     assert len(bits)==36 and set(bits)<={'0','1'},repr(bits)
     value=int(bits,2);bank=value>>32;payload=value&0xffffffff;record['last_raw_hex']='%09x'%value
     assert bank in banks,'Invalid bank tag: '+hex(value)
     if previous is not None:assert bank==(previous+1)%4,'USER2 bank discontinuity: '+hex(value)
     if bank==3:assert payload>>16==0xc9d2,'Missing C9D2 signature: '+hex(value)
     row=dict(time=datetime.datetime.now().astimezone().isoformat(),bank=bank,value=payload,raw_hex='%09x'%value)
     rows.append(row);banks[bank].append(row);previous=bank;time.sleep(.05)
    eng.reset()
  (out/'samples.json').write_text(json.dumps(rows,indent=2)+'\n')
  record['samples_sha256']=sha(out/'samples.json');record['observed']=decode(banks)
  record['status']='CAPTURED_READONLY_DDR_STATUS';print(json.dumps(record['observed'],indent=2),flush=True)
 except Exception as exc:
  record['status']='HOST_ERROR';record['error']=repr(exc);print(repr(exc),flush=True)
 finally:
  save()
  record['c10_restore_passed']=phase('restore_c10',[str(E/'python311/bin/python.exe'),str(R/'tools/capture_soc_cold_warm.py')],270)==0
  text=(out/'restore_c10.log').read_text(errors='replace');match=re.search(r'ATTEMPT_DIR=(.+)',text)
  if match:record['restore_attempt']=str(Path(match[1].strip()).relative_to(R)/'attempt.json')
  record['finished']=datetime.datetime.now().astimezone().isoformat();save()
 print(json.dumps(record,indent=2),flush=True)
 return 0 if record['status']=='CAPTURED_READONLY_DDR_STATUS' and record['c10_restore_passed'] else 1

if __name__=='__main__':raise SystemExit(main())
