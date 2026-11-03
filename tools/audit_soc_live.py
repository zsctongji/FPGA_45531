"""Bind the isolated C9 implementation to sources, pins, route and actual STA.
This is an offline implementation gate, never a hardware acceptance claim.
"""
from pathlib import Path
import argparse,hashlib,json,re,xml.etree.ElementTree as E
from audit_soc_physical import timing_summary,bus_summary
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/09_c7_live_acceptance';OUT=P/'outflow'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def main():
 global P,OUT
 parser=argparse.ArgumentParser();parser.add_argument('--cold',action='store_true');args=parser.parse_args()
 prefix='soc_cold' if args.cold else 'soc_live'
 if args.cold:P=ROOT/'projects/10_soc_cold';OUT=P/'outflow'
 checks=[]
 def require(ok,label):
  if not ok:raise ValueError(label)
  checks.append(label)
 live=read(P/('COLD_MANIFEST.json' if args.cold else 'LIVE_MANIFEST.json'));physical=read(P/'PHYSICAL_MANIFEST.json')
 parent=read(ROOT/'fpga_bitstreams/soc_physical_100mhz/BUILD_RECORD.json')
 require(live['parent_image_sha256']==parent['artifacts']['soc_physical.bit']['sha256'],'Qualified parent image identity')
 require(live['parent_manifest_sha256']==parent['source_manifest_sha256'],'Qualified parent source manifest identity')
 generator='prepare_soc_cold.py' if args.cold else 'prepare_c7_live.py'
 require(sha(ROOT/'tools'/generator)==live['generator_sha256'],'Project generator identity')
 require(live['source_sha256']==physical['source_sha256'],'Physical and live source sets agree')
 for name,digest in live['source_sha256'].items():require(sha(ROOT/name)==digest,'Compiled source '+name)
 old=ROOT/'projects/07_soc_physical'
 for name in ['soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl','overrides/ddr3_parameter.vh']:
  require((P/name).read_bytes()==(old/name).read_bytes(),'Qualified pins/clocks/voltage/timing preserved '+name)
 # Generated clocks, ball assignments and bank voltages must match the qualified
 # implementation, not only the input constraint text.
 pinrows=lambda path:[line for line in path.read_text(encoding='utf-8-sig').splitlines() if line and not line.startswith('#')]
 require(pinrows(OUT/'soc_physical.pinout.csv')==pinrows(old/'outflow/soc_physical.pinout.csv'),'Generated board pinout identical to qualified C7')
 core=(P/'physical_soc_core.v').read_text();top=(P/'soc_physical_top.sv').read_text()
 if not args.cold:
  require(".c2_map_enable(1'b1)" in top and ".c3_io_enable(1'b0)" in top,'Static C2 map and disabled external sensor actuation')
  require('c3_apb_peripheral c3_peripheral(' not in core and live['c3_sensor_peripheral_present'] is False,'Dedicated diagnostic omits C3 sensor backend')
 require('c7_cpu_axi_address cpu_address_boundary(' in core,'Qualified CPU lane normalization retained')
 if not args.cold:
  require('c9_live_control' in core and 'c9_pattern_source test_source' in top,'C9 snapshot and isolated source controls instantiated')
  require('run_sync[3] &&' in top,'Source pixels gated by committed RUN')
 else:
  from c7_spi_rx_override import patch
  vendor=ROOT/'projects/03_tinyml/ip/sapphire_soc/sapphire_soc.v'
  require(sha(vendor)==live['vendor_source_sha256'],'Original vendor RTL identity')
  require(sha(ROOT/'tools/c7_spi_rx_override.py')==live['patcher_sha256'],'SPI patch generator identity')
  require((P/'overrides/sapphire_soc_spi.v').read_text()==patch(vendor.read_text()),'Private override changes only the seven SPI RX sample sources')
  require('c3_apb_peripheral c3_peripheral(' in core,'Full C7 sensor backend retained')
  for name in ['soc_physical_top.sv','physical_soc_core.v']:
   require((P/name).read_text()==(old/name).read_text().replace(old.as_posix(),P.as_posix()),'Full C7 behavior preserved '+name)
 tree=E.parse(P/'soc_physical.xml');design=[e.get('name') for e in tree.iter() if e.tag.endswith('}design_file')]
 for name in live['source_sha256']:
  if name.startswith('team_work/03_ai_soc/c9_live/rtl/'):
   require((ROOT/name).as_posix() in design,'C9 RTL included in project '+name)
 tests=read(ROOT/'logs'/('c7_spi_rx_tests.json' if args.cold else 'soc_live_rtl_tests.json'))
 if args.cold:require(tests['status']=='PASS' and len(tests['cases'])==6 and all(t['returncode']==0 for t in tests['cases']),'Actual SPI RTL raw negative and corrected positive cases at three dividers')
 else:require(tests['status']=='PASS' and len(tests['tests'])==2 and all(t['returncode']==0 for t in tests['tests']),'C9 APB/CDC and actual A capture regressions pass')
 for name,digest in tests['source_sha256'].items():require(sha(ROOT/name)==digest,'C9 regression source '+name)
 binding=read(ROOT/'logs'/(prefix+'_cdc_binding.json'))
 require(binding['status']=='PASS' and binding['pointer_bits']==66 and len(binding['buses'])==10,'All inherited Gray pointer endpoints bound')
 for path,key in [(OUT/'soc_physical.map.v','netlist_sha256'),(P/'soc_physical_cdc.sdc','constraint_sha256'),(P/'soc_physical_cdc_review.sdc','diagnostic_sdc_sha256'),(ROOT/'tools/generate_physical_cdc.py','generator_sha256'),(ROOT/'tools'/('generate_'+prefix+'_cdc.py'),'live_wrapper_sha256')]:
  require(sha(path)==binding[key],'CDC identity '+path.name)
 sdc=(P/'soc_physical.sdc').read_text()
 require((P/'soc_physical_cdc_review.sdc').read_text().splitlines()==[l for l in sdc.splitlines() if not l.startswith('set_clock_groups ')],'CDC review removes only asynchronous group cuts')
 build=read(ROOT/'logs'/(prefix+'_build.json'))
 require(build['status']=='PASS' and [s['flow'] for s in build['steps']]==['interface','map','pnr','sta_tclsh','pgm'],'Complete ordered live implementation flows')
 require(all(s['status']=='PASS' and s['exit_code']==0 for s in build['steps']),'Every implementation flow succeeded')
 built={s['path']:s['sha256'] for s in build['sources']}
 for name,digest in live['source_sha256'].items():require(built.get(name)==digest,'Routed source '+name)
 lbf=P/'work_pnr/soc_physical.lbf';sta=next(s for s in build['steps'] if s['flow']=='sta_tclsh');pgm=build['steps'][-1]
 require(sha(lbf)==sta['routed_lbf_sha256']==pgm['routed_lbf_sha256'],'Timing and configuration use the identical routed LBF')
 for step in [sta,pgm]:
  for name,digest in step['constraints'].items():require(sha(P/name)==digest,'Final constraint '+step['flow']+' '+name)
 require(sha(OUT/'soc_physical.hex')==pgm['configuration_sha256'],'Configuration stream bound to pgm flow')
 timing=timing_summary(OUT/'soc_physical.review_timing.rpt')
 require(all(not v['violations'] for v in timing.values()),'All constrained primary setup/hold relationships pass')
 bus={m:bus_summary(OUT/f'soc_physical.bus_{m}.rpt',binding) for m in ['setup','hold']}
 require(all(sum(b['bits'] for b in rows)==66 for rows in bus.values()),'Both corners cover every Gray pointer bit')
 place=(OUT/'soc_physical.place.rpt').read_text();resources={}
 for label in ['XLRs','Memory Blocks','DSP Blocks','Global Clocks (GBUF)']:
  match=re.search(re.escape(label)+r':\s*(\d+)\s*/\s*(\d+)',place);require(bool(match),'Packed report '+label)
  used,total=map(int,match.groups());require(used<=total,'Device capacity '+label);resources[label]=dict(used=used,total=total)
 evidence=[P/('COLD_MANIFEST.json' if args.cold else 'LIVE_MANIFEST.json'),P/'PHYSICAL_MANIFEST.json',P/'soc_physical.xml',P/'soc_physical.peri.xml',P/'soc_physical.sdc',P/'soc_physical_cdc.sdc',P/'soc_physical_cdc_review.sdc',P/'review_timing.tcl',lbf]
 evidence += [OUT/n for n in ['soc_physical.map.v','soc_physical.map.rpt','soc_physical.pinout.csv','soc_physical.place.rpt','soc_physical.route.rpt','soc_physical.review_timing.rpt','soc_physical.bus_setup.rpt','soc_physical.bus_hold.rpt','soc_physical.bit','soc_physical.hex']]
 evidence += [ROOT/'logs'/n for n in [prefix+'_build.json',prefix+'_cdc_binding.json','c7_spi_rx_tests.json' if args.cold else 'soc_live_rtl_tests.json']]
 result=dict(status='PASS_OFFLINE_COLD_IMPLEMENTATION' if args.cold else 'PASS_OFFLINE_LIVE_IMPLEMENTATION',checks=len(checks),packed_resources=resources,primary_sta=timing,cdc_skew=bus,
  board_test_passed=False,flash_written=False,source_sha256=live['source_sha256'],
  auditor_sha256=sha(Path(__file__)),evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in evidence})
 (ROOT/'logs'/(prefix+'_audit.json')).write_text(json.dumps(result,indent=2)+'\n')
 print('PASS '+prefix+' offline implementation audit: %d checks'%len(checks))
if __name__=='__main__':main()
