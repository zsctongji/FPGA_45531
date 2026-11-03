"""Private C9 derivative with CPU-independent read-only USER2 DDR status."""
from pathlib import Path
import copy, hashlib, json, shutil, xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'projects/09_c7_live_acceptance'
P=ROOT/'build/c9_ddr_probe_20261101'
RTL=ROOT/'team_work/03_ai_soc/c9_live/debug/c9_ddr_probe.sv'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def expected_texts():
    core=(BASE/'physical_soc_core.v').read_text()
    needle='output wire integrated_reset,'
    assert core.count(needle)==1
    core=core.replace(needle,needle+'\noutput wire [99:0] c9_ddr_probe_data,\noutput wire [1:0] c9_reset_status,',1)
    needle='assign integrated_reset=io_systemReset;'
    assert core.count(needle)==1
    core=core.replace(needle,needle+'''
assign c9_reset_status={io_systemReset,cal_done};
// Read-only native status; no probe output enters functional logic.
assign c9_ddr_probe_data={ddr_debug_port[35:32],ddr_debug_port[31:0],
 4'b0,cnt,rdlvl_shift,wrlvl_shift,mpr_rdlvl_dly,idelay_ld,
 5'b0,rd_level_dqs_check,wrlvl_dq_check,init_cur_state,ddr_rstn,sys_rst,io_systemReset,cal_done};''',1)
    top=(BASE/'soc_physical_top.sv').read_text()
    ports=''.join('  (* syn_peri_port = 0 *) '+('output' if name=='TDO' else 'input')+' jtag_inst2_'+name+',\n'
                  for name in ['CAPTURE','DRCK','RESET','RUNTEST','SEL','SHIFT','TCK','TDI','TMS','UPDATE','TDO'])
    needle='module soc_physical_top(\n';assert top.count(needle)==1
    top=top.replace(needle,needle+ports,1)
    needle='physical_soc_core soc(\n';assert top.count(needle)==1
    top=top.replace(needle,'''wire [99:0] c9_ddr_probe_data;wire [1:0] c9_reset_status;
c9_ddr_probe diagnostic_user2(
 .tck(jtag_inst2_TCK),.tdi(jtag_inst2_TDI),.selected(jtag_inst2_SEL),.capture(jtag_inst2_CAPTURE),.shift(jtag_inst2_SHIFT),
 .root_reset_n(root_reset_n),.core_clk(core_clk),.system_clk(i_sysclk),.tx_clk(tx_cal_clk),.rx_clk(rx_cal_clk),
 .locks({pll_inst4_LOCKED,i_pll_locked,user_pll_locked,pll_locked}),.debug_high(c9_ddr_probe_data[99:96]),
 .status0(c9_ddr_probe_data[31:0]),.status1(c9_ddr_probe_data[63:32]),.status2(c9_ddr_probe_data[95:64]),.tdo(jtag_inst2_TDO));
physical_soc_core soc(
.c9_ddr_probe_data(c9_ddr_probe_data),.c9_reset_status(c9_reset_status),
''',1)
    needle="assign led={6'b0,c3_alarm,fault2};";assert top.count(needle)==1
    top=top.replace(needle,"assign led={6'b0,c9_reset_status}; // Diagnostic LED0 cal_done, LED1 CPU reset.",1)
    N='http://www.efinixinc.com/peri_design_db';Q='http://www.efinixinc.com/enf_proj'
    E.register_namespace('efxpt',N);E.register_namespace('efx',Q)
    tree=E.parse(BASE/'soc_physical.peri.xml');j=next(x for x in tree.iter() if x.tag=='{'+N+'}jtag_info')
    assert len(j)==1 and j[0].get('jtag_def')=='JTAG_USER1'
    second=copy.deepcopy(j[0])
    for e in second.iter():
        for key,val in list(e.attrib.items()):e.set(key,val.replace('jtag_inst1','jtag_inst2').replace('JTAG_USER1','JTAG_USER2'))
    j.append(second);E.indent(tree,space='    ')
    peri=E.tostring(tree.getroot(),encoding='unicode')+'\n'
    tree=E.parse(BASE/'soc_physical.xml');r=tree.getroot();q=lambda s:'{'+Q+'}'+s
    for e in r.iter():
        for key,val in list(e.attrib.items()):e.set(key,val.replace(BASE.as_posix(),P.as_posix()))
    design=r.find(q('design_info'))
    index=list(design).index(design.findall(q('design_file'))[-1])+1
    design.insert(index,E.Element(q('design_file'),name=RTL.as_posix(),version='default',library='default'))
    for e in r.find(q('place_and_route')):
        if e.get('name')=='seed':e.set('value','2')
    E.indent(tree,space='    ');xml=E.tostring(r,encoding='unicode')+'\n'
    sdc=(BASE/'soc_physical.sdc').read_text()
    needle='create_clock -period 20.000000 -name jtag_inst1_TCK [get_ports {jtag_inst1_TCK}]\n'
    assert sdc.count(needle)==1
    sdc=sdc.replace(needle,needle+'create_clock -period 20.000000 -name jtag_inst2_TCK [get_ports {jtag_inst2_TCK}]\n',1)
    lines=sdc.splitlines();groups=[i for i,s in enumerate(lines) if s.startswith('set_clock_groups ')]
    assert len(groups)==1;lines[groups[0]]+=' -group {jtag_inst2_TCK}'
    sdc='\n'.join(lines)+'\n'
    return {'physical_soc_core.v':core,'soc_physical_top.sv':top,'soc_physical.xml':xml,'soc_physical.peri.xml':peri,'soc_physical.sdc':sdc}

def main():
    a=json.loads((ROOT/'logs/soc_live_audit.json').read_text())
    assert a['status']=='PASS_OFFLINE_LIVE_IMPLEMENTATION'
    for field in ['source_sha256','evidence_sha256']:
        for n,d in a[field].items():assert sha(ROOT/n)==d,n
    assert not P.exists(),'Preserve prior diagnostic output'
    shutil.copytree(BASE,P)
    for name,text in expected_texts().items():(P/name).write_text(text,encoding='utf-8',newline='\n')
    for i in range(4):
        p=P/f'EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol{i}.bin'
        data=p.read_text().split();assert len(data)==1024
        data[0]=format(0x6f if i==0 else 0,'08b');p.write_text('\n'.join(data)+'\n')
    source=(ROOT/'tools/generate_physical_cdc.py').read_text()
    old="ROOT/'logs/soc_physical_cdc_binding.json'";assert source.count(old)==1
    source=source.replace(old,"ROOT/'build/c9_ddr_probe_20261101/cdc_binding.json'")
    (P/'bind_cdc.py').write_text("from pathlib import Path\nns={'__name__':'ddr_probe_binder','__file__':"+repr(str(ROOT/'tools/generate_physical_cdc.py'))+"}\nexec(compile("+repr(source)+",'ddr_probe_binder','exec'),ns)\nns['P']=Path("+repr(str(P))+")\nns['main']()\n")
    inputs=[P/n for n in expected_texts()]+[RTL]+list(P.glob('*ram_symbol*.bin'))
    record=dict(status='PREPARED_ONLY',diagnostic_only=True,flash_written=False,board_programmed=False,
                generator_sha256=sha(Path(__file__)),base_audit_sha256=sha(ROOT/'logs/soc_live_audit.json'),
                source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in inputs},
                scope='Read-only USER2 DDR stage/clock observation; native multi-bit samples are not atomic; parked ROM')
    (P/'PROBE_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

if __name__=='__main__':main()
