"""Repair the working LED example without changing vendor pin assignments."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
project=root/'projects/01_led'
top=project/'src/LED_8bit_Test.v'
data=top.read_bytes()
original_digest=hashlib.sha256(data).hexdigest()
old=b'wire led_clk = clk_sel? clk_50m :clk_54m;'
if old in data:
    resets=b'reg [1:0] rst54, rst50, rst25, rstosc;\r\n'
    for clk, signal in [('clk_54m','rst54'),('clk_50m','rst50'),('clk_25m_x2','rst25'),('osc_clk','rstosc')]:
        resets+=(f'always @(posedge {clk} or negedge sys_rst_n)\r\n'
                 f'    if (!sys_rst_n) {signal} <= 2\'b00;\r\n'
                 f'    else {signal} <= {{{signal}[0], 1\'b1}};\r\n').encode()
    data=data.replace(old,resets)
    data=data.replace(b'.clk(led_clk)',b'.clk(clk_54m)')
    def update_instance(match):
        body=match[2]
        clk=re.search(rb'\.clk\((\w+)\)',body)[1].decode()
        signal={'clk_54m':'rst54','clk_50m':'rst50','clk_25m_x2':'rst25','osc_clk':'rstosc'}[clk]
        assert body.count(b'.rst_n(sys_rst_n)') == 1
        return match[1]+b'('+body.replace(b'.rst_n(sys_rst_n)',f'.rst_n({signal}[1])'.encode())+b');'
    names=b'key[1-4]_detect_inst|led_ctrl_inst|clk_50m_led_ctrl_inst|clk_25m_led_ctrl_inst|clk_80m_led_ctrl_inst'
    data,count=re.subn(rb'((?:'+names+rb')\s*)\((.*?)\);',update_instance,data,flags=re.S)
    assert count == 8
    data=data.replace(b'{{3{led_data4}},{2{led_data3}},led_data2,led_data1}',b'{{4{led_data4}},{2{led_data3}},led_data2,led_data1}')
    # Debounce duration uses the actual domain frequencies from the vendor clocks.
    for instance,frequency in [('key2_detect_inst',50),('key3_detect_inst',25),('key4_detect_inst',80)]:
        pattern=rb'(key_detect #\s*\(\s*\.CLK_FREQUENCY_MHz\()54(\)\s*\)\s*'+instance.encode()+rb')'
        data,count=re.subn(pattern,lambda m:m[1]+str(frequency).encode()+m[2],data)
        assert count == 1
    top.write_bytes(data)
keyfile=project/'src/key_detect.v'
keydata=keyfile.read_bytes()
header=keydata.split(b'module key_detect #')[0]
body=b'''module key_detect #(
    parameter integer CLK_FREQUENCY_MHz = 50,
    parameter integer DEBOUNCE_MS = 15
)(
    input wire i_key,
    input wire clk,
    input wire rst_n,
    output reg key_sw_en
);
    localparam integer MAX_CNT = CLK_FREQUENCY_MHz * 1000 * DEBOUNCE_MS - 1;
    (* syn_preserve = 1 *) reg [1:0] key_sync;
    reg stable_key;
    reg [31:0] stable_count;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            key_sync <= 2'b11;
            stable_key <= 1'b1;
            stable_count <= 0;
            key_sw_en <= 0;
        end else begin
            key_sync <= {key_sync[0], i_key};
            key_sw_en <= 0;
            if (key_sync[1] == stable_key)
                stable_count <= 0;
            else if (stable_count == MAX_CNT) begin
                stable_count <= 0;
                stable_key <= key_sync[1];
                // One pulse after a debounced press followed by a debounced release.
                key_sw_en <= key_sync[1];
            end else
                stable_count <= stable_count + 1'b1;
        end
    end
endmodule
'''.replace(b'\n',b'\r\n')
keyfile.write_bytes(header+body)

# Use valid fabric clocks from the fresh PT output, not unfilled HSIO placeholders.
pt_sdc=project/'outflow/LED_8bit_Test.pt.sdc'
clocks=[]
for line in pt_sdc.read_text().splitlines():
    if line.startswith('create_clock') and '<' not in line:
        clocks.append(line)
assert len(clocks) == 4
sdc=project/'constraints/led_clocks.sdc'
sdc.parent.mkdir(parents=True,exist_ok=True)
sdc.write_text('# Fabric clocks copied from fresh Interface Designer output; asynchronous buttons are synchronized in RTL.\n'+'\n'.join(clocks)+'\n')
path=project/'LED_8bit_Test.xml'
ns='http://www.efinixinc.com/enf_proj'
tree=ET.parse(path)
tree.getroot().find(f'{{{ns}}}constraint_info/{{{ns}}}sdc_file').set('name','constraints/led_clocks.sdc')
ET.register_namespace('efx',ns)
ET.register_namespace('xsi','http://www.w3.org/2001/XMLSchema-instance')
tree.write(path,encoding='utf-8',xml_declaration=True)
record={'source_top_before_sha256':original_digest,'modified_top_sha256':hashlib.sha256(top.read_bytes()).hexdigest(),
        'key_detect_sha256':hashlib.sha256(keyfile.read_bytes()).hexdigest(),
        'changes':['Use one clock for key1 debounce and LED1; remove live fabric clock mux',
                   'Async reset assertion and synchronized release in each domain',
                   'Synchronize/debounce button inputs; correct 15 ms units and domain frequencies',
                   'Drive all 8 LEDs; preserve vendor peripheral pin configuration',
                   'Use the four generated fabric clock constraints without unused placeholders'],
        'physical_board_tested':False,'clock_constraints':clocks}
(project/'PREPARATION_RECORD.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
