"""Repair optional debug metadata in working projects, preserving physical pins."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
ns='http://www.efinixinc.com/enf_proj'
ET.register_namespace('efx',ns)
ET.register_namespace('xsi','http://www.w3.org/2001/XMLSchema-instance')
camera=root/'projects/04_camera_preprocess/ti60f225_oob.xml'
tree=ET.parse(camera)
debugger=tree.getroot().find(f'{{{ns}}}debugger')
for parameter in debugger.findall(f'{{{ns}}}param'):
    if parameter.get('name') == 'auto_instantiation':
        parameter.set('value','off')
tree.write(camera,encoding='utf-8',xml_declaration=True)
# This project already instantiates the supplied debug_edb_top RTL; automatic
# post-map insertion would require another, absent work_dbg/debug_top.v.

tinyml=root/'projects/03_tinyml'
peri=tinyml/'Ti60F225_tinyml_helloworld.peri.xml'
tree=ET.parse(peri)
peri_ns=tree.getroot().tag.partition('}')[0].lstrip('{')
ET.register_namespace('efxpt',peri_ns)
removed=0
for parent in tree.getroot().iter():
    for child in list(parent):
        if child.tag == f'{{{peri_ns}}}jtag' and child.get('name') == 'jtag_inst2':
            parent.remove(child)
            removed+=1
assert removed == 1
tree.write(peri,encoding='utf-8',xml_declaration=True)
top=tinyml/'src/tinyml_soc_top.v'
data=top.read_bytes()
data,count=re.subn(rb'^\s*(?:input|output)\s+(?:wire\s+)?jtag_inst2_\w+\s*,[^\r\n]*(?:\r?\n)',b'',data,flags=re.M)
assert count == 11
top.write_bytes(data)
record={'camera_auto_logic_analyzer_insertion':'off; existing explicit debug RTL retained',
        'tinyml_removed_unused_internal_user_jtag':'jtag_inst2 / JTAG_USER2',
        'tinyml_sapphire_debug_tap_retained':'jtag_inst1 / JTAG_USER1',
        'external_pin_assignments_changed':False,'physical_board_tested':False,
        'tinyml_peripheral_sha256':hashlib.sha256(peri.read_bytes()).hexdigest(),
        'tinyml_top_sha256':hashlib.sha256(top.read_bytes()).hexdigest()}
(root/'logs/release_project_repairs.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
