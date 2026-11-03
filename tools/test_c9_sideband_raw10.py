"""Test plain wrapper wiring with a protocol stub, not encrypted CSI behavior."""
from pathlib import Path
import hashlib,json,re,subprocess
from patch_c9_raw10_sideband_vendor import patched,patched_bytes
R=Path(__file__).resolve().parents[1];S=R/'team_work/03_ai_soc/c9_live/camera_geometry';B=R/'build/c9_sideband_raw10_tests_20261103'
def main():
 B.mkdir(exist_ok=True);vendor=R/'build/c9_camera_geometry_image_20261102/vendor_a/rtl/csi_rx_controller.sv';old=vendor.read_text();new=patched(old)
 assert old.partition('endmodule')[2]==new.partition('endmodule')[2],'Protected/source tail altered'
 assert vendor.read_bytes().partition(b'endmodule')[2]==patched_bytes(vendor.read_bytes()).partition(b'endmodule')[2],'IP tail bytes altered'
 wrapper=new.partition('endmodule')[0]+'endmodule\n';start=old.index('module `IP_MODULE_NAME(efx_csi2_rx) #(');end=old.index(');',start)+2
 header=old[start:end]
 stub=header+'''
initial if(PACK_TYPE!=1)$fatal(1,"Pack40 profile not applied");
assign word_count=16'hdead;assign datatype=6'h3f;assign vc=2'b11;
assign pixel_data_valid=reset_pixel_n;
assign pixel_per_clk=4'd4;
assign pixel_wordcount=16'd2400;assign pixel_datatype=6'h2b;assign pixel_vc=0;
endmodule
'''
 (B/'wrapper_and_stub.sv').write_text(wrapper+stub,newline='\n')
 tb='''`timescale 1ns/1ps
module tb_sideband_wrapper;
reg clk=0,rst=0;always #5 clk=~clk;
wire [15:0] wc;wire [5:0] dt;wire [1:0] vc;wire de;wire [3:0] ppc;
csi_rx_controller wrapper(.clk_pixel(clk),.reset_pixel_n(rst),.pixel_wordcount(wc),.pixel_datatype(dt),.pixel_vc(vc),.pixel_data_valid(de),.pixel_per_clk(ppc));
wire [63:0] o;c9_sideband_probe monitor(clk,rst,1'b1,1'b1,de,1'b0,wc,dt,ppc,vc,o);
initial begin #1;rst=0;repeat(3)@(negedge clk);rst=1;repeat(8)@(negedge clk);
 if(o[15:0]!=2400 || o[21:16]!=43 || o[27:26]!=0 || !o[31] || o[47:32]!=16'h10)$fatal(1,"byte status leaked or sideband missing %h",o);
 $display("PASS tb_sideband_wrapper actual_plain_wrapper pixel_ports_forwarded byte_status_poison_excluded protocol_stub_only");$finish;end
endmodule
'''
 (B/'tb_wrapper.sv').write_text(tb,newline='\n')
 iv=R/'tools/iverilog/bin/iverilog.exe';cases=[]
 for top,files in [('tb_sideband_small',[S/'c9_sideband_probe_small.sv',S/'tb_sideband_small.sv']),('tb_sideband_wrapper',[B/'wrapper_and_stub.sv',B/'tb_wrapper.sv',S/'c9_sideband_probe_small.sv'])]:
  output=B/(top+'.vvp');cmd=[str(iv),'-g2012','-Wall','-s',top,'-o',str(output),*[str(p) for p in files]]
  q=subprocess.run(cmd,capture_output=True,text=True,timeout=30);(B/(top+'_compile.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
  q=subprocess.run([str(iv.with_name('vvp.exe')),str(output)],capture_output=True,text=True,timeout=30);log=q.stdout+q.stderr;(B/(top+'.log')).write_text(log);assert q.returncode==0 and 'PASS '+top in log,log
  cases.append(dict(name=top,evidence=log));print(log)
 inputs=[vendor,S/'c9_sideband_probe_small.sv',S/'tb_sideband_small.sv',R/'tools/patch_c9_raw10_sideband_vendor.py',R/'tools/patch_c9_sideband_vendor.py',Path(__file__)]
 report=dict(status='PASS',hardware_accessed=False,encrypted_CSI_behavior_simulated=False,cases=cases,source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
 (R/'logs/c9_sideband_raw10_tests_20261103.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
