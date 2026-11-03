"""Observation-only native edge extension to frozen CSR candidate."""
from pathlib import Path
import datetime,hashlib,json,shutil
from c9_probe_image import select
R=Path(__file__).resolve().parents[1];B=R/'build/c9_linebuffer_csr_image_20261103';P=R/'build/c9_linebuffer_edges_image_20261103';S=R/'team_work/03_ai_soc/c9_live/camera_geometry'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def modified_top(t):
 inst='''wire [31:0] native_edge_counts;wire [7:0] native_edge_flags;
c9_native_edges native_edges(.clk(i_mipi_rx_pclk),.arst_n(camera_reset_n),.enable(csr_enable),
 .vs(w_mipi_rx_vs),.hs(w_mipi_rx_hs),.de(w_mipi_rx_de),.datatype(sb_dt),.vc(sb_vc),.ppc(sb_ppc),.wc(sb_wc),
 .counts(native_edge_counts),.flags(native_edge_flags));
wire [159:0] native_camera_observation={csr_observation[159:128] | {20'b0,native_edge_flags,4'b0},native_edge_counts,csr_observation[95:32],32'hc9f20002};
'''
 assert t.count('physical_soc_core soc(')==1;t=t.replace('physical_soc_core soc(',inst+'physical_soc_core soc(')
 for old,new in [('.c9_camera_data(csr_observation)','.c9_camera_data(native_camera_observation)'),('else if(!norm_armed)norm_debug_seen<=0;','else if(!csr_enable)norm_debug_seen<=0;')]:
  assert t.count(old)==1;t=t.replace(old,new)
 return t
def project_xml():
 t=(B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix());m='<efx:top_module name="soc_physical_top" />'
 return t.replace(m,m+'\n        <efx:design_file name="'+(S/'c9_native_edges.sv').as_posix()+'" version="default" library="default" />')
def main():
 image,audit=select(R,'linebuffer_csr');assert not P.exists()
 test=R/'logs/c9_native_edges_tests_20261103.json';t=json.loads(test.read_text());assert t['status']=='PASS'
 for n,d in t['source_sha256'].items():assert sha(R/n)==d,n
 P.mkdir()
 for n in ['rtl','vendor_a','overrides']:shutil.copytree(B/n,P/n)
 for n in ['physical_soc_core.v','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']+[v.name for v in B.glob('*ram_symbol*.bin')]:shutil.copy2(B/n,P/n)
 (P/'soc_physical_top.sv').write_text(modified_top((B/'soc_physical_top.sv').read_text()),newline='\n');(P/'soc_physical.xml').write_text(project_xml(),newline='\n')
 for n in ['bind_cdc.py','capture_geometry.py']:(P/n).write_text((B/n).read_text().replace(B.name,P.name).replace('scanout_raw10_linebuffer_csr','scanout_raw10_linebuffer_edges'),newline='\n')
 runner=R/'tools/run_c9_linebuffer_edges.ps1';runner.write_text((R/'tools/run_c9_linebuffer_csr.ps1').read_text().replace(B.name,P.name),newline='\n')
 files=[p for p in P.rglob('*') if p.is_file()]+[S/'c9_native_edges.sv']
 record=dict(status='PREPARED_NATIVE_EDGE_OBSERVER',started=datetime.datetime.now().astimezone().isoformat(),parent_audit_sha256=sha(audit),generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),tests_sha256=sha(test),controlled_change='Observe native VS rises/falls and signal/metadata flags after CSR enable, replacing camera word3 pre-debug and reserved flags with native-domain evidence. PHY debug set begins after CSR enable. No pixel, reset, error-mask, DDR, clock, pin or IP parameter changes. TinyML omitted.',source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'LINEBUFFER_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n',newline='\n');print('PREPARED observation-only native VS edge candidate')
if __name__=='__main__':main()
