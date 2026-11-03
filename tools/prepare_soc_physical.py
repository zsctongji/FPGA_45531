"""Generate a V4-reference whole-SoC physical project, with no board access.

Keep C6 portable/native evidence immutable. This new project uses one C6 DDR
controller, A's original CSI/ISP/HDMI blocks and new explicit pixel adapters.
No programmer flow or loadable release package is produced by this script.
"""
from pathlib import Path
import argparse,copy,hashlib,json,re,shutil,zipfile
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/07_soc_physical'
A=ROOT/'build/physical_20261031/a_source/projects/13_a_display_test'
NS='http://www.efinixinc.com/peri_design_db'
PN='http://www.efinixinc.com/enf_proj'
CPU_MHZ=100
E.register_namespace('efxpt',NS)
def n(s):return '{'+NS+'}'+s
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare_a():
    arc=ROOT/'build/team_real_20261031/A_video_source_20261029.zip'
    assert sha(arc)=='46fa61dcf79d6146f073ff8dc5b0095b6eb62b2691923e922ede3008290a1dfd'
    files=['rtl/csi_rx_controller.sv']
    files += ['rtl/debayer/'+s+'.v' for s in ['debayer_top_2to1','line_buffer','raw_to_rgb','rgb_gain_v1','true_dual_port_ram']]
    files += ['rtl/cam_i2c_ctrl/i2c/'+s+'.v' for s in ['i2c_16addr_8data','i2c_8addr_8data','i2c_master_ctrl_top','i2c_master_reg_rom','i2c_master_reg_set']]
    files += ['rtl/cam_i2c_ctrl/i2c_master/'+s+'.v' for s in ['i2c_master_byte_ctrl','i2c_master_top','i2c_master_bit_ctrl','oc_i2c_master']]
    files += ['rtl/cam_i2c_ctrl/i2c_master/i2c_master_defines.v','rtl/cam_i2c_ctrl/i2c_master/timescale.v']
    files += ['rtl/dvi_tx/'+s for s in ['ecc_calc_v1.v','audio_clock_regeneration_packet.sv','audio_packet.sv','auxiliary_video_information_info_frame.sv','audio_infoframe_packet.sv','efx_fifo.v','Sc_Fifo_Slr8.v','packet_assembler.sv','encode.v_encrypted.v','tx_aux.v_encrypted.v','dvi_encoder.v_encrypted.v']]
    renamed=['debayer_top_2to1','line_buffer','raw_to_rgb','rgb_gain_v1','true_dual_port_ram']
    sources=[];provenance={}
    with zipfile.ZipFile(arc) as z:
        # Fresh checkouts must not depend on an earlier manual extraction.
        for f in ['ti60f225_oob.peri.xml','ti60f225_oob.sdc','rtl/ti60f225_oob_top.v']:
            target=A/f;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(z.read('projects/13_a_display_test/'+f))
        for f in files:
            data=z.read('projects/13_a_display_test/'+f);target=P/'vendor_a'/f
            target.parent.mkdir(parents=True,exist_ok=True)
            if '/debayer/' in f:
                text=data.decode('utf-8-sig')
                for word in renamed:text=re.sub(r'\b'+word+r'\b','a_phys_'+word,text)
                target.write_text(text,encoding='utf-8',newline='\n')
            else:target.write_bytes(data)
            sources.append(target);provenance[f]={'original_sha256':hashlib.sha256(data).hexdigest(),'generated_sha256':sha(target),'change':'module namespace only' if '/debayer/' in f else 'byte-identical'}
    return sources,provenance


def gpio(parent,name,pad,mode,voltage='3.3 V LVCMOS'):
    template=next(x for x in parent.findall(n('comp_gpio')) if x.get('name')=='io_cam_scl')
    e=copy.deepcopy(template);e.set('name',name);e.set('gpio_def',pad);e.set('mode',mode);e.set('bus_name','');e.set('io_standard',voltage)
    for c in list(e):
        tag=c.tag.split('}')[-1]
        if (mode=='input' and tag!='input_config') or (mode=='output' and tag!='output_config'):e.remove(c);continue
        for k,v in list(c.attrib.items()):c.set(k,v.replace('io_cam_scl',name))
        if tag=='input_config':c.set('name',name if mode=='input' else name+'_IN');c.set('pull_option','weak pullup' if mode=='input' else 'none')
        elif tag=='output_config':
            c.set('name',name if mode=='output' else name+'_OUT')
            if voltage=='1.8 V LVCMOS':c.set('drive_strength','4')
        elif tag=='output_enable_config':c.set('name',name+'_OE');c.set('name_oen','')
    index=len(parent.findall(n('comp_gpio')));parent.insert(index,e)


