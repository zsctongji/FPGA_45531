"""Keep sensor in standby through configuration/CSR cleanup, stream on last."""
from pathlib import Path
import datetime,hashlib,json,shutil
from c9_probe_image import select
from patch_c9_camera_stream_gate import patched
R=Path(__file__).resolve().parents[1];B=R/'build/c9_linebuffer_reset_image_20261103';P=R/'build/c9_linebuffer_stream_image_20261103';V='vendor_a/rtl/cam_i2c_ctrl/i2c'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def modified_top(t):
 old='i2c_master_ctrl_top camera_setup(.clk(CLK_5M),.rst_n(config_delay[12]),';assert t.count(old)==1
 return t.replace(old,old+'.allow_stream(csr_enable),')
def project_xml():return (B/'soc_physical.xml').read_text().replace(B.as_posix(),P.as_posix())
def main():
 image,audit=select(R,'linebuffer_reset');assert not P.exists()
 test=R/'logs/c9_camera_stream_gate_tests_20261103.json';t=json.loads(test.read_text());assert t['status']=='PASS'
 for field in ['source_sha256','generated_sha256']:
  for n,d in t[field].items():assert sha(R/n)==d,n
 P.mkdir()
 for n in ['rtl','vendor_a','overrides']:shutil.copytree(B/n,P/n)
 for n in ['i2c_master_ctrl_top.v','i2c_master_reg_set.v','i2c_master_reg_rom.v']:(P/V/n).write_text(patched(n,(B/V/n).read_text()),newline='\n')
 for n in ['physical_soc_core.v','soc_physical.peri.xml','soc_physical.sdc','review_timing.tcl']+[p.name for p in B.glob('*ram_symbol*.bin')]:shutil.copy2(B/n,P/n)
 (P/'soc_physical_top.sv').write_text(modified_top((B/'soc_physical_top.sv').read_text()),newline='\n');(P/'soc_physical.xml').write_text(project_xml(),newline='\n')
 for n in ['bind_cdc.py','capture_geometry.py']:(P/n).write_text((B/n).read_text().replace(B.name,P.name).replace('scanout_raw10_linebuffer_reset','scanout_raw10_linebuffer_stream'),newline='\n')
 runner=R/'tools/run_c9_linebuffer_stream.ps1';runner.write_text((R/'tools/run_c9_linebuffer_reset.ps1').read_text().replace(B.name,P.name),newline='\n')
 files=[p for p in P.rglob('*') if p.is_file()]+[R/'tools/patch_c9_camera_stream_gate.py']
 m=dict(status='PREPARED_QUIESCENT_SENSOR_START',started=datetime.datetime.now().astimezone().isoformat(),parent_audit_sha256=sha(audit),generator_sha256=sha(Path(__file__)),runner_sha256=sha(runner),tests_sha256=sha(test),controlled_change='Sensor remains in standby for all configuration and 16 register reads; replace early stream-on by standby, append stream-on as transaction183. I2C sequencer waits before last transaction for synchronized CSR-ready. No mask relaxation, pixel/DDR/PLL/pin/CSI IP changes; no TinyML accelerator.',source_sha256={p.relative_to(R).as_posix():sha(p) for p in files})
 (P/'LINEBUFFER_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n');print('PREPARED standby/config/readback/CSR-qualified stream-on candidate')
if __name__=='__main__':main()
