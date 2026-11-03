"""Bind all 66 Gray-pointer bits, including merged binary/Gray MSB registers."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/07_soc_physical'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    net=P/'outflow/soc_physical.map.v';text=net.read_text(encoding='utf-8',errors='replace')
    ffs=set(re.findall(r'EFX_FF\s+\\(\S+)\s*\(',text))
    buses=[('soc/c2_full_video/ingress/crossing',7,5,10),
      ('soc/c2_full_video/framebuffer/output_cdc',7,10,1000/148.5),
      ('soc/c2_attachment/core/pixels/storage',5,5,10),('raw_split/queue',7,20,10),('gray_split/queue',7,10,5)]
    result={'status':'PASS','netlist_sha256':sha(net),'buses':[],'pointer_bits':0,
      'method':'Use mapped Gray FF; only the mathematically identical MSB may alias the mapped binary FF. No unbound patterns or ignored Gray bits.'}
    s='# Derived after synthesis. Covers Gray/binary MSB coalescing.\n'
    for hierarchy,width,wp,rp in buses:
      for ptr,binary,stage,period in [('wgray','wbin','wgray1',wp),('rgray','rbin','rgray1',rp)]:
        sources=[];destinations=[];aliases=[]
        for bit in range(width):
          src=f'{hierarchy}/{ptr}[{bit}]~FF';dst=f'{hierarchy}/{stage}[{bit}]~FF'
          if src not in ffs:
            if bit!=width-1:raise ValueError('Missing non-MSB Gray register '+src)
            alternate=f'{hierarchy}/{binary}[{bit}]~FF'
            if alternate not in ffs:raise ValueError('Missing Gray/binary MSB '+src)
            aliases.append({'logical_gray':src,'physical_ff':alternate});src=alternate
          if dst not in ffs:raise ValueError('Missing first synchronizer '+dst)
          sources.append(src);destinations.append(dst)
        sp=' '.join(x+'|CLK' for x in sources);dp=' '.join(x+'|D' for x in destinations)
        s+=f'set_bus_skew -from [get_pins {{{sp}}}] -to [get_pins {{{dp}}}] {period*0.8:.3f}\n'
        result['buses'].append({'hierarchy':hierarchy,'pointer':ptr,'bits':width,'source_clock_period_ns':period,'skew_limit_ns':round(period*0.8,3),'sources':sources,'destinations':destinations,'merged_MSB_aliases':aliases})
        result['pointer_bits']+=width
    if result['pointer_bits']!=66:raise ValueError('Incomplete Gray bus coverage')
    out=P/'soc_physical_cdc.sdc';out.write_text(s,encoding='utf-8',newline='\n')
    # Efinity suppresses report_bus_skew across set_clock_groups cuts. Inspect
    # the same routed design separately, without cuts; never use this view's
    # synchronous clock relationship slack as primary STA signoff.
    primary=(P/'soc_physical.sdc').read_text(encoding='utf-8')
    diagnostic='\n'.join(l for l in primary.splitlines() if not l.startswith('set_clock_groups '))+'\n'
    diag=P/'soc_physical_cdc_review.sdc';diag.write_text(diagnostic,encoding='utf-8',newline='\n')
    result['diagnostic_sdc_sha256']=sha(diag)
    result['constraint_sha256']=sha(out);result['generator_sha256']=sha(Path(__file__))
    (ROOT/'logs/soc_physical_cdc_binding.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS mapped CDC binding: 10 buses / 66 pointer bits including merged MSBs.')

if __name__=='__main__':main()
