"""Create a standalone destructive DDR diagnostic; no hardware access."""
from pathlib import Path
import copy,hashlib,json,re,xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/08_ddr_diag';C=ROOT/'projects/07_soc_physical'
NS='http://www.efinixinc.com/peri_design_db';PN='http://www.efinixinc.com/enf_proj'
def n(x):return '{'+NS+'}'+x
def q(x):return '{'+PN+'}'+x
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 E.register_namespace('efxpt',NS);t=E.parse(C/'soc_physical.peri.xml');r=t.getroot();r.set('name','ddr_diag')
 g=r.find('.//'+n('gpio_info'));keep=[]
 for e in list(g):
  if e.tag!=n('comp_gpio'):continue
  name=e.get('name','')
  if name.startswith('ddr_') or name in ['verf0','verf1','led[0]','led[1]','i_arstn','CLK_25M','uart_tx']:keep.append(name)
  else:g.remove(e)
 for group in ['mipi_dphy_info','lvds_info','jtag_info']:
  node=r.find('.//'+n(group))
  if node is not None:
   for e in list(node):node.remove(e)
 pll=r.find('.//'+n('pll_info'))
 for e in list(pll):
  if e.get('name') not in ['DDR3_PLL','CPU_PLL']:pll.remove(e)
  elif e.get('name')=='CPU_PLL':
   for c in list(e):
    if c.tag==n('comp_output_clock') and c.get('name') not in ['core_clk','i_fb_clk']:e.remove(c)
 # Remove bus declarations with no remaining physical members.
 for node in r.iter():
  for e in list(node):
   if e.tag==n('bus') and not any(x.get('bus_name')==e.get('name') for x in g):node.remove(e)
   elif e.tag==n('bus') and e.get('name')=='led':e.set('msb','1')
 E.indent(t,space='    ');t.write(P/'ddr_diag.peri.xml',encoding='utf-8',xml_declaration=True)
 # Keep precisely the previously verified DDR PHY port declarations.
 top=(C/'soc_physical_top.sv').read_text()
 # Locate the start of the declaration line independently of whitespace.
 begin=top.rfind('\n',0,top.index('tx_cal_clk_90edge'))+1;ports=top[begin:top.index('//LED')].strip().rstrip(',')
 ports=re.sub(r'//[^\n]*','',ports)
 header='input wire i_arstn,CLK_25M,pll_locked,i_pll_locked,i_fb_clk,output wire DDR3_PLL_RSTN,pll_inst1_RSTN,uart_tx,output wire [1:0] led,\n'+ports
 core=(C/'physical_soc_core.v').read_text();inst=core[core.index('ddr3_top #'):core.index('// End of User Design top instance')]
 inst=inst[:inst.rfind(');')+2]
 mapping={'axi_clk':'core_clk','ddr_addr':'mem_addr','sys_rst':'reset_ok','ddr_rstn':'ddr_controller_rstn'}
 for old,new in mapping.items():inst=re.sub(r'(?<=\()\s*'+old+r'\s*(?=\))',new,inst)
 signals={'awid':"8'b0",'awaddr':'awaddr','awlen':"8'b0",'awsize':"3'd4",'awburst':"2'b01",'awlock':"1'b0",'awcache':"4'b0",'awprot':"3'b0",'awqos':"4'b0",'awvalid':'awvalid','awready':'awready',
 'wdata':'wdata','wstrb':"16'hffff",'wlast':"1'b1",'wvalid':'wvalid','wready':'wready','bid':'bid','bresp':'bresp','bvalid':'bvalid','bready':'bready',
 'arid':"8'b0",'araddr':'araddr','arlen':"8'b0",'arsize':"3'd4",'arburst':"2'b01",'arlock':"1'b0",'arcache':"4'b0",'arprot':"3'b0",'arqos':"4'b0",'arvalid':'arvalid','arready':'arready','rid':'rid','rdata':'rdata','rresp':'rresp','rlast':'rlast','rvalid':'rvalid','rready':'rready'}
 for key,val in signals.items():inst=re.sub(r'(\.s_axi_'+key+r'\s*\()\s*[^)]*(\))',r'\g<1>'+val+r'\2',inst)
 body='''
assign DDR3_PLL_RSTN=i_arstn;assign pll_inst1_RSTN=i_arstn;
wire reset_ok=i_arstn && pll_locked && i_pll_locked;
(* async_reg="true" *) reg [1:0] core_release,monitor_release;
always @(posedge core_clk or negedge reset_ok)
 if(!reset_ok)core_release<=0;else core_release<={core_release[0],1'b1};
always @(posedge CLK_25M or negedge i_arstn)
 if(!i_arstn)monitor_release<=0;else monitor_release<={monitor_release[0],1'b1};
reg [16:0] reset_delay;
always @(posedge core_clk or negedge core_release[1])
 if(!core_release[1]) reset_delay<=0;else if(reset_delay<100000)reset_delay<=reset_delay+1'b1;
wire ddr_rstn=reset_delay==100000;
wire [13:0] mem_addr;assign ddr_addr={2'b0,mem_addr};
wire app_sr_active,app_ref_ack,app_zq_ack,cal_done,idelay_ld,mpr_rdlvl_dly;
wire [7:0] wrlvl_dq_check,rd_level_dqs_check;wire [2:0] rdlvl_shift,wrlvl_shift;
wire [6:0] init_cur_state;wire [35:0] ddr_debug_port;
wire [31:0] awaddr,araddr,fail_addr,checked,progress;
wire awvalid,awready,wvalid,wready,bvalid,bready,arvalid,arready,rvalid,rready,rlast;
wire [127:0] wdata,rdata,expected,observed;wire [1:0] bresp,rresp;wire [7:0] bid,rid,error;wire [3:0] state;
// A failed/aborted AXI transaction resets its controller; KEY0 restarts BIST.
wire ddr_controller_rstn=ddr_rstn && state!=7;
ddr_diag_bist bist(.clk(core_clk),.rst_n(ddr_rstn),.cal_done(cal_done),
 .awaddr(awaddr),.araddr(araddr),.awvalid(awvalid),.wvalid(wvalid),.bready(bready),.arvalid(arvalid),.rready(rready),
 .awready(awready),.wready(wready),.bvalid(bvalid),.arready(arready),.rvalid(rvalid),
 .wdata(wdata),.rdata(rdata),.bresp(bresp),.rresp(rresp),.bid(bid),.rid(rid),.rlast(rlast),
 .state(state),.error(error),.fail_addr(fail_addr),.expected(expected),.observed(observed),.checked(checked),.progress(progress));
wire [1:0] diag_led;assign led=diag_led;
ddr_diag_status status(.clk(CLK_25M),.rst_n(monitor_release[1]),.locks({i_pll_locked,pll_locked}),.cal(cal_done),
 .state(state),.error(error),.init_state(init_cur_state),.fail_addr(fail_addr),.checked(checked),.progress(progress),.led(diag_led),.uart_tx(uart_tx));
'''
 (P/'ddr_diag_top.sv').write_text('`timescale 1ns/1ps\nmodule ddr_diag_top(\n'+header+'\n);\n'+body+inst+'\nendmodule\n',encoding='utf-8')
 src=E.parse(C/'soc_physical.xml');pr=src.getroot();pr.set('name','ddr_diag');pr.set('description','Standalone destructive 256MiB DDR diagnosis; no CPU or Flash access')
 design=pr.find(q('design_info'));design.find(q('top_module')).set('name','ddr_diag_top');sources=[]
 for e in list(design.findall(q('design_file'))):
  name=e.get('name');design.remove(e)
  if '/ddr3_controller/' in name or name.endswith('/overrides/ddr3_top.v') or name.endswith('/overrides/ddr3_parameter.vh') or '/src/common/' in name:sources.append(Path(name))
 sources += [P/'ddr_diag_top.sv',*sorted((P/'rtl').glob('*.sv'))]
 index=list(design).index(design.find(q('top_module')))+1
 for p in sources:design.insert(index,E.Element(q('design_file'),name=p.as_posix(),version='default',library='default'));index+=1
 con=pr.find(q('constraint_info'))
 for x in list(con):con.remove(x)
 E.SubElement(con,q('sdc_file'),name='ddr_diag.sdc');E.SubElement(con,q('inter_file'),name='')
 E.register_namespace('efx',PN);E.indent(src,space='    ');src.write(P/'ddr_diag.xml',encoding='utf-8',xml_declaration=True)
 sdc=''
 for clock,period in [('CLK_25M',40),('core_clk',10),('i_fb_clk',10),('sdram_clk',2.5),('tx_cal_clk',2.5),('rx_cal_clk',2.5),('tx_cal_clk_90edge',2.5)]:sdc+=f'create_clock -period {period} -name {clock} [get_ports {{{clock}}}]\n'
 sdc+='set_clock_groups -asynchronous -group {CLK_25M} -group {core_clk i_fb_clk} -group {sdram_clk tx_cal_clk rx_cal_clk tx_cal_clk_90edge}\nset_false_path -from [get_ports {i_arstn}]\n'
 for line in (C/'soc_physical.sdc').read_text().splitlines():
  if line.startswith(('set_input_delay','set_output_delay')) and ('{ddr_' in line):sdc+=line+'\n'
 for out in ['uart_tx','led[0]','led[1]']:
  for kind in ['min','max']:sdc+=f'set_output_delay -clock CLK_25M -{kind} 0 [get_ports {{{out}}}]\n'
 (P/'ddr_diag.sdc').write_text(sdc,encoding='utf-8')
 manifest={'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sources},'generator_sha256':sha(Path(__file__)),'board_test_passed':False,'scope':'Standalone destructive 256MiB x16 DDR3 diagnostic; no CPU/Flash/camera'}
 (P/'DIAG_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 print('Prepared standalone DDR diagnostic; source C7 unchanged.')
if __name__=='__main__':main()
