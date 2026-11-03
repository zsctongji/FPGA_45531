"""Read-only DDR contract comparison against passing C10 and independent C8.

Compares peripheral source, generated LPF settings, controller inputs and
constraints. This is not electrical signoff or fabric-netlist equivalence.
"""
from pathlib import Path
import csv, hashlib, json, re, xml.etree.ElementTree as E

R=Path(__file__).resolve().parents[1]
Q='{http://www.efinixinc.com/peri_design_db}'
J='{http://www.efinixinc.com/enf_proj}'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(e):return E.canonicalize(E.tostring(e,encoding='unicode'),strip_text=True)
def peri(p):
    root=E.parse(p).getroot()
    pll=next(e for e in root.iter(Q+'pll') if e.get('name')=='DDR3_PLL')
    gpio={e.get('name'):canon(e) for e in root.iter(Q+'comp_gpio') if e.get('name','').startswith('ddr_') or e.get('name') in ['verf0','verf1']}
    bank={e.get('name'):dict(e.attrib) for e in root.iter(Q+'iobank')}
    return root,pll,gpio,bank
def lpf(p):
    return {e.get('id'):canon(e) for e in E.parse(p).getroot() if e.tag.endswith('}instance')}
def sources(project):
    values={}
    for e in E.parse(project).getroot().iter(J+'design_file'):
        path=Path(e.get('name'))
        if path.name in ['ddr3_top.v','ddr3_parameter.vh']:key=path.name
        elif '/ddr3_controller/' in path.as_posix():key=path.as_posix().split('/ddr3_controller/',1)[1]
        else:continue
        assert key not in values,'Duplicate controller source key'
        values[key]=dict(path=path.relative_to(R).as_posix(),sha256=sha(path))
        if path.name=='ddr3_top.v':
            text=path.read_text()
            matches=re.findall(r'`include\s+"([^"]*ddr3_parameter\.vh)"',text)
            assert len(matches)==1,'Ambiguous DDR parameter include'
            header=Path(matches[0]);assert header.is_absolute() and header.is_relative_to(R)
            assert sha(header)==sha(R/'projects/07_soc_physical/overrides/ddr3_parameter.vh'),'Included DDR parameters changed'
            normalized=text.replace(matches[0],'<verified-identical-ddr3_parameter.vh>',1)
            values[key].update(normalized_sha256=hashlib.sha256(normalized.encode()).hexdigest(),included_parameter=header.relative_to(R).as_posix(),included_parameter_sha256=sha(header))
    assert len(values)>=10,'Missing encrypted controller source manifest'
    return values
def source_bodies(src):return {n:v.get('normalized_sha256',v['sha256']) for n,v in src.items()}
def controller_ports(path):
    text=path.read_text();body=text.split('ddr3_top #(.AXI_ID_WIDTH(8)) u_ddr3_top',1)[1].split(');',1)[0]
    names=dict(re.findall(r'\.(\w+)\s*\(\s*([^()]*)\s*\)',body))
    return {n:re.sub(r'\s+','',v) for n,v in names.items() if n.startswith('ddr_') or n in [
        'axi_clk','core_clk','sdram_clk','rx_cal_clk','tx_cal_clk','tx_cal_clk_90edge','rstn','pll_shift','pll_shift_sel','pll_shift_ena','cal_done']}

