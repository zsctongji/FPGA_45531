"""Add explicit W1C/readback startup qualification to frozen linebuffer v2."""
from pathlib import Path
import datetime,hashlib,json,re,shutil
from c9_probe_image import select
R=Path(__file__).resolve().parents[1];B=R/'build/c9_linebuffer_v2_image_20261103';P=R/'build/c9_linebuffer_csr_image_20261103'
S=R/'team_work/03_ai_soc/c9_live/camera_geometry'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def modified_top(t):
 needle='wire norm_vs,norm_hs,norm_de,norm_fault,norm_armed,norm_run;'
 inst='''wire csr_enable,csr_fault,csr_awvalid,csr_awready,csr_wvalid,csr_wready,csr_bvalid,csr_bready,csr_arvalid,csr_arready,csr_rvalid,csr_rready;
wire [5:0] csr_awaddr,csr_araddr;wire [31:0] csr_wdata,csr_rdata;wire [159:0] csr_observation;
c9_csi_capture_gate capture_gate(.clk(i_mipi_rx_pclk),.arst_n(camera_reset_n),.run(norm_run),.debug(mipi_debug_out),
 .awaddr(csr_awaddr),.awvalid(csr_awvalid),.awready(csr_awready),.wdata(csr_wdata),.wvalid(csr_wvalid),.wready(csr_wready),
 .bvalid(csr_bvalid),.bready(csr_bready),.araddr(csr_araddr),.arvalid(csr_arvalid),.arready(csr_arready),
 .rdata(csr_rdata),.rvalid(csr_rvalid),.rready(csr_rready),.capture_enable(csr_enable),.fault(csr_fault),.observation(csr_observation));
'''
 assert t.count(needle)==1;t=t.replace(needle,inst+needle)
 for port,signal in [('axi_awaddr','csr_awaddr'),('axi_awvalid','csr_awvalid'),('axi_awready','csr_awready'),('axi_wdata','csr_wdata'),('axi_wvalid','csr_wvalid'),('axi_wready','csr_wready'),('axi_bvalid','csr_bvalid'),('axi_bready','csr_bready'),('axi_araddr','csr_araddr'),('axi_arvalid','csr_arvalid'),('axi_arready','csr_arready'),('axi_rdata','csr_rdata'),('axi_rvalid','csr_rvalid'),('axi_rready','csr_rready')]:
  t,n=re.subn(r'\.'+port+r'\s*\([^)]*\)', '.'+port+'('+signal+')',t);assert n==1,port
 for old,new in [('else if(!norm_run)norm_debug_seen<=0;','else if(!norm_armed)norm_debug_seen<=0;'),
  ('c9_raw10_linebuffer normalizer','c9_raw10_linebuffer_csr normalizer'),
  ('normalizer(.clk(i_mipi_rx_pclk),.arst_n(camera_reset_n),.run_async(c9_run)','normalizer(.clk(i_mipi_rx_pclk),.arst_n(camera_reset_n),.run_async(csr_enable)'),
  ("wire native_transport_problem=!mipi_debug_out[15]", "wire native_transport_problem=csr_fault || !mipi_debug_out[15]"),
  ('.c9_camera_clk(pixel2_clk)','.c9_camera_clk(i_mipi_rx_pclk)'),('.c9_camera_data(stage_isp_data)','.c9_camera_data(csr_observation)')]:
  assert t.count(old)==1,old;t=t.replace(old,new)
 return t
def project_xml():
 t=(B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix())
 old=(S/'c9_raw10_linebuffer.sv').as_posix();assert t.count(old)==1;t=t.replace(old,(S/'c9_raw10_linebuffer_csr.sv').as_posix())
 marker='<efx:top_module name="soc_physical_top" />';return t.replace(marker,marker+'\n        <efx:design_file name="'+(S/'c9_csi_capture_gate.sv').as_posix()+'" version="default" library="default" />')
def main():
 image,audit=select(R,'linebuffer');assert not P.exists(),'Preserve experiment'
 test=R/'logs/c9_linebuffer_csr_tests_20261103.json';m=json.loads(test.read_text());assert m['status']=='PASS'
 for f in ['source_sha256','generated_sha256']:
  for n,d in m[f].items():assert sha(R/n)==d,n
 expected=(S/'c9_raw10_linebuffer.sv').read_text().replace('module c9_raw10_linebuffer #','module c9_raw10_linebuffer_csr #').replace('if(transport_fault)errors[4]<=1;','if(armed && transport_fault)errors[4]<=1;')
 assert (S/'c9_raw10_linebuffer_csr.sv').read_text()==expected
 P.mkdir()
 for name in ['rtl','vendor_a','overrides']:shutil.copytree(B/name,P/name)
 for name in ['physical_soc_core.v','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']+[p.name for p in B.glob('*ram_symbol*.bin')]:shutil.copy2(B/name,P/name)
 (P/'soc_physical_top.sv').write_text(modified_top((B/'soc_physical_top.sv').read_text()),newline='\n');(P/'soc_physical.xml').write_text(project_xml(),newline='\n')
 for name in ['bind_cdc.py','capture_geometry.py']:(P/name).write_text((B/name).read_text().replace(B.name,P.name).replace('scanout_raw10_linebuffer','scanout_raw10_linebuffer_csr'),newline='\n')
 runner=R/'tools/run_c9_linebuffer_csr.ps1';runner.write_text((R/'tools/run_c9_linebuffer.ps1').read_text().replace(B.name,P.name),newline='\n')
 files=[p for p in P.rglob('*') if p.is_file()]+[S/'c9_raw10_linebuffer_csr.sv',S/'c9_csi_capture_gate.sv']
 record=dict(status='PREPARED_CSR_QUALIFIED_LINEBUFFER',started=datetime.datetime.now().astimezone().isoformat(),parent_audit_sha256=sha(audit),generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),tests_sha256=sha(test),controlled_change='From frozen linebuffer v2: native-domain AXI ISR pre-read, W1C bits14:2, readback before enabling capture; fresh errors remain fatal after natural VS arm. Native CSR camera bank replaces ISP probes; video counters stay video-domain. Pixel linebuffer and downstream unchanged apart from ignoring pre-arm transport errors; DDR, clock, pin, IP params unchanged. No TinyML accelerator.',source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'LINEBUFFER_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n',newline='\n');print('PREPARED independent CSR-qualified linebuffer candidate')
if __name__=='__main__':main()