def overrides():
    out=P/'overrides';out.mkdir(parents=True,exist_ok=True)
    ddr=ROOT/'projects/03_tinyml/src/ddr3_controller'
    # In SystemVerilog this vendor module's body parameter becomes local
    # because it has an ANSI parameter list. Use a private header instead of
    # an illegal instance override; the protected payload stays byte-identical.
    header=(ddr/'ddr3_parameter.vh').read_text(encoding='utf-8-sig')
    header,count=re.subn(r'(`define\s+tFAW\s+)35000\b',r'\g<1>50000',header)
    assert count==1
    (out/'ddr3_parameter.vh').write_text(header,encoding='utf-8',newline='\n')
    data=(ddr/'ddr3_top.v').read_bytes()
    old=b'`include "ddr3_parameter.vh"'
    new=('`include "'+(out/'ddr3_parameter.vh').as_posix()+'"').encode()
    assert data.count(old)==1
    (out/'ddr3_top.v').write_bytes(data.replace(old,new,1))
    base=ROOT/'projects/06_soc_c2/rtl'
    s=(base/'c2_async_fifo.sv').read_text(encoding='utf-8-sig')
    start=s.index(' reg [WIDTH-1:0] memory')
    s=s[:start]+''' c2_bram_async_fifo #(.WIDTH(WIDTH),.ADDR_BITS(ADDR_BITS)) storage(
 .arst_n(arst_n),.s_clk(s_clk),.s_valid(s_valid),.s_ready(s_ready),.s_data(s_data),
 .d_clk(d_clk),.d_valid(d_valid),.d_ready(d_ready),.d_data(d_data));
endmodule
'''
    (out/'c2_async_fifo.sv').write_text(s,encoding='utf-8',newline='\n')
    s=(base/'c2_image_writer.sv').read_text(encoding='utf-8-sig')
    s=s.replace('assign wdata=buffer[beat[3:0]]','assign wdata=buffer_word')
    s=s.replace('held<=pixel_words;buffer[fill_index[3:0]]<=pixel_words;','held<=pixel_words;')
    marker=' reg [3:0] hash_byte;'
    mem=''' reg [127:0] buffer_word;
 wire [3:0] read_address=(state==WRITE && wready && !wlast)?4'(beat+1'b1):beat[3:0];
 always @(posedge clk) if(state==CAPTURE && pixel_valid && pixel_ready) buffer[fill_index[3:0]]<=pixel_words;
 always @(posedge clk) buffer_word<=buffer[read_address];
'''
    assert marker in s;s=s.replace(marker,mem+marker)
    (out/'c2_image_writer.sv').write_text(s,encoding='utf-8',newline='\n')
    s=(base/'c2_video_framebuffer.sv').read_text(encoding='utf-8-sig')
    s=s.replace('R_END=6,R_ACK=7;','R_END=6,R_ACK=7,R_PREFETCH=8;')
    s=s.replace('wire [127:0] send_word=rbuf[send_index[3:0]];', '''reg [127:0] send_word,write_word;
 wire [3:0] write_read_addr=(ws==W_DATA && wready && !wlast)?4'(windex+1'b1):windex[3:0];
 wire [3:0] scan_read_addr=(rs==R_SEND && fifo_ready && send_index!=rbeats-1)?4'(send_index+1'b1):send_index[3:0];
 always @(posedge clk) begin
  if(ws==W_FILL && in_valid && in_ready && in_data[129:128]==0 && w_offset+32'(fill)<WORDS) wbuf[fill[3:0]]<=in_data[127:0];
  if(rs==R_DATA && rvalid) rbuf[rindex[3:0]]<=rdata;
  write_word<=wbuf[write_read_addr];send_word<=rbuf[scan_read_addr];
 end''')
    s=s.replace('assign wdata=wbuf[windex[3:0]]','assign wdata=write_word')
    old="if(w_offset+32'(fill)<WORDS) begin wbuf[fill[3:0]]<=in_data[127:0];fill<=fill+1'b1;end"
    assert old in s;s=s.replace(old,"if(w_offset+32'(fill)<WORDS) begin fill<=fill+1'b1;end")
    s=s.replace("rbuf[rindex[3:0]]<=rdata;rindex<=rindex+1'b1;","rindex<=rindex+1'b1;")
    s=s.replace('else rs<=R_SEND;','else rs<=R_PREFETCH;')
    s=s.replace('    R_SEND:if(fifo_ready) begin','    R_PREFETCH:rs<=R_SEND;\n    R_SEND:if(fifo_ready) begin')
    # Prefetch after the last R beat handles a one-beat burst correctly even
    # with BRAM READ_FIRST collision semantics on address zero.
    assert s.count('rbuf[rindex[3:0]]<=rdata;')==1 and s.count('wbuf[fill[3:0]]<=in_data[127:0];')==1
    (out/'c2_video_framebuffer.sv').write_text(s,encoding='utf-8',newline='\n')


