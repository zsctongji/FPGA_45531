"""Synthesis-only harness, no board pinout or programming claim."""
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
target=root/'projects/06_a_units'
target.mkdir(parents=True,exist_ok=True)
ns='http://www.efinixinc.com/enf_proj'
q=lambda s:'{'+ns+'}'+s
tree=ET.parse(root/'projects/05_camera_motion/ti60f225_oob.xml')
project=tree.getroot();project.set('name','a_side_units')
project.set('description','A-side synthesis-only unit harness; no board interface or bitstream')
design=project.find(q('design_info'))
for child in list(design):design.remove(child)
ET.SubElement(design,q('top_module'),name='a_side_units')
for file in ['a_side_units.v','ai_frame_mailbox.v','video_a_capture.v','video_grid_sampler.v','video_status_overlay.v']:
    ET.SubElement(design,q('design_file'),name='rtl/'+file,version='default',library='default')
    (target/'rtl').mkdir(exist_ok=True)
    shutil.copy2(root/'rtl'/file,target/'rtl'/file)
shutil.copy2(root/'rtl/osd_font5x7.vh',target/'rtl/osd_font5x7.vh')
shutil.copy2(root/'rtl/osd_font5x7.vh',target/'osd_font5x7.vh')
for tag in ['top_vhdl_arch','msg_config','partition_definitions','partition_interface_assignments']:
    ET.SubElement(design,q(tag),name='')
# Remove original board timing, peripheral and debugger assets from this harness.
for tag in ['interface_info','constraint_info']:
    for child in project.find(q(tag)):child.set('name','')
for child in project.find(q('debugger')):
    if child.get('name')=='profile':child.set('value','')
ET.register_namespace('efx',ns)
tree.write(target/'a_side_units.xml',encoding='utf-8',xml_declaration=True)
print(target/'a_side_units.xml')
