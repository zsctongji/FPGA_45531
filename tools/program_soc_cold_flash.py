"""Install only the audited, board-verified C10 image, preserving all Flash.
Fresh full backup must equal the previous verified C7 preservation image.
All unknown old Flash contents stay private under build/private_*.
"""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,time
ROOT=Path(__file__).resolve().parents[1];EF=ROOT/'tools/efinity/2026.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 audit=json.loads((ROOT/'logs/soc_cold_audit.json').read_text());assert audit['status']=='PASS_OFFLINE_COLD_IMPLEMENTATION'
 assert sha(ROOT/'tools/audit_soc_live.py')==audit['auditor_sha256']
 for field in ['source_sha256','evidence_sha256']:
  for name,digest in audit[field].items():assert sha(ROOT/name)==digest,name
 image=ROOT/'projects/10_soc_cold/outflow/soc_physical.bit';stream=image.with_suffix('.hex')
 warm=ROOT/'logs/c10_warm_boot_20261101/20261101_173651'
 result=json.loads((warm/'attempt.json').read_text());assert result['warm_automatic_boot_passed'] and result['fpga_image_sha256']==sha(image)
 assert sha(warm/'uart.log')==result['uart_sha256'] and json.loads((warm/'reference_check.json').read_text())['status']=='PASS'
 cpu=ROOT/'logs/ram_diagnostic_20261101/20261101_173856'
 check=json.loads((cpu/'uart_check.json').read_text());assert check['status']=='PASS_CPU_DDR_CACHE_LOG' and sha(cpu/'uart.log')==check['log_sha256']
 old=json.loads((ROOT/'logs/c7_cold_flash_program_20261101.json').read_text());expected_base=old['readback_sha256']
 bridge=EF/'pgm/fli/titanium/u10660A79.bit';assert sha(bridge)=='2fa6bda7ad79e03edc2f862c02e956823a90b4667b23229e2b2bc692bb63927e'
 out=ROOT/'build/private_c10_cold_program_20261101'/datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
 report=ROOT/'logs/c10_cold_flash_program_20261101.json'
 meta=dict(status='PREPARING',started=datetime.datetime.now().astimezone().isoformat(),private_evidence_dir=str(out),flash_write_attempted=False,flash_written=False,automatic_cold_boot_passed=False,
  fpga_image_sha256=sha(image),source_audit_sha256=sha(ROOT/'logs/soc_cold_audit.json'),warm_attempt_sha256=sha(warm/'attempt.json'),cpu_check_sha256=sha(cpu/'uart_check.json'),recovery_backup_sha256=old['recovery_backup_sha256'])
 def save():
  text=json.dumps(meta,indent=2)+'\n';report.write_text(text);(out/'attempt.json').write_text(text)
 save();print('PRIVATE_ATTEMPT_DIR='+str(out),flush=True)
 env=os.environ.copy();env.update(PYTHONHOME=str(EF/'python311'),PYTHONUTF8='1',EFX_HIFTDI_ENABLE='0',PROCESSOR_ARCHITECTURE='AMD64',EFINITY_USER_DIR_INI=(ROOT/'build/ddr_diag/efinity_user/user_dir.ini').as_posix())
 for k,p in [('EFINITY_HOME',EF),('EFXPGM_HOME',EF/'pgm'),('EFXDBG_HOME',EF/'debugger'),('EFXPT_HOME',EF/'pt'),('EFXIPM_HOME',EF/'ipm')]:env[k]=p.as_posix()
 base=[str(EF/'python311/bin/python.exe'),str(EF/'pgm/bin/efx_pgm/ftdi_program.py')];url='ftdi://0x0403:0x6011:0:ff/1'
 def phase(name,args,timeout):
  print('START '+name,flush=True);start=time.monotonic();notice=start
  with (out/(name+'.log')).open('wb') as log:
   child=subprocess.Popen(base+args,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
   try:
    while child.poll() is None:
     time.sleep(.2)
     if time.monotonic()-start>timeout:raise TimeoutError(name)
     if time.monotonic()-notice>30:print('WAIT '+name,flush=True);notice=time.monotonic()
   finally:
    if child.poll() is None:child.terminate();child.wait(timeout=10)
  meta[name+'_returncode']=child.returncode;save();assert child.returncode==0,name+' failed'
  return (out/(name+'.log')).read_text(errors='replace')
 def decode(path):return bytes(int(line,16) for line in path.read_text().splitlines())
 try:
  phase('load_official_bridge',[str(bridge),'-m','jtag','-u',url,'--jtag_clock_freq','1000000'],120)
  phase('fresh_backup',[str(stream),'-m','jtag_bridge','--jtag_bridge_mode','read','-u',url,'--address','0','--num_bytes','8388608','-o',str(out/'fresh_backup.hex'),'--jtag_clock_freq','1000000'],240)
  before=decode(out/'fresh_backup.hex');assert len(before)==8388608 and hashlib.sha256(before).hexdigest()==expected_base,'Fresh Flash backup differs from previous verified image'
  (out/'fresh_backup.bin').write_bytes(before);meta['fresh_backup_sha256']=expected_base
  firmware=ROOT/'firmware/c1_static_person_detect/tinyml_c1.bin';fw=firmware.read_bytes();assert before[0x380000:0x380000+len(fw)]==fw,'C1 Flash payload changed'
  payload=decode(stream);assert 0<len(payload)<0x380000
  merged=bytearray(before);merged[:len(payload)]=payload;assert merged[len(payload):]==before[len(payload):]
  merged=bytes(merged);image_hex=out/'c10_preserved.hex';(out/'c10_preserved.bin').write_bytes(merged);image_hex.write_text('\n'.join('%02x'%b for b in merged)+'\n')
  meta.update(expected_flash_sha256=hashlib.sha256(merged).hexdigest(),fpga_config_bytes=len(payload),firmware_sha256=sha(firmware),firmware_unchanged=True,all_bytes_outside_fpga_payload_preserved=True,status='PROGRAMMING',flash_write_attempted=True);save()
  text=phase('program',[str(image_hex),'-m','jtag_bridge','--jtag_bridge_mode','all','--verify_method','hostx1','-u',url,'--address','0','--jtag_clock_freq','1000000'],720)
  assert 'Flash verify successful' in text,'Missing host verify success';meta['flash_written']=True;meta['status']='INDEPENDENT_READBACK';save()
  phase('readback',[str(image_hex),'-m','jtag_bridge','--jtag_bridge_mode','read','-u',url,'--address','0','--num_bytes','8388608','-o',str(out/'readback.hex'),'--jtag_clock_freq','1000000'],240)
  data=decode(out/'readback.hex');assert len(data)==8388608;meta['readback_sha256']=hashlib.sha256(data).hexdigest();assert data==merged,'Independent full readback mismatch'
  (out/'readback.bin').write_bytes(data);meta['status']='PASS_FLASH_WRITE_AND_TWO_FULL_VERIFICATIONS_COLD_BOOT_PENDING'
 except Exception as exc:meta['status']='FAILED';meta['error']=repr(exc);print(repr(exc),flush=True)
 finally:meta['finished']=datetime.datetime.now().astimezone().isoformat();save()
 print(json.dumps(meta,indent=2),flush=True);return 0 if meta['status'].startswith('PASS') else 1
if __name__=='__main__':raise SystemExit(main())
