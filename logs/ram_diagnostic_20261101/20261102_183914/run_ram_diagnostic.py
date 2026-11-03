"""Load a manifest-bound test into DDR, verify every byte, then run and capture.
No Flash programming operation exists in this runner.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,shutil,subprocess,time
from c9_probe_image import select as select_probe_image, VARIANTS
ROOT=Path(__file__).resolve().parents[1];EF=ROOT/'tools/efinity/2026.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--record',type=Path,required=True);ap.add_argument('--binary',type=Path,required=True)
 ap.add_argument('--prefix',required=True);ap.add_argument('--seconds',type=int,default=90);ap.add_argument('--port',default='COM13')
 ap.add_argument('--dump-camera-input',action='store_true',help='After DONE, halt and dump the last private GRAY8/tensor buffers locally')
 ap.add_argument('--preflight-only',action='store_true',help='Verify frozen firmware/image identities without opening USB or serial')
 group=ap.add_mutually_exclusive_group();group.add_argument('--configure-c9',action='store_true');group.add_argument('--configure-cold',action='store_true')
 group.add_argument('--configure-probe',choices=sorted(VARIANTS),help='Use exactly the audited USER2 experiment; ROM parking is replaced by the explicit application entry after full DDR readback')
 args=ap.parse_args()
 fw=args.binary.resolve();build=json.loads(args.record.read_text());entry=int(build['entry'],0)
 assert sha(fw)==build['artifacts'][fw.name]['sha256']
 for name,digest in build['source_sha256'].items():assert sha(ROOT/name)==digest,name
 probe_selection=select_probe_image(ROOT,args.configure_probe) if args.configure_probe else None
 if args.preflight_only:
  assert probe_selection is not None,'Offline variant preflight requires --configure-probe'
  image,audit_path=probe_selection
  print(json.dumps(dict(status='PASS_OFFLINE_PREFLIGHT',hardware_accessed=False,flash_written=False,board_test_passed=False,
      firmware_version=build.get('version'),firmware_sha256=sha(fw),entry=hex(entry),probe_variant=args.configure_probe,
      fpga_image_sha256=sha(image),implementation_audit_sha256=sha(audit_path)),indent=2))
  return 0
 import serial
 out=ROOT/'logs/ram_diagnostic_20261101'/datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
 shutil.copyfile(args.record,out/'firmware_build_record.json')
 record=dict(started=datetime.datetime.now().astimezone().isoformat(),status='RUNNING',flash_written=False,entry=hex(entry),firmware_sha256=sha(fw),firmware_version=build.get('version'),build_record_sha256=sha(args.record),runner_sha256=sha(Path(__file__)),prefix=args.prefix,board_test_passed=False,fpga_configured=False)
 def save():(out/'attempt.json').write_text(json.dumps(record,indent=2)+'\n')
 save();print('ATTEMPT_DIR='+str(out),flush=True)
 env=os.environ.copy();env.update(PYTHONHOME=str(EF/'python311'),PYTHONUTF8='1',EFX_HIFTDI_ENABLE='0',PROCESSOR_ARCHITECTURE='AMD64',EFINITY_USER_DIR_INI=(ROOT/'build/ddr_diag/efinity_user/user_dir.ini').as_posix(),EFINITY_USER_DIR=str(ROOT/'build/ddr_diag/efinity_user'))
 for k,p in [('EFINITY_HOME',EF),('EFXPGM_HOME',EF/'pgm'),('EFXDBG_HOME',EF/'debugger'),('EFXPT_HOME',EF/'pt'),('EFXIPM_HOME',EF/'ipm')]:env[k]=p.as_posix()
 base=(ROOT/'logs/c7_board_20261101/probe_20261101_123338/probe.cfg').read_text();head=base.split('\ninit\n')[0]+'\ninit\nhalt\nwait_halt 2000\n'
 commands={'load_readback':head+'echo [reg pc]\necho [reset halt]\nwait_halt 2000\necho [load_image {%s} 0x%x bin]\necho [dump_image {%s} 0x%x %d]\nshutdown\n'%(fw.as_posix(),entry,(out/'readback.bin').as_posix(),entry,fw.stat().st_size),
           'resume':head+'echo [reg pc 0x%x]\necho [reg pc]\necho [resume]\necho CPU_RESUMED\nshutdown\n'%entry}
 for name,text in commands.items():(out/(name+'.cfg')).write_text(text)
 port=serial.Serial(port=None,baudrate=115200,timeout=.1);port.dtr=False;port.rts=False;port.port=args.port
 raw=None;buffer=b'';done=False;failed=False;child=None
 def collect():
  nonlocal buffer,done,failed
  data=port.read(max(1,port.in_waiting))
  if data:
   raw.write(data);raw.flush();buffer+=data
   while b'\n' in buffer:
    line,buffer=buffer.split(b'\n',1);text=line.decode(errors='replace').strip('\r');print(text,flush=True)
    if text.startswith(args.prefix+'DONE'):done=True
    if re.match(r'^(?:C7|C9|C24|SPI)\|FAIL\b',text) or '|TRAP' in text or 'CRASH' in text:failed=True;done=True
 def phase(name,cmd,timeout):
  nonlocal child
  start=time.monotonic();notice=start;print('START '+name,flush=True)
  with (out/(name+'.log')).open('wb') as log:
   child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
   while child.poll() is None:
    collect()
    if time.monotonic()-start>timeout:raise TimeoutError(name)
    if time.monotonic()-notice>30:print('WAIT '+name,flush=True);notice=time.monotonic()
  if child.returncode:raise RuntimeError(name+' process failed')
  if name in commands:
   txt=(out/(name+'.log')).read_text(errors='replace')
   if name=='resume' and 'CPU_RESUMED' not in txt:raise RuntimeError('CPU resume not reached')
   if name=='load_readback' and 'dumped %d bytes'%fw.stat().st_size not in txt:raise RuntimeError('Readback command not completed')
 try:
  port.open();port.reset_input_buffer()
  with (out/'uart.log').open('wb') as raw:
   if probe_selection:
    image,audit_path=select_probe_image(ROOT,args.configure_probe)
    shutil.copyfile(audit_path,out/'implementation_audit.json');record['implementation_audit_sha256']=sha(out/'implementation_audit.json')
    record['probe_variant']=args.configure_probe;record['fpga_image_sha256']=sha(image);save()
    phase('configure_probe',[str(EF/'python311/bin/python.exe'),str(EF/'pgm/bin/efx_pgm/ftdi_program.py'),str(image),'-m','jtag','-u','ftdi://0x0403:0x6011:0:ff/1','--jtag_clock_freq','1000000'],180)
    record['fpga_configured']=True;save()
   elif args.configure_c9 or args.configure_cold:
    audit_name='soc_cold' if args.configure_cold else 'soc_live';proj='10_soc_cold' if args.configure_cold else '09_c7_live_acceptance'
    audit=json.loads((ROOT/'logs'/(audit_name+'_audit.json')).read_text());assert audit['status']==('PASS_OFFLINE_COLD_IMPLEMENTATION' if args.configure_cold else 'PASS_OFFLINE_LIVE_IMPLEMENTATION')
    if args.configure_c9:
     assert audit['c2_data_path_regression_audit']=='PASS_SAME_AS_QUALIFIED_C7_C2'
     assert sha(ROOT/'tools/audit_c9.py')==audit['c9_auditor_sha256']
    assert sha(ROOT/'tools/audit_soc_live.py')==audit['auditor_sha256']
    for name,digest in audit['evidence_sha256'].items():assert sha(ROOT/name)==digest,name
    for name,digest in audit['source_sha256'].items():assert sha(ROOT/name)==digest,name
    shutil.copyfile(ROOT/'logs'/(audit_name+'_audit.json'),out/'implementation_audit.json');record['implementation_audit_sha256']=sha(out/'implementation_audit.json')
    image=ROOT/'projects'/proj/'outflow/soc_physical.bit';record['fpga_image_sha256']=sha(image);save()
    phase('configure_c9',[str(EF/'python311/bin/python.exe'),str(EF/'pgm/bin/efx_pgm/ftdi_program.py'),str(image),'-m','jtag','-u','ftdi://0x0403:0x6011:0:ff/1','--jtag_clock_freq','1000000'],180)
    record['fpga_configured']=True;save()
   ocd=str(EF/'debugger/openocd/bin/openocd.exe')
   phase('load_readback',[ocd,'-f',str(out/'load_readback.cfg')],420)
   record['readback_sha256']=sha(out/'readback.bin');assert record['readback_sha256']==sha(fw),'Complete DDR readback mismatch';save()
   phase('resume',[ocd,'-f',str(out/'resume.cfg')],30)
   start=time.monotonic();notice=start
   while not done and time.monotonic()-start<args.seconds:
    collect()
    if time.monotonic()-notice>30:print('WAIT UART',flush=True);notice=time.monotonic()
   if done and not failed and args.dump_camera_input:
    text=(out/'uart.log').read_text(errors='replace')
    match=re.search(r'C9\|BUFFER gray=([\da-f]+) tensor=([\da-f]+) bytes=9216',text);assert match,'Private input pointers missing'
    pointers=[int(s,16) for s in match.groups()];assert all(0x1000<=p<=0x08000000-9216 for p in pointers),'Private input pointer outside CPU DDR'
    assert abs(pointers[0]-pointers[1])>=9216,'Overlapping private buffers'
    private=ROOT/'build/private_c9_camera_20261101'/out.name;private.mkdir(parents=True,exist_ok=False)
    cfg=head
    for name,address in zip(['gray','tensor'],pointers):cfg+='echo [dump_image {%s} 0x%x 9216]\n'%((private/(name+'.bin')).as_posix(),address)
    cfg+='shutdown\n';(out/'dump_private_input.cfg').write_text(cfg)
    phase('dump_private_input',[ocd,'-f',str(out/'dump_private_input.cfg')],60)
    record['private_inputs']={name:dict(path=str(private/(name+'.bin')),bytes=(private/(name+'.bin')).stat().st_size,sha256=sha(private/(name+'.bin'))) for name in ['gray','tensor']}
    assert all(v['bytes']==9216 for v in record['private_inputs'].values())
  record['status']='CAPTURED_DONE_REQUIRES_CHECKER' if done and not failed else 'FAIL_OR_INCOMPLETE'
 except Exception as exc:record['status']='HOST_ERROR';record['error']=repr(exc);print(repr(exc),flush=True)
 finally:
  if child and child.poll() is None:child.terminate();child.wait(timeout=10)
  port.close();record['finished']=datetime.datetime.now().astimezone().isoformat();save()
 print(json.dumps(record,indent=2),flush=True)
 return 0 if record['status']=='CAPTURED_DONE_REQUIRES_CHECKER' else 1
if __name__=='__main__':raise SystemExit(main())
