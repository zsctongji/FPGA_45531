"""Qualify startup PHY status before releasing any buffered line; retain errors."""
from pathlib import Path
import datetime,hashlib,json,shutil
from c9_probe_image import select
R=Path(__file__).resolve().parents[1];B=R/'build/c9_linebuffer_stream_image_20261103';P=R/'build/c9_linebuffer_quality_image_20261103';S=R/'team_work/03_ai_soc/c9_live/camera_geometry'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def modified_top(t):
 old="wire native_transport_problem=csr_fault || !mipi_debug_out[15] || |(mipi_debug_out & 32'h0007447d);";assert t.count(old)==1
 new='''wire receiver_transport_problem,receiver_release_ok;wire [3:0] receiver_quality_flags;
c9_receiver_quality receiver_quality(.clk(i_mipi_rx_pclk),.arst_n(camera_reset_n),.enable(csr_enable),
 .frame_armed(norm_armed),.de(w_mipi_rx_de),.debug(mipi_debug_out),
 .transport_fault(receiver_transport_problem),.release_ok(receiver_release_ok),.flags(receiver_quality_flags));
wire native_transport_problem=csr_fault || receiver_transport_problem;'''
 t=t.replace(old,new).replace('c9_raw10_linebuffer_csr normalizer','c9_raw10_linebuffer_quality normalizer')
 old='.ppc(sb_ppc),.transport_fault(native_transport_problem),';assert t.count(old)==1;t=t.replace(old,old+'.quality_ready(receiver_release_ok),')
 old="csr_observation[159:128] | {20'b0,native_edge_flags,4'b0}";assert t.count(old)==1
 t=t.replace(old,"csr_observation[159:128] | {16'b0,receiver_quality_flags,native_edge_flags,4'b0}")
 assert t.count("32'hc9f20002")==1;return t.replace("32'hc9f20002","32'hc9f20003")
def project_xml():
 t=(B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix()).replace((S/'c9_raw10_linebuffer_csr.sv').as_posix(),(S/'c9_raw10_linebuffer_quality.sv').as_posix())
 m='<efx:top_module name="soc_physical_top" />';return t.replace(m,m+'\n        <efx:design_file name="'+(S/'c9_receiver_quality.sv').as_posix()+'" version="default" library="default" />')
def main():
 image,audit=select(R,'linebuffer_stream');assert not P.exists()
 test=R/'logs/c9_receiver_quality_tests_20261103.json';t=json.loads(test.read_text());assert t['status']=='PASS'
 for field in ['source_sha256','generated_sha256']:
  for n,d in t.get(field,{}).items():assert sha(R/n)==d,n
 expected=(S/'c9_raw10_linebuffer_csr.sv').read_text().replace('module c9_raw10_linebuffer_csr #','module c9_raw10_linebuffer_quality #').replace('input wire transport_fault,','input wire transport_fault,quality_ready,').replace('if(pending_vs && (!ready[rbank] || first_line[rbank]))','if(!quality_ready)begin end\n      else if(pending_vs && (!ready[rbank] || first_line[rbank]))')
 assert (S/'c9_raw10_linebuffer_quality.sv').read_text()==expected
 P.mkdir()
 for n in ['rtl','vendor_a','overrides']:shutil.copytree(B/n,P/n)
 for n in ['physical_soc_core.v','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']+[p.name for p in B.glob('*ram_symbol*.bin')]:shutil.copy2(B/n,P/n)
 (P/'soc_physical_top.sv').write_text(modified_top((B/'soc_physical_top.sv').read_text()),newline='\n');(P/'soc_physical.xml').write_text(project_xml(),newline='\n')
 for n in ['bind_cdc.py','capture_geometry.py']:(P/n).write_text((B/n).read_text().replace(B.name,P.name).replace('scanout_raw10_linebuffer_stream','scanout_raw10_linebuffer_quality'),newline='\n')
 runner=R/'tools/run_c9_linebuffer_quality.ps1';runner.write_text((R/'tools/run_c9_linebuffer_stream.ps1').read_text().replace(B.name,P.name),newline='\n')
 files=[p for p in P.rglob('*') if p.is_file()]+[S/'c9_receiver_quality.sv',S/'c9_raw10_linebuffer_quality.sv']
 m=dict(status='PREPARED_RECEIVER_QUALITY_GATE',started=datetime.datetime.now().astimezone().isoformat(),parent_audit_sha256=sha(audit),generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),tests_sha256=sha(test),controlled_change='Buffer output waits for 32 consecutive PHY-clean native cycles after natural frame arm. Prequalification PHY status is retained separately; any subsequent PHY error and all packet/FIFO/init errors remain fatal. No payload release for persistent PHY fault; no WC/PPC/frame-count/DDR/clock/pin/IP change; TinyML omitted.',source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'LINEBUFFER_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n');print('PREPARED strict pre-release PHY-quality gate')
if __name__=='__main__':main()
