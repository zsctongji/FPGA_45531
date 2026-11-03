"""Red/green through frozen A ISP plus ordering, rejection and reset cases."""
from pathlib import Path
import hashlib,json,subprocess
from c9_probe_image import select
R=Path(__file__).resolve().parents[1];S=R/'team_work/03_ai_soc/c9_live/camera_geometry';B=R/'build/c9_linebuffer_tests_20261103'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 image,audit=select(R,'stage_min');P=image.parents[1];B.mkdir(exist_ok=True)
 original=S/'tb_stage_chain.sv';bench=original.read_text().replace('tb_stage_chain','tb_linebuffer_chain')
 old='if(MODE==1 && (complete_records!=0 || width!=72 || native[22:12]!=18 || stages[22:12]!=36 || output_stage[10:0]!=72))$fatal(1,"Gap did not reproduce 72-pixel fragmentation");'
 assert bench.count(old)==1
 bench=bench.replace(old,'if(MODE==1 && (complete_records!=3 || width!=WIDTH || height!=4))$fatal(1,"RAW valid gaps must produce full 1920-pixel rows");')
 # Drain both full line banks and the closing VS; acceptance remains exact.
 bench=bench.replace('vs=1;repeat(100)@(negedge c50);','vs=1;repeat(2000)@(negedge c50);')
 red=B/'red_chain.sv';red.write_text(bench,newline='\n')
 needle="physical_pixel_split raw_split(rst,c50,c100,vs,hs,de,32'h80808080,rvs,rhs,rde,raw2,rov);"
 inst="""wire fvs,fhs,fde,ffault;wire [31:0] fdata;wire [6:0] ferr;wire [18:0] fcount;
c9_raw10_linebuffer #(.HEIGHT(4)) normalizer(.clk(c50),.arst_n(rst),.run_async(run),.vs(vs),.de(de),.data(32'h80808080),.wordcount(16'd2400),.datatype(6'h2b),.vc(2'd0),.ppc(4'd4),.transport_fault(1'b0),.ovs(fvs),.ohs(fhs),.ode(fde),.odata(fdata),.fault(ffault),.errors(ferr),.last_frame_beats(fcount));
physical_pixel_split raw_split(rst,c50,c100,fvs,fhs,fde,fdata,rvs,rhs,rde,raw2,rov);"""
 assert bench.count(needle)==1
 green=B/'green_chain.sv';green.write_text(bench.replace(needle,inst).replace('if(rov || pov)$fatal','if(ffault)$fatal(1,"Normalizer fault %h count %0d",ferr,fcount);\n  if(rov || pov)$fatal'),newline='\n')
 iv=R/'tools/iverilog/bin/iverilog.exe';cases=[];inputs={Path(__file__),original,S/'c9_raw10_linebuffer.sv',S/'tb_raw10_linebuffer.sv',S/'c9_stage_probe.sv'}
 glue=[S/'c9_stage_probe.sv',P/'rtl/physical_video.sv',R/'projects/06_soc_c2/rtl/c2_bram_async_fifo.sv',R/'projects/06_soc_c2/a_side/video_a_capture.v',R/'projects/06_soc_c2/a_side/video_grid_sampler.v',*sorted((P/'vendor_a/rtl/debayer').glob('*.v'))];inputs.update(glue)
 def run(name,top,files,params,red_expected=False):
  exe=B/(name+'.vvp');q=subprocess.run([str(iv),'-g2012','-Wall','-s',top,*[f'-P{top}.{k}={v}' for k,v in params.items()],'-o',str(exe),*[str(p) for p in files]],capture_output=True,text=True,timeout=30)
  (B/(name+'_compile.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
  q=subprocess.run([str(iv.with_name('vvp.exe')),str(exe)],capture_output=True,text=True,timeout=60);out=q.stdout+q.stderr;(B/(name+'.log')).write_text(out)
  passed=(q.returncode!=0 and 'RAW valid gaps must produce full 1920-pixel rows' in out) if red_expected else q.returncode==0 and 'PASS '+top in out
  cases.append(dict(name=name,expected_failure=red_expected,matched=passed,returncode=q.returncode,evidence=out));print(name+': '+('EXPECTED_FAILURE' if red_expected and passed else 'PASS' if passed else 'FAIL'),flush=True)
 run('red_original_gapped','tb_linebuffer_chain',[red,*glue],dict(MODE=1),True)
 for mode,phase in [(0,0),(0,1),(0,3),(1,0),(1,1),(1,3),(2,0),(3,0)]:
  run(f'green_mode{mode}_phase{phase}','tb_linebuffer_chain',[green,S/'c9_raw10_linebuffer.sv',*glue],dict(MODE=mode,PHASE=phase))
 for case in range(11):run(f'unit{case}','tb_raw10_linebuffer',[S/'c9_raw10_linebuffer.sv',S/'tb_raw10_linebuffer.sv'],dict(CASE=case))
 report=dict(status='PASS' if all(c['matched'] for c in cases) else 'FAIL',hardware_accessed=False,real_camera_verified=False,encrypted_CSI_behavior_simulated=False,cases=cases,source_sha256={p.relative_to(R).as_posix():sha(p) for p in sorted(inputs)},generated_sha256={p.relative_to(R).as_posix():sha(p) for p in [red,green]})
 (R/'logs/c9_linebuffer_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
 return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
