"""Lightweight stage diagnostic: idle unused TinyML master/custom interface."""
from pathlib import Path
import datetime,hashlib,json,re,shutil
import prepare_c9_stage as common
R=common.R;B=common.B;P=R/'build/c9_stage_min_image_20261103';S=common.S
modified_top=common.modified_top
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def without_tinyml(text):
 start=text.index('tinyml_top#(');end=text.index('\n);',start)+3
 block=text[start:end]
 outputs=['cmd_ready','cmd_int','rsp_valid','rsp_outputs_0',
 'm_axi_awvalid','m_axi_awaddr','m_axi_awlen','m_axi_awsize','m_axi_awburst','m_axi_awprot','m_axi_awlock','m_axi_awcache',
 'm_axi_wdata','m_axi_wstrb','m_axi_wlast','m_axi_wvalid','m_axi_bready',
 'm_axi_arvalid','m_axi_araddr','m_axi_arlen','m_axi_arsize','m_axi_arburst','m_axi_arprot','m_axi_arlock','m_axi_arcache','m_axi_rready']
 assignments=[]
 for port in outputs:
  found=re.findall(r'\.'+port+r'\s*\(\s*(\w+)\s*\)',block);assert len(found)==1,port
  assignments.append("assign "+found[0]+" = '0;")
 # No accelerator command is accepted; no fake success/result. S2 AXI idle.
 return text[:start]+'// Stage-only diagnostic: TinyML accelerator omitted, custom commands disabled.\n'+'\n'.join(assignments)+text[end:]
def project_xml():
 return common.project_xml().replace(common.P.as_posix(),P.as_posix())
def main():
 from c9_probe_image import select
 image,audit=select(R,'sideband_seed3');assert not P.exists(),'Preserve experiment'
 test=R/'logs/c9_stage_chain_tests_20261103.json';t=json.loads(test.read_text());assert t['status']=='PASS'
 for n,d in t['source_sha256'].items():assert sha(R/n)==d,n
 P.mkdir()
 for name in ['rtl','overrides','vendor_a']:shutil.copytree(B/name,P/name)
 for name in ['physical_soc_core.v','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']+[p.name for p in B.glob('*ram_symbol*.bin')]:shutil.copy2(B/name,P/name)
 (P/'physical_soc_core.v').write_text(without_tinyml((B/'physical_soc_core.v').read_text()),newline='\n')
 (P/'soc_physical_top.sv').write_text(modified_top((B/'soc_physical_top.sv').read_text()),newline='\n')
 (P/'soc_physical.xml').write_text(project_xml(),newline='\n')
 for name in ['bind_cdc.py','capture_geometry.py']:
  (P/name).write_text((B/name).read_text().replace(B.name,P.name).replace('scanout_sideband_observer','scanout_stage_min_observer'),newline='\n')
 runner=R/'tools/run_c9_stage_min.ps1';runner.write_text((R/'tools/run_c9_sideband_seed3.ps1').read_text().replace(B.name,P.name),newline='\n')
 files=[p for p in P.rglob('*') if p.is_file()]+[S/'c9_stage_probe.sv']
 record=dict(status='PREPARED_STAGE_DIAGNOSTIC',started=datetime.datetime.now().astimezone().isoformat(),parent_audit_sha256=sha(audit),generator_sha256=sha(Path(__file__)),base_generator_sha256=sha(Path(common.__file__)),runner_sha256=sha(runner),tests_sha256=sha(test),controlled_change='Same native-domain stage probes and pixel path as stage variant. TinyML accelerator omitted, custom commands unaccepted, AXI S2 master idle. CPU, C2, unique DDR, pixel/control/clock/pin/IP connections retained. Pack40 diagnostic only; no AI/concurrency acceptance.',source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'STAGE_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n',newline='\n')
 print('PREPARED lightweight stage diagnostic; TinyML unavailable; active profile unchanged')
if __name__=='__main__':main()
