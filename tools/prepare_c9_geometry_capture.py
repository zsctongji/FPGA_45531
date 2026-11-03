"""Freeze the unchanged USER2 capture protocol for the geometry-only build."""
from pathlib import Path
import hashlib
R=Path(__file__).resolve().parents[1]
B=R/'build/c9_display_fix_20261102';P=R/'build/c9_camera_geometry_image_20261102'
def expected():
 text=(B/'capture_display.py').read_text()
 old="synthesis_variant='cong_comb4_off_seed2_scanout_startup_fix'"
 assert text.count(old)==1
 return text.replace(old,"synthesis_variant='cong_comb4_off_seed2_scanout_geometry_observer'")
def main():
 path=P/'capture_geometry.py';text=expected()
 if path.exists():assert path.read_text()==text,'Preserve previous capture source'
 else:path.write_text(text,newline='\n')
 print('PREPARED geometry USER2 capture: '+hashlib.sha256(path.read_bytes()).hexdigest())
if __name__=='__main__':main()
