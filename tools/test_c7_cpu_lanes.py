"""Actual vendor BMB upsizer -> pinned AXI SIZE=4 -> C7 boundary -> C2 adapter."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/07_soc_physical';B=ROOT/'build/c7_board_20261101/lane_regression';B.mkdir(parents=True,exist_ok=True)
vendor=ROOT/'projects/03_tinyml/ip/sapphire_soc/sapphire_soc.v'
match=re.search(r'module (BmbUpSizerBridge_\w+)\s*\(.*?\nendmodule',vendor.read_text(),re.S)
assert match,'Actual vendor BMB upsizer missing'
(B/'actual_vendor_upsizer.v').write_text(match[0],encoding='utf-8')
prefix=(ROOT/'projects/06_soc_c2/sim/tb_c2_adapter.sv').read_text().split('integer checks=')[0]
prefix=prefix.replace('module tb_c2_adapter;','module tb_c7_cpu_lanes #(parameter RAW=0);')
prefix=prefix.replace('.s_awaddr(s_awaddr)','.s_awaddr(RAW?s_awaddr:aligned_awaddr)').replace('.s_araddr(s_araddr)','.s_araddr(RAW?s_araddr:aligned_araddr)')
prefix+='''
wire [31:0] aligned_awaddr,aligned_araddr;
c7_cpu_axi_address boundary(.awaddr(s_awaddr),.araddr(s_araddr),.awlen(s_awlen),.arlen(s_arlen),.awsize(s_awsize),.arsize(s_arsize),.aligned_awaddr(aligned_awaddr),.aligned_araddr(aligned_araddr));
reg cpu_valid=0;reg [31:0] cpu_address=0,cpu_data=0;reg [3:0] cpu_mask=0;reg [5:0] cpu_length=0;
wire vendor_valid;wire [31:0] vendor_address;wire [127:0] vendor_data;wire [15:0] vendor_mask;
'''
prefix+=match[1]+''' upsizer(
.io_input_cmd_valid(cpu_valid),.io_input_cmd_ready(),.io_input_cmd_payload_last(1'b1),
.io_input_cmd_payload_fragment_source(1'b0),.io_input_cmd_payload_fragment_opcode(1'b1),
.io_input_cmd_payload_fragment_address(cpu_address),.io_input_cmd_payload_fragment_length(cpu_length),
.io_input_cmd_payload_fragment_data(cpu_data),.io_input_cmd_payload_fragment_mask(cpu_mask),.io_input_cmd_payload_fragment_context(1'b0),
.io_input_rsp_valid(),.io_input_rsp_ready(1'b1),.io_input_rsp_payload_last(),.io_input_rsp_payload_fragment_source(),.io_input_rsp_payload_fragment_opcode(),.io_input_rsp_payload_fragment_data(),.io_input_rsp_payload_fragment_context(),
.io_output_cmd_valid(vendor_valid),.io_output_cmd_ready(1'b1),.io_output_cmd_payload_last(),.io_output_cmd_payload_fragment_source(),.io_output_cmd_payload_fragment_opcode(),
.io_output_cmd_payload_fragment_address(vendor_address),.io_output_cmd_payload_fragment_length(),.io_output_cmd_payload_fragment_data(vendor_data),.io_output_cmd_payload_fragment_mask(vendor_mask),.io_output_cmd_payload_fragment_context(),
.io_output_rsp_valid(1'b0),.io_output_rsp_ready(),.io_output_rsp_payload_last(1'b1),.io_output_rsp_payload_fragment_source(1'b0),.io_output_rsp_payload_fragment_opcode(1'b0),.io_output_rsp_payload_fragment_data(128'b0),.io_output_rsp_payload_fragment_context(5'b0),
.io_systemClk(clk),.systemCd_logic_outputReset(!rst_n));
reg [127:0] expected=0;integer stores=0,reads=0;
task store(input integer off,input integer size,input [31:0] value);
 reg [31:0] a;reg [127:0] d;reg [15:0] mask;integer i;
 begin
  @(negedge clk);cpu_address=32'h1800+off;cpu_data=value;cpu_mask=((1<<size)-1)<<(off%4);cpu_length=size-1;cpu_valid=1;
  #1;if(!vendor_valid)$fatal(1,"Vendor did not emit command");
  a=vendor_address;d=vendor_data;mask=vendor_mask;
  if(a!==32'h1800+off || mask!==(((1<<size)-1)<<off))$fatal(1,"Unexpected pinned vendor contract");
  for(i=0;i<16;i=i+1)if(mask[i])expected[i*8+:8]=d[i*8+:8];
  @(negedge clk);cpu_valid=0;s_awaddr=a;s_awsize=4;s_awlen=0;s_awvalid=1;
  while(!s_awready)@(negedge clk);
  @(negedge clk);s_awvalid=0;s_wdata=d;s_wstrb=mask;s_wlast=1;s_wvalid=1;
  while(!s_wready)@(negedge clk);
  @(negedge clk);s_wvalid=0;s_bready=1;
  while(!s_bvalid)@(negedge clk);
  if(s_bresp!==0)$fatal(1,"CPU byte/word lane rejected offset=%0d response=%0d",off,s_bresp);
  @(negedge clk);s_bready=0;stores=stores+1;
 end
endtask
task read_lane(input integer off);
 begin
  @(negedge clk);s_araddr=32'h1800+off;s_arsize=4;s_arlen=0;s_arvalid=1;
  while(!s_arready)@(negedge clk);
  @(negedge clk);s_arvalid=0;s_rready=0;
  while(!s_rvalid)@(negedge clk);
  if(s_rresp!==0 || s_rdata!==expected)$fatal(1,"CPU read lane/contents incorrect offset=%0d",off);
  repeat(3)begin @(negedge clk);if(!s_rvalid || s_rdata!==expected)$fatal(1,"Read backpressure corruption");end
  s_rready=1;@(negedge clk);s_rready=0;reads=reads+1;
 end
endtask
integer n;
initial begin
 #1;rst_n=0;repeat(4)@(negedge clk);rst_n=1;
 for(n=0;n<4;n=n+1)store(4*n,4,32'h04030201+32'h04040404*n);
 for(n=0;n<16;n=n+1)read_lane(n);
 for(n=0;n<16;n=n+1)store(n,1,{4{8'h80+n[7:0]}});
 for(n=0;n<16;n=n+1)read_lane(n);
 for(n=0;n<16;n=n+2)store(n,2,{2{16'h9876+n[15:0]}});
 for(n=0;n<16;n=n+1)read_lane(n);
 if(rejected || protocol_error || fabric_error)$fatal(1,"Unexpected protocol error");
 $display("PASS c7_cpu_lanes actual_vendor_upsizer stores=%0d reads=%0d SIZE4_shifted_WSTRB all16_offsets backpressure",stores,reads);$finish;
end
initial begin #100000;$fatal(1,"Timeout");end
endmodule
'''
(B/'tb_c7_cpu_lanes.sv').write_text(prefix,encoding='utf-8')
sources=[B/'tb_c7_cpu_lanes.sv',B/'actual_vendor_upsizer.v',P/'rtl/c7_cpu_axi_address.sv',ROOT/'projects/06_soc_c2/rtl/c2_axi_to_vendor.sv',*sorted((ROOT/'projects/06_soc_c2/rtl').glob('*.sv')),*sorted((ROOT/'projects/06_soc_c2/sim').glob('*.sv'))]
sources=list(dict.fromkeys(sources));iv=ROOT/'tools/iverilog/bin/iverilog.exe';rows=[]
for raw in [1,0]:
 exe=B/f'case{raw}.vvp'
 subprocess.run([str(iv),'-g2012','-s','tb_c7_cpu_lanes',f'-Ptb_c7_cpu_lanes.RAW={raw}','-o',str(exe),*[str(p) for p in sources]],cwd=ROOT,check=True)
 r=subprocess.run([str(iv.with_name('vvp.exe')),str(exe)],cwd=ROOT,capture_output=True,text=True,timeout=20)
 (B/f'case{raw}.log').write_text(r.stdout+r.stderr,encoding='utf-8')
 ok=(r.returncode!=0 and 'lane rejected offset=4' in r.stdout) if raw else (r.returncode==0 and 'PASS c7_cpu_lanes' in r.stdout)
 rows.append(dict(raw=raw,expected_result_met=ok,returncode=r.returncode,output=r.stdout))
 print(('RAW_NEGATIVE: ' if raw else 'C7_BOUNDARY: ')+r.stdout.strip(),flush=True)
record=dict(status='PASS' if all(r['expected_result_met'] for r in rows) else 'FAIL',cases=rows,
            source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [vendor,P/'rtl/c7_cpu_axi_address.sv',ROOT/'projects/06_soc_c2/rtl/c2_axi_to_vendor.sv',Path(__file__)]})
(ROOT/'logs/c7_cpu_lanes_tests.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if record['status']=='PASS' else 1)
