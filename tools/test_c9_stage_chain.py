"""Synthetic stage localization through frozen, qualified pixel path RTL."""
from pathlib import Path
import hashlib,json,re,subprocess
from c9_probe_image import select
R=Path(__file__).resolve().parents[1]
S=R/'team_work/03_ai_soc/c9_live/camera_geometry'
B=R/'build/c9_stage_tests_20261103'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 image,audit=select(R,'sideband_seed3');P=image.parents[1];B.mkdir(exist_ok=True)
 sources=[S/'c9_stage_probe.sv',S/'tb_stage_chain.sv',P/'rtl/physical_video.sv',R/'projects/06_soc_c2/rtl/c2_bram_async_fifo.sv',R/'projects/06_soc_c2/a_side/video_a_capture.v',R/'projects/06_soc_c2/a_side/video_grid_sampler.v',*sorted((P/'vendor_a/rtl/debayer').glob('*.v'))]
 iv=R/'tools/iverilog/bin/iverilog.exe';cases=[]
 for mode,phase in [(0,0),(0,1),(0,3),(1,0),(1,3),(2,0),(3,0)]:
  name=f'mode{mode}_phase{phase}';exe=B/(name+'.vvp')
  q=subprocess.run([str(iv),'-g2012','-Wall','-s','tb_stage_chain',f'-Ptb_stage_chain.MODE={mode}',f'-Ptb_stage_chain.PHASE={phase}','-o',str(exe),*[str(p) for p in sources]],capture_output=True,text=True,timeout=30)
  (B/(name+'_compile.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
  q=subprocess.run([str(iv.with_name('vvp.exe')),str(exe)],capture_output=True,text=True,timeout=60);out=q.stdout+q.stderr
  (B/(name+'.log')).write_text(out);print(out,flush=True)
  cases.append(dict(mode=mode,phase_ns=phase,passed=q.returncode==0 and 'PASS tb_stage_chain' in out,evidence=out))
 report=dict(status='PASS' if all(c['passed'] for c in cases) else 'FAIL',synthetic_only=True,encrypted_CSI_behavior_simulated=False,real_camera_verified=False,qualified_image_sha256=sha(image),cases=cases,source_sha256={p.relative_to(R).as_posix():sha(p) for p in sources+[Path(__file__)]})
 (R/'logs/c9_stage_chain_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n')
 return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
