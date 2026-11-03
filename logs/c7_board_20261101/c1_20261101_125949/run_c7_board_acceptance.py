"""Explicit JTAG SRAM/DDR-only C7 acceptance; complete host SHA256 readback gate.
Use Efinity's bundled Python (pyserial). No Flash operation is implemented.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,shutil,subprocess,sys,time
import serial
ROOT=Path(__file__).resolve().parents[1]
EF=ROOT/'tools/efinity/2026.1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--stage',choices=['cpu_diag','c1'],required=True)
 ap.add_argument('--configure',action='store_true',help='Temporarily configure C7 FPGA SRAM first')
 ap.add_argument('--port',default='COM13');ap.add_argument('--url',default='ftdi://0x0403:0x6011:0:ff/1')
 ap.add_argument('--configuration-attempt',type=Path,help='Prior successful C7 configuration record when omitting --configure')
 args=ap.parse_args()
 pgmcheck=json.loads((ROOT/'logs/soc_physical_pgm_check.json').read_text(encoding='utf-8-sig'))
 audit=json.loads((ROOT/'logs/soc_physical_audit.json').read_text(encoding='utf-8-sig'))
 assert pgmcheck['status']=='PASS' and audit['status']=='PASS_REFERENCE_AUDIT'
 xml_serialization_only=False
 for item in pgmcheck['sources']:
  path=ROOT/item['path']
  if sha(path)==item['sha256']:continue
  # Efinity pgm removes ElementTree's XML declaration. Require the exact
  # captured original SHA after restoring it with the platform line ending.
  if item['path']=='projects/07_soc_physical/soc_physical.xml':
   data=path.read_bytes()
   restored=[b"<?xml version='1.0' encoding='utf-8'?>"+newline+data for newline in [b'\r\n',b'\n']]
   assert any(hashlib.sha256(candidate).hexdigest()==item['sha256'] for candidate in restored),'Project XML changed beyond the verified tool serialization'
   xml_serialization_only=True
  else:raise AssertionError(item['path'])
 assert sha(ROOT/'projects/07_soc_physical/outflow/soc_physical.hex')==pgmcheck['step']['configuration_sha256']
 assert sha(ROOT/'projects/07_soc_physical/work_pnr/soc_physical.lbf')==pgmcheck['step']['routed_lbf_sha256']
 for name,digest in audit['evidence_sha256'].items():assert sha(ROOT/name)==digest,name
 image=ROOT/'projects/07_soc_physical/outflow/soc_physical.bit'
 # The pgm flow must have regenerated both containers from the audited routed LBF.
 assert image.stat().st_mtime>=datetime.datetime.fromisoformat(pgmcheck['step']['started']).timestamp()-2
 if args.stage=='cpu_diag':
  package=ROOT/'firmware/c7_board_diag';fw=package/'c7_board_diag.bin';entry=0x01000000
  manifest=json.loads((package/'BUILD_RECORD.json').read_text())
  assert sha(fw)==manifest['artifacts'][fw.name]['sha256']
  for name,digest in manifest['source_sha256'].items():assert sha(ROOT/name)==digest,name
  checker=ROOT/'tools/check_c7_board_uart.py';prefix='C7|';end='C7|DONE '
 else:
  package=ROOT/'firmware/c1_static_person_detect';fw=package/'tinyml_c1.bin';entry=0x1000
  manifest=json.loads((package/'C1_INPUT_MANIFEST.json').read_text())
  build=json.loads((ROOT/'logs/firmware_c1.json').read_text(encoding='utf-8-sig'))
  expected=next(a['sha256'].lower() for a in build['artifacts'] if Path(a['path']).name==fw.name)
  assert sha(fw)==expected
  checker=ROOT/'tools/check_c1_uart.py';prefix='C1|';end='C1|DONE '
 if not args.configure:
  assert args.configuration_attempt,'A successful same-image configuration attempt is required'
  prior=json.loads(args.configuration_attempt.read_text())
  assert prior.get('programmer_returncode')==0 and prior['fpga_image_sha256']==sha(image)
 stamp=datetime.datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')
 out=ROOT/'logs/c7_board_20261101'/(args.stage+'_'+stamp);out.mkdir(parents=True,exist_ok=False)
 meta=dict(started=datetime.datetime.now().astimezone().isoformat(),stage=args.stage,
           fpga_image_sha256=sha(image),firmware_sha256=sha(fw),firmware_bytes=fw.stat().st_size,
           firmware_version=manifest['version'],entry=hex(entry),flash_written=False,
           uart=args.port,baud=115200,dtr=False,rts=False,board_stage_passed=False,
           configured_this_attempt=args.configure,configuration_attempt=str(args.configuration_attempt) if args.configuration_attempt else None,
           whole_soc_validated=False,external_dma_coherence_validated=False,
           project_xml_only_declaration_and_line_endings_changed=xml_serialization_only)
 def save():(out/'attempt.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
 save();print('ATTEMPT_DIR='+str(out),flush=True)
 env=os.environ.copy();env.update(EFINITY_HOME=EF.as_posix(),EFXPGM_HOME=(EF/'pgm').as_posix(),EFXDBG_HOME=(EF/'debugger').as_posix(),EFXIPM_HOME=(EF/'ipm').as_posix(),EFXPT_HOME=(EF/'pt').as_posix(),
  PYTHONHOME=str(EF/'python311'),PYTHONUTF8='1',PYTHONUNBUFFERED='1',EFX_HIFTDI_ENABLE='0',PROCESSOR_ARCHITECTURE='AMD64',
  EFINITY_USER_DIR_INI=(ROOT/'build/ddr_diag/efinity_user/user_dir.ini').as_posix())
 python=str(EF/'python311/bin/python.exe');pgm=str(EF/'pgm/bin/efx_pgm/ftdi_program.py');ocd=str(EF/'debugger/openocd/bin/openocd.exe')
 head='''gdb_port disabled
tcl_port disabled
telnet_port disabled
adapter driver ftdi
ftdi vid_pid 0x0403 0x6011
ftdi channel 1
ftdi layout_init 0x08 0x0b
adapter speed 1000
transport select jtag
jtag newtap fpga_spinal bridge -expected-id 0x10660A79 -irlen 5 -ircapture 0x5 -irmask 0xF
target create fpga_spinal.cpu0 vexriscv -endian little -chain-position fpga_spinal.bridge -coreid 0 -dbgbase 0x10B80000 -work-area-phys 0xF9000000 -work-area-size 1024
vexriscv readWaitCycles 40
vexriscv cpuConfigFile {%s}
vexriscv jtagMapping 8 8 0 1 2 2
init
halt
'''%(ROOT/'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/cpu0.yaml').as_posix()
 cfg=head+'echo [reg pc]\necho [load_image {%s} 0x%x bin]\necho [dump_image {%s} 0x%x %d]\nshutdown\n'%(fw.as_posix(),entry,(out/'readback.bin').as_posix(),entry,fw.stat().st_size)
 (out/'load_readback.cfg').write_text(cfg,encoding='utf-8')
 (out/'resume.cfg').write_text(head+'resume 0x%x\necho CPU_RESUMED\nshutdown\n'%entry,encoding='utf-8')
 port=serial.Serial(port=None,baudrate=115200,timeout=.1,xonxoff=False,rtscts=False,dsrdtr=False)
 port.dtr=False;port.rts=False;port.port=args.port
 child=None;buffer=b'';done=False;raw=None
 def collect():
  nonlocal buffer,done
  data=port.read(max(1,port.in_waiting))
  if data:
   raw.write(data);raw.flush();buffer+=data
   while b'\n' in buffer:
    line,buffer=buffer.split(b'\n',1);text=line.decode('utf-8',errors='replace').strip('\r');print(text,flush=True)
    if end in text or prefix+'FAIL ' in text:done=True
 def phase(name,command,timeout):
  nonlocal child
  print('START '+name,flush=True);start=time.monotonic();notice=start
  with (out/(name+'.log')).open('wb') as log:
   child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
   while child.poll() is None:
    collect()
    if time.monotonic()-start>timeout:raise TimeoutError(name)
    if time.monotonic()-notice>=25:print('WAIT '+name+' elapsed_s=%d'%(time.monotonic()-start),flush=True);notice=time.monotonic()
  meta[name+'_returncode']=child.returncode;save()
  print((out/(name+'.log')).read_text(encoding='utf-8',errors='replace'),flush=True)
  if child.returncode:raise RuntimeError(name+' failed')
 try:
  port.open();port.reset_input_buffer()
  with (out/'uart.log').open('wb') as rawfile:
   raw=rawfile
   if args.configure:
    scan=subprocess.run([python,pgm,'--scan_usb'],cwd=ROOT,env=env,capture_output=True,timeout=45)
    (out/'jtag_scan.log').write_bytes(scan.stdout+scan.stderr)
    devices=json.loads(scan.stdout.decode().strip()) if scan.returncode==0 else []
    assert len(devices)==1 and devices[0]['idcode']==['0x10660a79'],'Wrong or missing JTAG target'
    phase('programmer',[python,pgm,str(image),'-m','jtag','-u',args.url,'--jtag_clock_freq','1000000'],120)
    # Allow PHY/core startup; the debugger then explicitly halts the boot ROM.
    until=time.monotonic()+2
    while time.monotonic()<until:collect()
   phase('load_readback',[ocd,'-f',str(out/'load_readback.cfg')],420)
   meta['readback_sha256']=sha(out/'readback.bin')
   assert meta['readback_sha256']==meta['firmware_sha256'],'Complete firmware readback differs; refusing to execute'
   print('HOST_SHA256_READBACK_PASS',flush=True);save()
   phase('resume',[ocd,'-f',str(out/'resume.cfg')],30)
   start=time.monotonic();notice=start
   while not done and time.monotonic()-start<300:
    collect()
    if time.monotonic()-notice>=25:print('WAIT firmware elapsed_s=%d'%(time.monotonic()-start),flush=True);notice=time.monotonic()
   meta['result']='UART_TERMINAL_CAPTURED' if done else 'UART_TIMEOUT'
 except Exception as exc:
  meta['result']='FAILED';meta['error']=repr(exc);print(repr(exc),flush=True)
 finally:
  if child and child.poll() is None:child.terminate();child.wait(timeout=10)
  port.close();meta['finished']=datetime.datetime.now().astimezone().isoformat();save()
 if (out/'uart.log').exists():
  r=subprocess.run([python,str(checker),str(out/'uart.log'),'--output',str(out/'uart_check.json')],cwd=ROOT,env=env,capture_output=True)
  (out/'checker.log').write_bytes(r.stdout+r.stderr)
  print(r.stdout.decode('utf-8',errors='replace'),flush=True)
  meta['checker_returncode']=r.returncode
  meta['board_stage_passed']=r.returncode==0 and meta.get('resume_returncode')==0 and meta.get('readback_sha256')==meta['firmware_sha256']
  meta['uart_sha256']=sha(out/'uart.log')
 # Retain exact loading recipe and all manifests with each attempt.
 for src in [Path(__file__),package/('BUILD_RECORD.json' if args.stage=='cpu_diag' else 'C1_INPUT_MANIFEST.json')]:shutil.copyfile(src,out/src.name)
 save();print(json.dumps(meta,indent=2),flush=True)
 return 0 if meta['board_stage_passed'] else 1
if __name__=='__main__':raise SystemExit(main())
