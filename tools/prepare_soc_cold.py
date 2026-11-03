"""Derive full C7 + private SPI RX fix; preserve qualified original C7."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as E
from c7_spi_rx_override import patch
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'projects/07_soc_physical';P=ROOT/'projects/10_soc_cold'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parent=json.loads((ROOT/'fpga_bitstreams/soc_physical_100mhz/BUILD_RECORD.json').read_text())
 assert sha(BASE/'PHYSICAL_MANIFEST.json')==parent['source_manifest_sha256']
 if P.exists() and not (P/'COLD_MANIFEST.json').exists():raise ValueError('Unrelated project directory')
 P.mkdir(exist_ok=True)
 for src in BASE.rglob('*'):
  rel=src.relative_to(BASE)
  if not src.is_file() or any(x.startswith('work_') or x=='outflow' for x in rel.parts):continue
  dst=P/rel;dst.parent.mkdir(parents=True,exist_ok=True);data=src.read_bytes()
  if src.suffix in ['.v','.sv','.vh','.xml','.sdc','.json','.tcl']:data=data.replace(BASE.as_posix().encode(),P.as_posix().encode())
  dst.write_bytes(data)
 vendor=ROOT/'projects/03_tinyml/ip/sapphire_soc/sapphire_soc.v';override=P/'overrides/sapphire_soc_spi.v'
 override.write_text(patch(vendor.read_text()),encoding='utf-8',newline='\n')
 xml=P/'soc_physical.xml';tree=E.parse(xml);ns='http://www.efinixinc.com/enf_proj';E.register_namespace('efx',ns)
 found=0
 for e in tree.iter():
  if e.tag.endswith('}design_file') and e.get('name')==vendor.as_posix():e.set('name',override.as_posix());found+=1
 assert found==1,found
 E.indent(tree,space='    ');tree.write(xml,encoding='utf-8',xml_declaration=True)
 mf=json.loads((P/'PHYSICAL_MANIFEST.json').read_text());sources={k.replace('projects/07_soc_physical','projects/10_soc_cold'):v for k,v in mf['source_sha256'].items()}
 assert sources.pop(vendor.relative_to(ROOT).as_posix())==sha(vendor)
 sources[override.relative_to(ROOT).as_posix()]=sha(override)
 mf['source_sha256']={k:sha(ROOT/k) for k in sources};(P/'PHYSICAL_MANIFEST.json').write_text(json.dumps(mf,indent=2)+'\n')
 extra=dict(kind='Full C7 cold boot SPI receive correction',parent_image_sha256=parent['artifacts']['soc_physical.bit']['sha256'],parent_manifest_sha256=parent['source_manifest_sha256'],
  generator_sha256=sha(Path(__file__)),patcher_sha256=sha(ROOT/'tools/c7_spi_rx_override.py'),vendor_source_sha256=sha(vendor),source_sha256=mf['source_sha256'],
  scope='Full original C7 with one private SPI RX sampling correction; C3 sensors and all original peripherals retained',flash_written=False)
 (P/'COLD_MANIFEST.json').write_text(json.dumps(extra,indent=2)+'\n');print('Prepared C10: full C7 with private SPI RX correction')
if __name__=='__main__':main()
