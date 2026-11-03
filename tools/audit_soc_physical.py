"""Cross-check the V4 reference constraints against Efinity's actual outputs.
Does not access the board. Physical device/PCB/electrical verification is never
inferred from successful offline implementation or synthetic functional tests.
"""
from pathlib import Path
import argparse,csv,hashlib,json,re
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/07_soc_physical'
OUT=P/'outflow'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def local(t):return t.split('}')[-1]

def timing_summary(path):
    text=path.read_text(encoding='utf-8',errors='replace')
    part=text.split('Setup (Max) Clock Relationship',1)[1]
    setup,hold=part.split('Hold (Min) Clock Relationship',1)
    hold=hold.split('Clock Relationship Summary (end)',1)[0]
    pattern=r'^\s*(\S+)\s+(\S+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\([RF]-[RF]\)\s*$'
    result={}
    for name,section in [('setup',setup),('hold',hold)]:
        rows=re.findall(pattern,section,re.M)
        if len(rows)<29:raise ValueError('Incomplete '+name+' timing table')
        values=[float(r[3]) for r in rows]
        result[name]={'rows':len(rows),'minimum_slack_ns':min(values),'violations':[r for r in rows if float(r[3])<0]}
    return result

def bus_summary(path,binding):
    text=path.read_text(encoding='utf-8',errors='replace')
    blocks=re.split(r'^Requirement: (?=\d)',text,flags=re.M)[1:]
    if len(blocks)!=10 or 'No bus skew paths found' in text:raise ValueError('Empty/missing CDC skew paths')
    result=[]
    for block,bus in zip(blocks,binding['buses']):
        requirement=float(re.match(r'([\d.]+) ns',block)[1])
        if abs(requirement-bus['skew_limit_ns'])>0.001:raise ValueError('Wrong CDC skew requirement')
        destinations=set(re.findall(r'(\S+~FF\|D)',block))
        if destinations!={s+'|D' for s in bus['destinations']}:raise ValueError('Missing CDC endpoint bit')
        rows=re.findall(r'\|\s+(?:Slow|Fast)\s+\|\s+([\d.]+)\s+\|\s+(-?[\d.]+)',block)
        if not rows or any(float(slack)<0 for _,slack in rows):raise ValueError('CDC skew violation/incomplete paths')
        result.append({'hierarchy':bus['hierarchy'],'pointer':bus['pointer'],'bits':bus['bits'],
          'requirement_ns':requirement,'maximum_skew_ns':max(float(a) for a,_ in rows),
          'minimum_slack_ns':min(float(b) for _,b in rows)})
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--require-ready',action='store_true');args=ap.parse_args()
    checks=[]
    def require(v,msg):
        if not v:raise ValueError(msg)
        checks.append(msg)
    manifest=read(P/'PHYSICAL_MANIFEST.json');tree=E.parse(P/'soc_physical.peri.xml')
    pins={e.get('name'):e for e in tree.iter() if local(e.tag)=='comp_gpio'}
    owners={}
    for name,e in pins.items():
        require(e.get('gpio_def') not in owners,'Unique pad '+e.get('gpio_def'));owners[e.get('gpio_def')]=name
    expected={
      'i_arstn':('GPIOL_07','C4','Input','3.3 V'),
      'integration_arm_n':('GPIOL_03','A3','Input','3.3 V'),
      'c3_scl':('GPIOL_04','B3','Inout','3.3 V'),
      'c3_sda':('GPIOL_06','C3','Inout','3.3 V'),
      'buzzer_sig':('GPIOL_10','B5','Output','3.3 V'),
      'led[0]':('GPIOR_27','P13','Output','3.3 V'),
      'led[1]':('GPIOR_24','N13','Output','3.3 V'),
      'CLK_25M':('GPIOL_P_08','J2','Input','1.8 V'),
      'CLK_27M':('GPIOL_P_10','H2','Input','1.8 V'),
      'uart_tx':('GPIOR_28','R14','Output','3.3 V'),
      'uart_rx':('GPIOL_02','R4','Input','3.3 V'),
      'flash_sclk':('GPIOL_N_01','N1','Output','1.8 V'),
      'flash_ss':('GPIOL_P_01','P1','Output','1.8 V'),
      'flash_d0':('GPIOL_P_03','M1','Inout','1.8 V'),
      'flash_d1':('GPIOL_N_03','L1','Inout','1.8 V'),
      'flash_d2':('GPIOL_P_04','H5','Inout','1.8 V'),
      'flash_d3':('GPIOL_N_04','H4','Inout','1.8 V')}
    csv_lines=[l for l in (OUT/'soc_physical.pinout.csv').read_text(encoding='utf-8-sig').splitlines() if l and not l.startswith('#')]
    actual={re.sub(r'\.[PN]$','',r['Signal Name']):r for r in csv.DictReader(csv_lines) if r['Signal Name']}
    for name,(pad,ball,direction,voltage) in expected.items():
        require(name in pins and pins[name].get('gpio_def')==pad,'Declared role '+name)
        require(name in actual,'Generated pinout role '+name)
        row=actual[name]
        wanted_direction='Bidirectional' if direction=='Inout' else direction
        require(row['Pin Number']==ball and row['Direction'].lower()==wanted_direction.lower() and row['I/O Bank Voltage']==voltage,'Efinity ball/direction/voltage '+name)
    require('LCD_POWER' not in pins and 'LCD_RST_P' not in pins,'Legacy LCD owners removed')
    top=(P/'soc_physical_top.sv').read_text(encoding='utf-8-sig')
    core=(P/'physical_soc_core.v').read_text(encoding='utf-8-sig')
    require('c7_cpu_axi_address cpu_address_boundary(' in core and
            '.s_awaddr(c7_cpu_awaddr_aligned)' in core and
            '.s_araddr(c7_cpu_araddr_aligned)' in core,'CPU vendor single-beat addresses pass through the C7 normalization boundary')
    lanes=read(ROOT/'logs/c7_cpu_lanes_tests.json')
    require(lanes['status']=='PASS' and len(lanes['cases'])==2 and
            all(c['expected_result_met'] for c in lanes['cases']),
            'Actual vendor BMB upsizer shifted-lane regression and raw negative case pass')
    for name,digest in lanes['source_sha256'].items():require(sha(ROOT/name)==digest,'CPU lane regression input '+name)
    ddr_header=P/'overrides/ddr3_parameter.vh'
    require(manifest['ddr_profile']['tFAW_override_ps']==50000 and re.search(r'`define\s+tFAW\s+50000\b',ddr_header.read_text()),'Actual x16 DDR profile uses conservative 50ns tFAW')
    original=ROOT/'projects/03_tinyml/src/ddr3_controller/ddr3_top.v'
    expected_payload=original.read_bytes().replace(b'`include "ddr3_parameter.vh"',('`include "'+ddr_header.as_posix()+'"').encode(),1)
    require((P/'overrides/ddr3_top.v').read_bytes()==expected_payload,'Vendor DDR payload unchanged except private header include')
    require(ddr_header.as_posix() in core,'C7 core selects the private DDR header')
    for bus in ['c3_scl','c3_sda']:
        require("assign "+bus+"_OUT=1'b0" in top,'Open-drain constant zero '+bus)
        oe=next(e for e in pins[bus] if local(e.tag)=='output_enable_config')
        require(oe.get('name')==bus+'_OE' and not oe.get('name_oen'),'Active-high OE '+bus)
    banks={e.get('name'):e.get('iostd') for e in tree.iter() if local(e.tag)=='iobank'}
    for bank,voltage in manifest['bank_voltage_V'].items():require(banks[bank].startswith(str(voltage)+' V'),'Bank reference voltage '+bank)
    plls={e.get('pll_def'):e for e in tree.iter() if local(e.tag)=='pll'}
    require(set(plls)==set(manifest['pll_owners']),'Four exclusive PLL owners')
    require(plls['PLL_TR0'].get('name')=='DDR3_PLL' and plls['PLL_TL0'].get('name')=='CPU_PLL','DDR and CPU PLL assignment')
    require(not any(local(e.tag)=='mipi_dphy' and e.get('ops_type')=='tx' for e in tree.iter()),'Unused DSI TX resources removed')
    clocks={}
    pt_sdc=(OUT/'soc_physical.pt.sdc').read_text(encoding='utf-8-sig')
    for period,name in re.findall(r'create_clock[^\n]*?-period\s+([\d.]+)[^\n]*?-name\s+(\S+)',pt_sdc):clocks[name]=float(period)
    for name,mhz in manifest['clock_MHz'].items():require(name in clocks and abs(clocks[name]-1000/mhz)<0.001,'PLL-generated clock '+name)
    sdc=(P/'soc_physical.sdc').read_text(encoding='utf-8-sig')
    require('jtag_inst1_TCK [get_ports' in sdc and '-name jtag_inst1_TCK' in sdc,'Explicit JTAG clock ceiling')
    require('set_multicycle_path' not in sdc and not re.search(r'set_false_path\s+-from\s+\[all_',sdc),'No blanket data-path timing exemption')
    fragment=P/'soc_physical_cdc.sdc';binding=read(ROOT/'logs/soc_physical_cdc_binding.json')
    require('source soc_physical_cdc.sdc' in sdc and len(re.findall(r'^set_bus_skew ',fragment.read_text(),re.M))==10,'Ten mapped Gray-pointer bus skew checks declared')
    require(binding['status']=='PASS' and binding['pointer_bits']==66 and sha(fragment)==binding['constraint_sha256'],'All 66 Gray pointer bits including merged MSBs bound')
    require(sha(OUT/'soc_physical.map.v')==binding['netlist_sha256'] and sha(ROOT/'tools/generate_physical_cdc.py')==binding['generator_sha256'],'CDC constraint generator and actual netlist identity')
    diagnostic=P/'soc_physical_cdc_review.sdc'
    require(sha(diagnostic)==binding['diagnostic_sdc_sha256'],'Independent CDC diagnostic SDC identity')
    require(diagnostic.read_text().splitlines()==[l for l in sdc.splitlines() if not l.startswith('set_clock_groups ')],'CDC view only removes asynchronous group cuts')
    for name,digest in manifest['source_sha256'].items():require(sha(ROOT/name)==digest,'Current compiled source '+name)
    require(sha(ROOT/'tools/prepare_soc_physical.py')==manifest['generator_sha256'],'Physical generator identity')
    tests=read(ROOT/'logs/soc_physical_tests.json')
    require(tests['status']=='PASS' and tests['full_hd'] and len(tests['tests'])==3,'Pixel adapters and actual A ISP small/full-HD checks')
    for name,digest in tests['source_sha256'].items():require(sha(ROOT/name)==digest,'Pixel/ISP test identity '+name)
    c2=read(ROOT/'logs/physical_c2_selftest.json')
    require(c2['status']=='PASS' and c2['passed']==53 and c2['physical_overrides'],'53 C2 cases on actual physical BRAM overrides')
    require(len(c2['tail_checks'])==2 and all(t['status']=='PASS' for t in c2['tail_checks']),'One/six-beat read-first collision checks')
    for name,digest in c2['source_sha256'].items():require(sha(ROOT/name)==digest,'Physical C2 simulation input '+name)
    for row in c2['source_clone_provenance'].values():require(sha(ROOT/row['compiled_from'])==row['compiled_sha256'],'Cloned original/override input '+row['compiled_from'])
    require(sha(ROOT/'tools/test_physical_c2.py')==c2['wrapper_sha256'],'Physical C2 runner identity')
    net=(OUT/'soc_physical.map.v').read_text(encoding='utf-8',errors='replace')
    memories=re.findall(r'\bEFX_RAM10\s+\\(\S+)\s*\(',net)
    for prefix in ['soc/c2_attachment/core/pixels/storage/memory','soc/c2_attachment/core/hub/writer/buffer','soc/c2_full_video/framebuffer/wbuf','soc/c2_full_video/framebuffer/rbuf']:
        require(any(n.startswith(prefix+'__') for n in memories),'Actual BRAM instance '+prefix)
    rpt=(OUT/'soc_physical.map.rpt').read_text(encoding='utf-8',errors='replace')
    resources={k:int(re.findall(k+r'\s*:\s*(\d+)',rpt)[-1]) for k in ['EFX_LUT4','EFX_FF','EFX_RAM10','EFX_DSP48','EFX_ADD']}
    timing=OUT/'soc_physical.timing.rpt'
    routed=P/'work_pnr/soc_physical.lbf'
    implementation_complete=timing.is_file() and routed.is_file() and (OUT/'soc_physical.route.rpt').is_file()
    require(implementation_complete,'Actual routed LBF, route and timing reports present')
    route=read(ROOT/'logs/soc_physical_route_build.json')
    require(route['status']=='PASS' and any(s['flow']=='pnr' and s['status']=='PASS' for s in route['steps']),'Completed whole-SoC P&R')
    route_sources={s['path']:s['sha256'] for s in route['sources']}
    for name,digest in manifest['source_sha256'].items():require(route_sources.get(name)==digest,'Routed compiled HDL '+name)
    review=read(ROOT/'logs/soc_physical_sta_tclsh_check.json')
    require(review['status']=='PASS' and review['step']['flow']=='sta_tclsh','Completed post-route STA and skew review')
    require(sha(routed)==review['step']['routed_lbf_sha256'],'STA bound to the current routed design')
    for name,digest in review['step']['constraints'].items():require(sha(P/name)==digest,'STA input constraint '+name)
    # A fresh full build needs no reuse proof. This run refined Gray endpoints
    # after routing; bind that refinement to the unchanged routed design.
    route_sdc=route_sources.get('projects/07_soc_physical/soc_physical.sdc')
    if route_sdc!=sha(P/'soc_physical.sdc'):
        post=read(ROOT/'logs/soc_physical_postroute_review_inputs.json')
        require(post['status']=='PASS_SAME_PRIMARY_TIMING' and post['prior_sdc_sha256']==route_sdc and post['current_sdc_sha256']==sha(P/'soc_physical.sdc'),'Post-route endpoint refinement preserves primary timing')
        require(sha(routed)==post['routed_lbf_sha256'],'STA examines the exact routed LBF')
    sta=timing_summary(OUT/'soc_physical.review_timing.rpt')
    require(not sta['setup']['violations'] and not sta['hold']['violations'],'All primary setup/hold clock relationships nonnegative')
    bus={mode:bus_summary(OUT/f'soc_physical.bus_{mode}.rpt',binding) for mode in ['setup','hold']}
    require(all(sum(b['bits'] for b in rows)==66 for rows in bus.values()),'Actual skew reports cover 10 buses and all 66 bits at both corners')
    place=(OUT/'soc_physical.place.rpt').read_text()
    packed={}
    for label in ['XLRs','Memory Blocks','DSP Blocks','Global Clocks (GBUF)']:
        match=re.search(re.escape(label)+r':\s*(\d+)\s*/\s*(\d+)',place)
        require(bool(match),'Packed resource '+label)
        used,total=map(int,match.groups());require(used<=total,'Device packing capacity '+label)
        packed[label]={'used':used,'total':total,'percent':round(100*used/total,2)}
    identity_path=ROOT/'logs/hardware_identity_20261031.json'
    voltage=read(identity_path).get('voltage_observation',{'status':'NOT_REPORTED'}) if identity_path.is_file() else {'status':'NOT_REPORTED'}
    open_items=['Actual PCB/pin mapping, pull-ups and connector orientation need confirmation; DC rails are user-reported within expectation, with exact readings absent.' if voltage.get('status')=='PASS_USER_REPORTED' else 'Actual PCB revision, jumpers, rail/pull-up measurements and connector orientation unverified.',
                'Inherited V4 DDR clock/HDMI adjacent-HSIO coupling warning requires physical stress verification.',
                'External Flash SPI timing/model, camera/HDMI electrical timing and real DDR calibration are not hardware-verified.',
                'No live CPU/AI execution, real sensor GPIO actuation, or board bandwidth/CDC experiment was performed.']
    evidence=[P/'soc_physical.peri.xml',P/'soc_physical.sdc',P/'PHYSICAL_MANIFEST.json',OUT/'soc_physical.pinout.csv',OUT/'soc_physical.pt.rpt',OUT/'soc_physical.map.rpt',OUT/'soc_physical.map.v',ROOT/'logs/soc_physical_tests.json',ROOT/'logs/physical_c2_selftest.json',ROOT/'logs/c7_cpu_lanes_tests.json']
    evidence += [timing,fragment,diagnostic,P/'review_timing.tcl',OUT/'soc_physical.review_timing.rpt',OUT/'soc_physical.bus_setup.rpt',OUT/'soc_physical.bus_hold.rpt',OUT/'soc_physical.clocks.rpt',OUT/'soc_physical.place.rpt',OUT/'soc_physical.route.rpt',routed,ROOT/'logs/soc_physical_cdc_binding.json',ROOT/'logs/soc_physical_sta_tclsh_check.json',ROOT/'logs/soc_physical_route_build.json']
    post_path=ROOT/'logs/soc_physical_postroute_review_inputs.json'
    if route_sdc!=sha(P/'soc_physical.sdc'):evidence.append(post_path)
    if identity_path.is_file():evidence.append(identity_path)
    result={'status':'PASS_REFERENCE_AUDIT','checks':len(checks),'physical_release_ready':False,'board_programmed':False,
            'implementation_artifacts_present':implementation_complete,'resources':resources,'pin_contract':expected,'voltage_observation':voltage,
            'packed_resources':packed,'clock_periods_ns':clocks,'open_items':open_items,'primary_sta':sta,'cdc_skew':bus,
            'timing_signoff':'PASS constrained primary setup/hold plus separate uncut CDC skew on the same routed design; external Flash SPI and board electrical timing remain open.',
            'source_sha256':{'tools/audit_soc_physical.py':sha(Path(__file__))},'evidence_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in evidence}}
    (ROOT/'logs/soc_physical_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f'PASS reference audit: {len(checks)} checks. Physical release remains disabled.')
    return 2 if args.require_ready else 0

if __name__=='__main__':raise SystemExit(main())