def constraints():
    tree=E.parse(A/'ti60f225_oob.peri.xml');t=tree.getroot();t.set('name','soc_physical')
    d=t;g=t.find('.//'+n('gpio_info'))
    for b in t.find('.//'+n('iobank_info')):
        if b.get('name')=='2B':b.set('iostd','1.2 V LVCMOS')
        if b.get('name')=='3A':b.set('iostd','1.8 V LVCMOS')
    for e in list(g):
        if e.get('name') in ['LCD_POWER','LCD_RST_P']:g.remove(e)
    gpio(g,'c3_scl','GPIOL_04','inout');gpio(g,'c3_sda','GPIOL_06','inout')
    gpio(g,'integration_arm_n','GPIOL_03','input')
    gpio(g,'uart_rx','GPIOL_02','input')
    # V4 schematic page 9: the six configuration flash signals share GPIO pads
    # after configuration. No extra 3.3V GPIO is substituted for these 1.8V pads.
    gpio(g,'flash_sclk','GPIOL_N_01','output','1.8 V LVCMOS')
    gpio(g,'flash_ss','GPIOL_P_01','output','1.8 V LVCMOS')
    for i,pad in enumerate(['GPIOL_P_03','GPIOL_N_03','GPIOL_P_04','GPIOL_N_04']):gpio(g,f'flash_d{i}',pad,'inout','1.8 V LVCMOS')
    # Remove unused MIPI DSI TX, retaining all five camera RX resources and HDMI.
    m=t.find('.//'+n('mipi_dphy_info'))
    for e in list(m):
        if e.get('ops_type')=='tx':m.remove(e)
    pll=t.find('.//'+n('pll_info'));ddr=next(e for e in pll if e.get('name')=='DDR3_PLL')
    video=next(e for e in pll if e.get('name')=='USER_PLL')
    for e in list(video):
        if e.tag==n('comp_output_clock') and e.get('name')=='vid_clk_dvi2':video.remove(e)
    old=next(e for e in pll if e.get('name')=='MIPI_TX_PLL');pll.remove(old)
    c=E.parse(ROOT/'projects/03_tinyml/Ti60F225_tinyml_helloworld.peri.xml')
    cpu=copy.deepcopy(next(e for e in c.iter(n('pll')) if e.get('name')=='pll_inst1'))
    cpu.set('name','CPU_PLL');cpu.set('ref_clock_name','CLK_25M');cpu.set('locked_name','i_pll_locked');cpu.set('reset_name','pll_inst1_RSTN')
    next(e for e in cpu if e.get('name')=='i_sysclk').set('out_divider','27' if CPU_MHZ==100 else '12')
    pll.append(cpu)
    cam=next(e for e in pll if e.get('name')=='pll_inst4');cam.set('locked_name','pll_inst4_LOCKED');cam.set('reset_name','pll_inst4_RSTN')
    for name,num,divider in [('pixel2_clk',2,6),('pixel1_clk',3,3)]:
        e=E.Element(n('comp_output_clock'),name=name,number=str(num),out_divider=str(divider),is_dyn_phase='false',phase_setting='0',is_inverted='false',conn_type='gclk')
        cam.insert(list(cam).index(cam.find(n('comp_prop'))),e)
    E.indent(tree,space='    ');tree.write(P/'soc_physical.peri.xml',encoding='utf-8',xml_declaration=True)


