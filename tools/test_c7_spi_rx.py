"""Actual generated SPI engine, raw red case and buffered green case."""
from pathlib import Path
import subprocess,re,json,hashlib
from c7_spi_rx_override import patch,MODULE
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=ROOT/'build/c7_spi_rx_tests';out.mkdir(exist_ok=True)
 src=ROOT/'projects/03_tinyml/ip/sapphire_soc/sapphire_soc.v';tb=ROOT/'team_work/03_ai_soc/c7_spi/sim/tb_spi_receive.sv'
 text=src.read_text();cases=[]
 for divider in [2,8,32]:
  for name,payload in [('raw',text),('buffered',patch(text))]:
   module=re.search(r'module '+MODULE+r' \(.*?\nendmodule',payload,re.S).group()
   p=out/(name+'.v');p.write_text(module+'\n');v=out/(name+'.vvp')
   subprocess.run([str(ROOT/'tools/iverilog/bin/iverilog.exe'),'-g2012','-s','tb_spi_receive','-Ptb_spi_receive.FIXED='+str(int(name=='buffered')),'-Ptb_spi_receive.DIVIDER='+str(divider),'-o',str(v),str(tb),str(p)],check=True,capture_output=True)
   z=subprocess.run([str(ROOT/'tools/iverilog/bin/vvp.exe'),str(v)],capture_output=True,text=True);print(z.stdout.splitlines()[0]);cases.append(dict(case=name,divider=divider,returncode=z.returncode,output=z.stdout));assert z.returncode==0
 paths=[src,tb,ROOT/'tools/c7_spi_rx_override.py',Path(__file__)]
 record=dict(status='PASS',cases=cases,source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths})
 (ROOT/'logs/c7_spi_rx_tests.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
