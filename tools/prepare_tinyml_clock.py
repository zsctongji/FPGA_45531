from pathlib import Path
import json
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
project=root/'projects/03_tinyml'
peri=project/'Ti60F225_tinyml_helloworld.peri.xml'
tree=ET.parse(peri)
ns=tree.getroot().tag.partition('}')[0].lstrip('{')
ET.register_namespace('efxpt',ns)
matches=[x for x in tree.getroot().iter() if x.tag==f'{{{ns}}}comp_output_clock' and x.get('name')=='i_sysclk']
assert len(matches)==1 and matches[0].get('out_divider') in ('9','12')
# Same PLL feedback/VCO and 100 MHz outputs; only CPU/accelerator output divider changes.
matches[0].set('out_divider','12')
tree.write(peri,encoding='utf-8',xml_declaration=True)
sdc=project/'sdc/ddr3.sdc'
text=sdc.read_bytes()
old=b'create_clock -period 3.333 -name i_sysclk [get_ports {i_sysclk}]'
new=b'create_clock -period 4.444 -name i_sysclk [get_ports {i_sysclk}]'
assert text.count(old)+text.count(new)==1
sdc.write_bytes(text.replace(old,new))
record={'i_sysclk_mhz':225,'previous_i_sysclk_mhz':300,
        'scope':'Sapphire CPU and TinyML accelerator; memory/peripheral/CLINT clocks remain 100 MHz',
        'pll_change':'i_sysclk output divider 9 -> 12; feedback and other divider values unchanged',
        'sdc_change':'i_sysclk period 3.333 -> 4.444 ns; no false/multicycle paths added',
        'ddr_phy_mhz':400,'physical_pin_changes':False,'board_tested':False}
(project/'CLOCK_PROFILE.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
