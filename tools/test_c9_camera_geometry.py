"""Exercise real capture diagnostics and reproduce valid-gap frame rejection.

Synthetic CSI-valid gaps test a hypothesis, not the actual sensor waveform.
No qualified build or historical report is overwritten.
"""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parents[1]
S=R/'team_work/03_ai_soc/c9_live/camera_geometry'
B=R/'build/c9_geometry_tests_20261102'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 B.mkdir(exist_ok=True);iv=R/'tools/iverilog/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');cases=[];sources=set()
 def run(name,top,files,expect_failure=False):
  sources.update(files);binary=B/(name+'.vvp')
  q=subprocess.run([str(iv),'-g2012','-Wall','-s',top,'-o',str(binary),*[str(p) for p in files]],capture_output=True,text=True,timeout=60)
  (B/(name+'_compile.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr
  q=subprocess.run([str(vvp),str(binary)],capture_output=True,text=True,timeout=60)
  output=q.stdout+q.stderr;(B/(name+'.log')).write_text(output)
  matched=(q.returncode!=0 and 'ISP line split/length' in output) if expect_failure else q.returncode==0 and 'PASS '+top in output
  cases.append(dict(name=name,returncode=q.returncode,expected_failure=expect_failure,expected_result_met=matched,evidence=output))
  print(name+': '+('EXPECTED_REJECTION' if expect_failure and matched else 'PASS' if matched else 'FAIL'),flush=True)
 run('capture_geometry','tb_capture_geometry',[S/'tb_capture_geometry.sv',S/'c9_capture_geometry.sv',R/'projects/06_soc_c2/a_side/video_a_capture.v',R/'projects/06_soc_c2/a_side/video_grid_sampler.v'])
 original=R/'projects/07_soc_physical/sim/tb_physical_isp.sv'
 sources.add(original)
 base=original.read_text().replace('tb_physical_isp','tb_camera_valid_gap')
 needle='repeat(WIDTH/4)@(negedge c50);';assert base.count(needle)==1
 for gap in [False,True]:
  content=base
  if gap:content=content.replace(needle,'repeat(WIDTH/8)@(negedge c50);de=0;repeat(3)@(negedge c50);de=1;repeat(WIDTH/8)@(negedge c50);')
  bench=B/('gapped.sv' if gap else 'continuous.sv');bench.write_text(content)
  files=[bench,R/'projects/06_soc_c2/rtl/c2_bram_async_fifo.sv',R/'build/c9_display_fix_20261102/rtl/physical_video.sv',*sorted((R/'build/c9_display_fix_20261102/vendor_a/rtl/debayer').glob('*.v'))]
  run('isp_valid_gap' if gap else 'isp_continuous','tb_camera_valid_gap',files,gap)
 report=dict(status='PASS' if all(c['expected_result_met'] for c in cases) else 'FAIL',board_test_passed=False,
  scope='Synthetic valid gaps reproduce line fragmentation through actual A ISP and pixel glue; sensor valid-gap hypothesis remains unverified',
  cases=cases,source_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(sources|{Path(__file__)})})
 (R/'logs/c9_camera_geometry_tests_20261102.json').write_text(json.dumps(report,indent=2)+'\n')
 return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
