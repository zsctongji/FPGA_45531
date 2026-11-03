"""Verify standalone DDR RTL and implementation without touching hardware."""
from pathlib import Path
import argparse,csv,hashlib,json,re,shutil,subprocess,importlib.util
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/08_ddr_diag';OUT=P/'outflow'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def timing():
 text=(OUT/'ddr_diag.timing.rpt').read_text()
 sections=text.split('Setup (Max) Clock Relationship',1)[1].split('Hold (Min) Clock Relationship',1)
 result={}
 for kind,part in zip(['setup','hold'],sections):
  if kind=='hold':part=part.split('Clock Relationship Summary (end)',1)[0]
  rows=re.findall(r'^\s*(\S+)\s+(\S+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\([RF]-[RF]\)\s*$',part,re.M)
  if not rows or any(float(x[3])<0 for x in rows):raise ValueError('Missing/negative '+kind+' slack')
  result[kind]={'rows':len(rows),'minimum_slack_ns':min(float(x[3]) for x in rows)}
 return result
def simulate():
 build=ROOT/'build/ddr_diag';build.mkdir(parents=True,exist_ok=True);tests=[]
 files=[*sorted((P/'rtl').glob('*.sv')),*sorted((P/'sim').glob('*.sv'))]
 for top in ['tb_ddr_diag','tb_ddr_status']:
  exe=build/(top+'.vvp')
  c=subprocess.run([str(ROOT/'tools/iverilog/bin/iverilog.exe'),'-g2012','-Wall','-s',top,'-o',str(exe),*[str(p) for p in files]],capture_output=True,text=True,timeout=60)
  if c.returncode or re.search('warning|error',c.stdout+c.stderr,re.I):raise ValueError(c.stdout+c.stderr)
  v=subprocess.run([str(ROOT/'tools/iverilog/bin/vvp.exe'),str(exe)],capture_output=True,text=True,timeout=90)
  if v.returncode or 'PASS '+top+' ' not in v.stdout:raise ValueError(v.stdout+v.stderr)
  (ROOT/'logs'/(top+'.log')).write_text(v.stdout,encoding='utf-8');tests.append({'name':top,'status':'PASS','evidence':v.stdout.splitlines()})
 parser=ROOT/'tools/check_ddr_uart.py';spec=importlib.util.spec_from_file_location('ddr_uart',parser);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 sample='DDR|S=06 L=3 C=1 I=12 E=00 A=00000000 N=04000019 P=00000000\n'
 if module.validate(sample*2)['status']!='PASS_LOG':raise ValueError('UART acceptance positive case')
 bad=[sample,sample.replace('04000019','04000018')*2,sample.replace('C=1','C=0')*2,sample.replace('S=06','S=F1')+sample*2,sample.replace('E=00','E=05')+sample*2,sample*2+'DDR|S=',sample*2+sample.replace('S=06','S=03')]
 if any(module.validate(s)['status']!='FAIL_LOG' for s in bad):raise ValueError('UART acceptance rejection case')
 report={'status':'PASS_RTL_SIM','board_test_passed':False,'scope':'Reduced 32-word AXI memory model plus all 24 address-bit probes; no encrypted DDR electrical simulation','tests':tests,'uart_parser_cases':8,'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in [*files,parser,Path(__file__)]}}
 (ROOT/'logs/ddr_diag_tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return report
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--sim-only',action='store_true');ap.add_argument('--timing-only',action='store_true');args=ap.parse_args()
 if args.sim_only:simulate();print('PASS 12 AXI scenarios and 4 decoded UART status records.');return
 t=timing()
 if args.timing_only:print('PASS standalone DDR setup/hold:',t);return
 tests=read(ROOT/'logs/ddr_diag_tests.json')
 for name,digest in tests['source_sha256'].items():
  if sha(ROOT/name)!=digest:raise ValueError('Changed simulated input '+name)
 manifest=read(P/'DIAG_MANIFEST.json');build=read(ROOT/'logs/ddr_diag_build.json')
 if sha(ROOT/'tools/prepare_ddr_diag.py')!=manifest['generator_sha256']:raise ValueError('Changed project generator')
 if build['status']!='PASS':raise ValueError('Incomplete build')
 if [s['flow'] for s in build['steps']]!=['interface','map','pnr','pgm']:raise ValueError('Complete fresh four-stage build required')
 for step in build['steps']:
  if step['status']!='PASS':raise ValueError('Failed build stage')
 for name,digest in manifest['source_sha256'].items():
  if sha(ROOT/name)!=digest:raise ValueError('Changed implementation input '+name)
 source={x['path']:x['sha256'] for x in build['sources']}
 if source!=manifest['source_sha256']:raise ValueError('Compiled source mismatch')
 pgm=build['steps'][-1]
 for name,digest in pgm['inputs'].items():
  if sha(P/name)!=digest:raise ValueError('Changed project/physical constraint '+name)
 if sha(P/'work_pnr/ddr_diag.lbf')!=pgm['routed_lbf_sha256']:raise ValueError('Different routed image')
 for name,digest in pgm['artifacts'].items():
  if sha(OUT/name)!=digest:raise ValueError('Changed programming artifact')
 lines=[x for x in (OUT/'ddr_diag.pinout.csv').read_text(encoding='utf-8-sig').splitlines() if x and not x.startswith('#')]
 rows={re.sub(r'\.[PN]$','',r['Signal Name']):r for r in csv.DictReader(lines) if r['Signal Name']}
 for name,ball,voltage in [('i_arstn','C4','3.3 V'),('CLK_25M','J2','1.8 V'),('uart_tx','R14','3.3 V'),('led[0]','P13','3.3 V'),('led[1]','N13','3.3 V')]:
  if rows[name]['Pin Number']!=ball or rows[name]['I/O Bank Voltage']!=voltage:raise ValueError('Pin contract '+name)
 payload=(OUT/'ddr_diag.hex').read_text(encoding='ascii').splitlines()
 if not payload or any(not re.fullmatch('[0-9a-fA-F]{2}',l) for l in payload):raise ValueError('Unexpected configuration format')
 if len(payload)>0x380000:raise ValueError('Unexpectedly oversized diagnostic image')
 report={'status':'PASS_OFFLINE_DIAGNOSTIC','board_test_passed':False,'destructive_memory_test':True,'expected_capacity_bytes':268435456,'expected_success_checked_words':67108889,'timing':t,'configuration_stream_upper_bound_bytes':len(payload),'pin_contract':{n:rows[n] for n in ['i_arstn','CLK_25M','uart_tx','led[0]','led[1]']},'source_sha256':manifest['source_sha256'],'tool_sha256':sha(Path(__file__)),'artifacts':{n:{'bytes':(OUT/n).stat().st_size,'sha256':sha(OUT/n)} for n in ['ddr_diag.bit','ddr_diag.hex','ddr_diag.timing.rpt','ddr_diag.place.rpt','ddr_diag.pinout.csv']}}
 report.update(project_constraint_sha256=pgm['inputs'],test_report_sha256=sha(ROOT/'logs/ddr_diag_tests.json'),build_report_sha256=sha(ROOT/'logs/ddr_diag_build.json'))
 target=ROOT/'fpga_bitstreams/ddr_diag_100mhz';target.mkdir(parents=True,exist_ok=True)
 for n in report['artifacts']:shutil.copyfile(OUT/n,target/n)
 (target/'BUILD_RECORD.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 (ROOT/'logs/ddr_diag_check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print('PASS offline DDR diagnostic image. Hardware acceptance remains unverified.')
if __name__=='__main__':main()