def wrapper():
    a=(A/'rtl/ti60f225_oob_top.v').read_text(encoding='utf-8-sig')
    h=a[a.index('  (* syn_peri_port'):a.index('\n);')]
    h=h[:h.index('// MIPI DSI')]+h[h.index('// hdmi interface'):]
    h=re.sub(r'^\s*input wire\s+vid_clk_dvi2,','',h,flags=re.M)
    sizes={'CKE_WIDTH-1:0':'0:0','ROW_WIDTH-1:0':'15:0','BANK_WIDTH-1:0':'2:0','CS_WIDTH*RANK_RATIO-1:0':'0:0','DQS_WIDTH-1:0':'1:0','DQ_WIDTH-1:0':'15:0','DM_WIDTH-1:0':'1:0','ODT_WIDTH-1:0':'0:0'}
    for k,v in sizes.items():h=h.replace(k,v)
    h=h.rstrip()+',\ninput wire i_sysclk,i_peripheralClk,i_fb_clk,pixel2_clk,pixel1_clk,uart_rx,integration_arm_n,\n'
    h+='input wire c3_scl_IN,c3_sda_IN,output wire c3_scl_OUT,c3_sda_OUT,c3_scl_OE,c3_sda_OE,\n'
    h+='output wire flash_sclk,flash_ss,\n'+',\n'.join(f'input wire flash_d{i}_IN,output wire flash_d{i}_OUT,flash_d{i}_OE' for i in range(4))
    body='''
wire clocks_locked=pll_locked && user_pll_locked && i_pll_locked && pll_inst4_LOCKED;
wire root_reset_n=i_arstn && clocks_locked;
assign pll_inst1_RSTN=i_arstn;assign USER_PLL_RSTN=i_arstn;
assign DDR3_PLL_RSTN=i_arstn;assign pll_inst4_RSTN=i_arstn;
reg [4:0] arm_settle;reg live_arm;
(* async_reg="true" *) reg arm1,arm2;
always @(posedge core_clk or negedge root_reset_n)
 if(!root_reset_n) begin arm_settle<=0;live_arm<=0;arm1<=1;arm2<=1;end
 else begin
  arm1<=integration_arm_n;arm2<=arm1;
  if(!arm_settle[4]) begin arm_settle<=arm_settle+1'b1;live_arm<=!arm2;end
 end
wire soc_reset;wire camera_reset_n=root_reset_n && !soc_reset;
wire w_mipi_rx_hs,w_mipi_rx_vs,w_mipi_rx_de;wire [63:0] w_mipi_rx_data;
wire [31:0] mipi_debug_out;
assign cam_d0_RST=1'b0;assign cam_d1_RST=1'b0;assign cam_d2_RST=1'b0;assign cam_d3_RST=1'b0;
'''
    start=a.index('csi_rx_controller inst_efx_csi2_rx');end=a.index('//     wire',start)
    csi=a[start:end].replace('(i_arstn)','(camera_reset_n)').replace('(i_mipi_clk)','(core_clk)').replace('(w_mipi_rx_pclk_arstn)','(camera_reset_n)')
    for port in ['Rx_HS_D_4','Rx_HS_D_5','Rx_HS_D_6','Rx_HS_D_7']:
        csi=re.sub(r'(\.'+port+r'\s*)\(\s*\)',r"\1(8'b0)",csi)
    for port in ['u_dly_enable_D','u_dly_inc_D']:
        csi=re.sub(r'(\.'+port+r'\s*)\(\s*\)',r"\1(4'b0)",csi)
    csi=csi.replace('.mipi_debug_out(mipi_debug_out)',".mipi_debug_in(32'b0),.mipi_debug_out(mipi_debug_out)")
    body+=csi
    body+='''
wire [127:0] camera_registers_5m;wire camera_registers_valid_5m;
reg [12:0] config_delay;
always @(posedge CLK_5M or negedge root_reset_n)
 if(!root_reset_n)config_delay<=0;else if(!config_delay[12])config_delay<=config_delay+1'b1;
wire scl_padoen_o,sda_padoen_o;
i2c_master_ctrl_top camera_setup(.clk(CLK_5M),.rst_n(config_delay[12]),
 .scl_pad_i(io_cam_scl_IN),.scl_pad_o(io_cam_scl_OUT),.scl_padoen_o(scl_padoen_o),
 .sda_pad_i(io_cam_sda_IN),.sda_pad_o(io_cam_sda_OUT),.sda_padoen_o(sda_padoen_o),
 .camera_registers(camera_registers_5m),.camera_registers_valid(camera_registers_valid_5m));
assign io_cam_scl_OE=~scl_padoen_o;assign io_cam_sda_OE=~sda_padoen_o;
assign o_cam_rst_p=~root_reset_n;
wire raw_vs,raw_hs,raw_de;wire [15:0] raw2;wire raw_overflow,gray_overflow;
physical_pixel_split #(.IN_BITS(32),.OUT_BITS(16)) raw_split(
 .arst_n(camera_reset_n),.sclk(i_mipi_rx_pclk),.dclk(pixel2_clk),
 .vs(w_mipi_rx_vs),.hs(w_mipi_rx_hs),.de(w_mipi_rx_de && w_mipi_rx_hs),
 .data({w_mipi_rx_data[39:32],w_mipi_rx_data[29:22],w_mipi_rx_data[19:12],w_mipi_rx_data[9:2]}),
 .ovs(raw_vs),.ohs(raw_hs),.ode(raw_de),.odata(raw2),.overflow(raw_overflow));
wire rgb_vs,rgb_hs,rgb_de,rgb_valid;wire [47:0] rgb2;
a_phys_debayer_top_2to1 isp(.in_pclk(pixel2_clk),.in_rstn(camera_reset_n),
 .raw_vs_i(raw_vs),.raw_hs_i(raw_hs),.raw_de_i(raw_de),.raw_valid_i(raw_de),.raw_datax4_i(raw2),
 .r_gain(16'd255),.g_gain(16'd255),.b_gain(16'd255),
 .rgb_vs_o(rgb_vs),.rgb_hs_o(rgb_hs),.rgb_de_o(rgb_de),.rgb_valid_o(rgb_valid),
 .rgb_bout(),.rgb_gout(),.rgb_rout(),.rgb_datax2_o(rgb2));
wire gray_vs,gray_hs,gray_de;wire [15:0] gray2;
physical_gray2 luma(.clk(pixel2_clk),.arst_n(camera_reset_n),.vs(rgb_vs),.hs(rgb_hs),.de(rgb_valid && rgb_de),
 .bgr(rgb2),.ovs(gray_vs),.ohs(gray_hs),.ode(gray_de),.gray(gray2));
wire pixel_vs,pixel_hs,pixel_de;wire [7:0] pixel_gray;
physical_pixel_split #(.IN_BITS(16),.OUT_BITS(8)) gray_split(
 .arst_n(camera_reset_n),.sclk(pixel2_clk),.dclk(pixel1_clk),.vs(gray_vs),.hs(gray_hs),.de(gray_de),.data(gray2),
 .ovs(pixel_vs),.ohs(pixel_hs),.ode(pixel_de),.odata(pixel_gray),.overflow(gray_overflow));
// Any transport/CRC/ECC error stops future publication until common reset.
// Old DISPLAY/READY frames remain protected by C2 ownership; never mask a
// corrupt stream as a valid new source frame.
reg camera_fault;
always @(posedge i_mipi_rx_pclk or negedge camera_reset_n)
 if(!camera_reset_n)camera_fault<=0;
 else if(|(mipi_debug_out & 32'h0000447d))camera_fault<=1;
(* async_reg="true" *) reg fault1,fault2;
always @(posedge pixel1_clk or negedge camera_reset_n)
 if(!camera_reset_n)begin fault1<=0;fault2<=0;end
 else begin fault1<=camera_fault || raw_overflow || gray_overflow;fault2<=fault1;end
wire raster_vs,raster_hs,raster_de;wire [23:0] display_rgb;wire display_vs,display_hs,display_de;
physical_raster raster(.clk(hdmi_tx_slow_clk),.arst_n(camera_reset_n),.vs(raster_vs),.hs(raster_hs),.de(raster_de));
wire c3_alarm;wire c3_scl_low,c3_sda_low;
assign c3_scl_OUT=1'b0;assign c3_sda_OUT=1'b0;
assign c3_scl_OE=c3_scl_low;assign c3_sda_OE=c3_sda_low;
assign led={6'b0,c3_alarm,fault2};
'''
    # Infer exact port set from the current native core header. There are no
    # implicit nets or blanket connections to user GPIO for internal status.
    src=(ROOT/'projects/06_soc_c2/integration/c2_tinyml_soc_top.v').read_text(encoding='utf-8-sig')
    core=src.replace('module c2_tinyml_soc_top','module physical_soc_core',1).replace('input wire c2_video_clk,c2_map_enable,','output wire integrated_reset,\ninput wire c2_video_clk,c2_map_enable,',1)
    core=core.replace('wire io_systemReset;','wire io_systemReset;\nassign integrated_reset=io_systemReset;',1)
    # Actual U12 D9PTK is MT41K128M16JT-125:K, x16 (2KB page).
    # The original 35ns tFAW has no validated reduced-tFAW part entitlement.
    # 50ns covers the standard x16 DDR3-800..1600 timing table. Keep C6
    # and its hashed firmware inputs immutable; override only this instance.
    ddr_instance='ddr3_top #(.AXI_ID_WIDTH(8)) u_ddr3_top'
    assert core.count(ddr_instance)==1
    original_header=(ROOT/'projects/03_tinyml/src/ddr3_controller/ddr3_parameter.vh').as_posix()
    assert original_header in core
    core=core.replace(original_header,(P/'overrides/ddr3_parameter.vh').as_posix())
    # The pinned BMB upsizer retains the CPU byte address, but its downstream
    # BmbToAxi4Bridge declares SIZE=4 for a one-beat partial write/read. Convert
    # that vendor-specific form at this private C7 boundary; keep generic C2's
    # strict request validation and all shifted byte strobes unchanged.
    marker='c2_axi_to_vendor #(.ALLOW_NARROW(1),'
    assert core.count(marker)==1
    boundary='''wire [31:0] c7_cpu_awaddr_aligned,c7_cpu_araddr_aligned;
c7_cpu_axi_address cpu_address_boundary(
 .awaddr(axi_inter_s0_awaddr),.araddr(axi_inter_s0_araddr),
 .awsize(axi_inter_s0_awsize),.arsize(axi_inter_s0_arsize),
 .awlen(axi_inter_s0_awlen),.arlen(axi_inter_s0_arlen),
 .aligned_awaddr(c7_cpu_awaddr_aligned),.aligned_araddr(c7_cpu_araddr_aligned));
'''
    core=core.replace(marker,boundary+marker,1)
    for channel in ['aw','ar']:
        old=f'.s_{channel}addr(axi_inter_s0_{channel}addr)'
        assert core.count(old)==1
        core=core.replace(old,f'.s_{channel}addr(c7_cpu_{channel}addr_aligned)',1)
    (P/'physical_soc_core.v').write_text(core,encoding='utf-8',newline='\n')
    header=core[core.index('output wire integrated_reset'):core.index('\n   );')]
    header=re.sub(r'//[^\n]*','',header);header=re.sub(r'/\*.*?\*/','',header,flags=re.S)
    # Native debug uses USER1; RISCV_SOFT_JTAG is not enabled in define.v.
    header=re.sub(r'`ifdef\s+RISCV_SOFT_JTAG.*?`else\s*`endif','',header,flags=re.S)
    header=re.sub(r'`[^\n]*','',header)
    header=re.sub(r'\(\*.*?\*\)','',header,flags=re.S)
    header=re.sub(r'\[[^\]]*\]','',header)
    names=[]
    for part in header.split(','):
        toks=re.sub(r'\b(input|output|wire|reg)\b',' ',part).split()
        if toks:names.append(toks[-1])
    conn={name:'' for name in names}
    physical=['axi_clk','core_clk','sdram_clk','rx_cal_clk','tx_cal_clk','tx_cal_clk_90edge','i_sysclk','i_peripheralClk','i_fb_clk']
    physical += ['ddr_ck_hi','ddr_ck_lo','ddr_reset_n','ddr_cke','ddr_ba','ddr_cas_n','ddr_cs_n','ddr_ras_n','ddr_we_n','ddr_dqs_in_hi','ddr_dqs_in_lo','ddr_dq_in_hi','ddr_dq_in_lo','ddr_dqs_oe','ddr_dqs_oe_n','ddr_dq_oe','ddr_dqs_out_hi','ddr_dqs_out_lo','ddr_dq_out_hi','ddr_dq_out_lo','ddr_dm_hi','ddr_dm_lo','ddr_odt','pll_shift','pll_shift_sel','pll_shift_ena']
    for name in physical:conn[name]='core_clk' if name=='axi_clk' else name
    conn.update(integrated_reset='soc_reset',ddr_addr='ddr_addr[13:0]',pll_locked='root_reset_n',user_pll_locked='root_reset_n',
                c2_video_clk='pixel1_clk',c2_map_enable='live_arm',c2_pixel_vs='pixel_vs && !fault2',c2_pixel_de='pixel_de && !fault2',c2_pixel_gray='pixel_gray',
                c2_display_clk='hdmi_tx_slow_clk',c2_display_vs='raster_vs',c2_display_hs='raster_hs',c2_display_de='raster_de',
                c2_display_rgb='display_rgb',c2_out_vs='display_vs',c2_out_hs='display_hs',c2_out_de='display_de',
                c3_io_enable='live_arm',c3_sensor_scl_read='c3_scl_IN',c3_sensor_sda_read='c3_sda_IN',c3_sensor_scl_drive_low='c3_scl_low',
                c3_sensor_sda_drive_low='c3_sda_low',c3_buzzer='buzzer_sig',c3_alarm_led='c3_alarm',
                system_uart_0_io_txd='uart_tx',system_uart_0_io_rxd='uart_rx',system_spi_0_io_sclk_write='flash_sclk',system_spi_0_io_ss='flash_ss')
    for name in names:
        if name.startswith('jtag_inst1_'):conn[name]=name
    for i in range(4):
        for suffix,port in [('read','IN'),('write','OUT'),('writeEnable','OE')]:conn[f'system_spi_0_io_data_{i}_{suffix}']=f'flash_d{i}_{port}'
    body+='assign ddr_addr[15:14]=2\'b0;\nphysical_soc_core soc(\n'+',\n'.join('.'+name+'('+value+')' for name,value in conn.items())+');\n'
    body+='''
wire [9:0] tmds_data0,tmds_data1,tmds_data2,tmds_clk;
dvi_encoder hdmi(.pixelclk(hdmi_tx_slow_clk),.rst_p(!camera_reset_n),
 .i_bdata(display_rgb[7:0]),.i_gdata(display_rgb[15:8]),.i_rdata(display_rgb[23:16]),
 .i_de(display_de),.i_hs(display_hs),.i_vs(display_vs),
 .video_format(2'b00),.video_VIC(7'd16),.audio_L(24'd0),.audio_R(24'd0),.audio_valid(1'b0),
 .audio_N(20'd6144),.audio_CTS(20'd148500),.audio_sample_frequency(4'd0),.audio_word_length(4'b1011),
 .tmds_data0(tmds_data0),.tmds_data1(tmds_data1),.tmds_data2(tmds_data2),.tmds_clk(tmds_clk));
assign tmds_tx_clk_TX_DATA=~tmds_clk;assign tmds_tx_data0_TX_DATA=~tmds_data0;
assign tmds_tx_data1_TX_DATA=~tmds_data1;assign tmds_tx_data2_TX_DATA=~tmds_data2;
assign tmds_tx_clk_TX_OE=1'b1;assign tmds_tx_data0_TX_OE=1'b1;assign tmds_tx_data1_TX_OE=1'b1;assign tmds_tx_data2_TX_OE=1'b1;
assign tmds_tx_clk_TX_RST=!camera_reset_n;assign tmds_tx_data0_TX_RST=!camera_reset_n;
assign tmds_tx_data1_TX_RST=!camera_reset_n;assign tmds_tx_data2_TX_RST=!camera_reset_n;
endmodule
'''
    (P/'soc_physical_top.sv').write_text('`timescale 1ns/1ps\nmodule soc_physical_top(\n'+h+'\n);\n'+body,encoding='utf-8',newline='\n')