def main():
    baseline=R/'projects/10_soc_cold';c8=R/'projects/08_ddr_diag'
    projects=[R/'build'/n for n in ['c9_ddr_probe_20261101','c9_ddr_probe_speed_20261101','c9_ddr_probe_nopack_20261101']]
    evidence={};results=[]
    def bind(path):evidence[path.relative_to(R).as_posix()]=sha(path)
    accepted_audit=R/'logs/soc_cold_audit.json';accepted=json.loads(accepted_audit.read_text())
    assert accepted['status']=='PASS_OFFLINE_COLD_IMPLEMENTATION'
    for field in ['source_sha256','evidence_sha256']:
        for n,d in accepted[field].items():assert sha(R/n)==d,'Changed accepted C10 input: '+n
    boot_path=R/'logs/c10_warm_boot_20261101/20261101_213308/attempt.json';boot=json.loads(boot_path.read_text())
    assert boot['status']=='PASS_WARM_ROM_FLASH_BOOT' and boot['fpga_image_sha256']==sha(baseline/'outflow/soc_physical.bit')
    assert boot['uart_sha256']==sha(boot_path.parent/'uart.log')
    for f in [accepted_audit,boot_path,boot_path.parent/'uart.log']:bind(f)
    br,bpll,bgpio,bbank=peri(baseline/'soc_physical.peri.xml')
    blpf=lpf(baseline/'outflow/soc_physical.lpf');bsrc=sources(baseline/'soc_physical.xml')
    bports=controller_ports(baseline/'physical_soc_core.v')
    for p in [baseline/'soc_physical.peri.xml',baseline/'soc_physical.xml',baseline/'soc_physical.sdc',baseline/'physical_soc_core.v',baseline/'outflow/soc_physical.lpf']:bind(p)
    macros=dict(re.findall(r'`define\s+(\w+)\s+([^\r\n]+)',(R/bsrc['ddr3_parameter.vh']['path']).read_text()))
    outputs={e.get('name'):e for e in bpll if e.tag==Q+'comp_output_clock'}
    selectors={'RX_CLK_SEL':'rx_cal_clk','TX_CLK_SEL':'tx_cal_clk','TX_CLK_90EDGE_SEL':'tx_cal_clk_90edge'}
    for macro,name in selectors.items():
        assert int(macros[macro])==int(outputs[name].get('number')) and outputs[name].get('is_dyn_phase')=='true',macro
    assert macros['ASYN_AXI_CLK'].strip()=='0' and macros['CK_RATIO'].strip()=='4'
    assert macros['tCK'].strip()=='2500'
    for p in projects:
        root,pll,gpio,bank=peri(p/'soc_physical.peri.xml')
        assert canon(pll)==canon(bpll),p.name+' DDR PLL differs'
        assert gpio==bgpio and bank==bbank,p.name+' DDR IO configuration differs'
        generated=lpf(p/'outflow/soc_physical.lpf');common=set(blpf)&set(generated)
        assert common and all(blpf[k]==generated[k] for k in common),p.name+' Generated peripheral configuration differs'
        src=sources(p/'soc_physical.xml');assert source_bodies(src)==source_bodies(bsrc),p.name+' Controller source bodies differ'
        for v in src.values():
            bind(R/v['path'])
            if 'included_parameter' in v:bind(R/v['included_parameter'])
        assert controller_ports(p/'physical_soc_core.v')==bports,p.name+' DDR port wiring differs'
        # DDR timing statements, including their generated clock-reference pins,
        # must remain identical; other application clocks/JTAG may differ.
        timing=lambda f: [l.strip() for l in f.read_text().splitlines() if 'ddr_' in l or (l.startswith('create_clock') and any(s in l for s in ['tx_cal_clk','rx_cal_clk','sdram_clk','core_clk']))]
        assert timing(p/'soc_physical.sdc')==timing(baseline/'soc_physical.sdc'),p.name+' DDR clock/IO constraints differ'
        for f in ['soc_physical.xml','soc_physical.peri.xml','physical_soc_core.v','soc_physical.sdc','outflow/soc_physical.lpf']:bind(p/f)
        results.append(dict(project=p.relative_to(R).as_posix(),status='MATCHES_C10_STATIC_DDR_CONTRACT',
            ddr_io_components=len(gpio),identical_generated_common_peripherals=len(common),controller_source_files=len(src)))
    _,pll,gpio,_=peri(c8/'ddr_diag.peri.xml')
    assert canon(pll)==canon(bpll) and gpio==bgpio,'Independent C8 DDR physical configuration differs'
    src=sources(c8/'ddr_diag.xml');assert source_bodies(src)==source_bodies(bsrc)
    for f in [c8/'ddr_diag.xml',c8/'ddr_diag.peri.xml',R/'tools/audit_ddr_baseline_contract.py']:bind(f)
    for v in [*bsrc.values(),*src.values()]:
        bind(R/v['path'])
        if 'included_parameter' in v:bind(R/v['included_parameter'])
    report=dict(status='PASS_STATIC_DDR_CONTRACT_COMPARISON',board_calibration_fixed=False,hardware_accessed=False,
        baseline='C10 accepted CPU/DDR/TinyML image',comparisons=results,c8_ddr_pll_io_and_controller_sources_match=True,
        phase_selectors={m:dict(index=int(macros[m]),output=n) for m,n in selectors.items()},
        source_comparison_note='ddr3_top include paths differ by isolated project; each included header is byte-identical and identity-bound before normalizing that path only',
        limitations=['Not fabric-netlist functional equivalence','Not routed fabric timing/electrical equivalence',
                    'Clock activity does not establish actual frequency or phase','Encrypted initialization state definitions unavailable',
                    'C9 COMB4-off and C8 COMB4-on controls still require the board'],evidence_sha256=evidence)
    (R/'logs/ddr_static_contract_20261102.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='evidence_sha256'},indent=2))
if __name__=='__main__':main()
