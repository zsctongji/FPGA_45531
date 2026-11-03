"""Align camera reset/configuration with the existing CSI/SoC reset."""
from pathlib import Path
import datetime,hashlib,json,shutil
from c9_probe_image import select
R=Path(__file__).resolve().parents[1];B=R/'build/c9_linebuffer_edges_image_20261103';P=R/'build/c9_linebuffer_reset_image_20261103'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def modified_top(t):
 for old,new in [('always @(posedge CLK_5M or negedge root_reset_n)\n if(!root_reset_n)config_delay','always @(posedge CLK_5M or negedge camera_reset_n)\n if(!camera_reset_n)config_delay'),('assign o_cam_rst_p=~root_reset_n;','assign o_cam_rst_p=~camera_reset_n;')]:
  assert t.count(old)==1,old;t=t.replace(old,new)
 return t
def project_xml():return (B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix())
def main():
 image,audit=select(R,'linebuffer_edges');assert not P.exists()
 test=R/'logs/c9_camera_reset_tests_20261103.json';t=json.loads(test.read_text());assert t['status']=='PASS'
 for n,d in t['source_sha256'].items():assert sha(R/n)==d,n
 P.mkdir()
 for n in ['rtl','vendor_a','overrides']:shutil.copytree(B/n,P/n)
 for n in ['physical_soc_core.v','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']+[p.name for p in B.glob('*ram_symbol*.bin')]:shutil.copy2(B/n,P/n)
 (P/'soc_physical_top.sv').write_text(modified_top((B/'soc_physical_top.sv').read_text()),newline='\n');(P/'soc_physical.xml').write_text(project_xml(),newline='\n')
 for n in ['bind_cdc.py','capture_geometry.py']:(P/n).write_text((B/n).read_text().replace(B.name,P.name).replace('scanout_raw10_linebuffer_edges','scanout_raw10_linebuffer_reset'),newline='\n')
 runner=R/'tools/run_c9_linebuffer_reset.ps1';runner.write_text((R/'tools/run_c9_linebuffer_edges.ps1').read_text().replace(B.name,P.name),newline='\n')
 files=[p for p in P.rglob('*') if p.is_file()]
 m=dict(status='PREPARED_CAMERA_RESET_ALIGNMENT',started=datetime.datetime.now().astimezone().isoformat(),parent_audit_sha256=sha(audit),generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),tests_sha256=sha(test),controlled_change='Camera reset output and camera I2C configuration-delay reset now use camera_reset_n, already used by CSI and pixel pipeline. Original reset polarity and delay length retained. All pixel/CSR/error-mask/DDR/clock/pin/IP logic unchanged. Diagnostic only, no TinyML accelerator.',source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'LINEBUFFER_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n');print('PREPARED camera/CSI reset-alignment candidate')
if __name__=='__main__':main()