def project(sources,provenance):
    E.register_namespace('efx',PN);q=lambda s:'{'+PN+'}'+s
    tree=E.parse(ROOT/'projects/06_soc_c2/integration/c2_native.xml');t=tree.getroot();t.set('name','soc_physical');t.set('description','V4-reference physical integration; NOT a hardware-verified release')
    d=t.find(q('design_info'));d.find(q('top_module')).set('name','soc_physical_top')
    all_sources=[]
    for e in list(d.findall(q('design_file'))):
        d.remove(e);p=Path(e.get('name'))
        if p.name=='c2_tinyml_soc_top.v':p=P/'physical_soc_core.v'
        elif p.name in ['ddr3_parameter.vh','ddr3_top.v'] and p.parent.name=='ddr3_controller':p=P/'overrides'/p.name
        elif p.parent.name=='rtl' and p.name in ['c2_async_fifo.sv','c2_image_writer.sv','c2_video_framebuffer.sv']:p=P/'overrides'/p.name
        all_sources.append(p)
    all_sources += [P/'soc_physical_top.sv',P/'rtl/physical_video.sv',P/'rtl/c7_cpu_axi_address.sv',*sources]
    index=list(d).index(d.find(q('top_module')))+1
    for p in dict.fromkeys(all_sources):
        e=E.Element(q('design_file'),name=p.as_posix(),version='default',library='default');d.insert(index,e);index+=1
    c=t.find(q('constraint_info'))
    for e in list(c):c.remove(e)
    E.SubElement(c,q('sdc_file'),name='soc_physical.sdc');E.SubElement(c,q('inter_file'),name='')
    for e in t.find(q('place_and_route')):
        if e.get('name')=='seed':e.set('value','1')
    E.indent(tree,space='    ');tree.write(P/'soc_physical.xml',encoding='utf-8',xml_declaration=True)
    for p in (ROOT/'projects/03_tinyml/ip/sapphire_soc').glob('*.bin'):shutil.copyfile(p,P/p.name)
    manifest={'scope':'Reference V4 physical whole-SoC project; no hardware/power/PCB-revision verification','board_programmed':False,'download_allowed':False,
      'single_ddr':True,'pixel_path':'A RAW10 MSB8 4PPC -> 2PPC A debayer -> rounded 77/150/29 GRAY8 -> 1PPC C2 -> single DDR -> 1080p60 raster -> A HDMI',
      'ddr_profile':{'part':'MT41K128M16JT-125:K','capacity_bytes':268435456,'operating_clock_MHz':400,'reference_voltage_V':1.5,'tFAW_override_ps':50000,'scope':'Conservative x16 tFAW; encrypted controller scheduling and real DDR calibration/read-write remain unverified'},
      'clock_MHz':{'core_clk':100,'i_sysclk':CPU_MHZ,'i_peripheralClk':100,'i_mipi_rx_pclk':50,'pixel2_clk':100,'pixel1_clk':200,'CLK_5M':5,'hdmi_tx_slow_clk':148.5,'hdmi_tx_fast_clk':742.5,'sdram_clk':400},
      'pll_owners':{'PLL_TR0':'DDR','PLL_TL0':'CPU/APB','PLL_BL0':'HDMI','PLL_BR0':'camera/pixel adapters'},
      'reset':'KEY0 C4 and all PLL locks; shared SoC reset after DDR calibration',
      'live_arm':'KEY3 A3 active low sampled at root reset release; default pull-up disables C2 live map and C3 IO. Not approved for physical use until PCB/voltages/map checked.',
      'bank_voltage_V':{'1A':1.8,'1B':1.8,'2A':1.2,'2B':1.2,'3A':1.8,'3B':1.5,'4A':1.5,'4B':1.5,'BL':3.3,'BR':3.3,'TL':3.3,'TR':3.3},
      'A_sources':provenance,'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in dict.fromkeys(all_sources)},'generator_sha256':sha(Path(__file__))}
    (P/'PHYSICAL_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


def sdc():
    # Preserve A's board DDR/MIPI IO timing, not its independent-demo clock
    # groups or stale CPU/DSI clock declarations. Never add blanket multicycles.
    original=(A/'ti60f225_oob.sdc').read_text(encoding='utf-8-sig')
    clock={'tx_cal_clk_90edge':2.5,'sdram_clk':2.5,'rx_cal_clk':2.5,'tx_cal_clk':2.5,
           'core_clk':10,'i_sysclk':1000/CPU_MHZ,'i_peripheralClk':10,'i_fb_clk':10,
           'hdmi_tx_slow_clk':1000/148.5,'fb':1000/54,'i_mipi_rx_pclk':20,
           'pixel2_clk':10,'pixel1_clk':5,'CLK_5M':200,'i_cam_ck_CLKOUT':10,
           'CLK_25M':40,'CLK_27M':1000/27,'jtag_inst1_TCK':20}
    text='# V4 reference, actual PLL allocation. Hardware signoff remains pending.\n'
    for name,period in clock.items():text+=f'create_clock -period {period:.6f} -name {name} [get_ports {{{name}}}]\n'
    text+='create_clock -waveform {0.337 1.010} -period 1.346801 -name hdmi_tx_fast_clk [get_ports {hdmi_tx_fast_clk}]\n'
    text+='set_clock_groups -asynchronous -group {sdram_clk tx_cal_clk rx_cal_clk tx_cal_clk_90edge} -group {core_clk i_sysclk i_peripheralClk i_fb_clk} -group {i_mipi_rx_pclk pixel2_clk pixel1_clk CLK_5M} -group {hdmi_tx_slow_clk hdmi_tx_fast_clk fb} -group {i_cam_ck_CLKOUT} -group {jtag_inst1_TCK}\n'
    for line in original.splitlines():
        if line.lstrip().startswith(('set_input_delay','set_output_delay')) and not any(s in line for s in ['jtag_inst2','mipi_dp_','LCD_','{uart_tx}','{jtag_inst1_RESET}','{jtag_inst1_UPDATE}','{jtag_inst1_DRCK}']):text+=line+'\n'
    for port in ['uart_tx','c3_scl_OE','c3_sda_OE','buzzer_sig','led[1]']:
        for kind in ['max','min']:text+=f'set_output_delay -clock i_peripheralClk -{kind} 0 [get_ports {{{port}}}]\n'
    # Asynchronous board controls are first synchronized by the wrapper/C3.
    text+='set_false_path -from [get_ports {i_arstn integration_arm_n uart_rx c3_scl_IN c3_sda_IN}]\n'
    # Generated after map so binary/Gray MSB register coalescing cannot leave
    # any pointer bits outside the physical skew check.
    text+='source soc_physical_cdc.sdc\n'
    (P/'soc_physical.sdc').write_text(text,encoding='utf-8',newline='\n')


def main():
    global CPU_MHZ
    ap=argparse.ArgumentParser();ap.add_argument('--cpu-mhz',type=int,choices=[100,225],default=100);args=ap.parse_args();CPU_MHZ=args.cpu_mhz
    P.mkdir(parents=True,exist_ok=True)
    sources,provenance=prepare_a();overrides();constraints();wrapper();sdc();project(sources,provenance)
    print('Prepared V4 reference physical whole-SoC project. No programming/release authorization inferred.')

if __name__=='__main__':main()
