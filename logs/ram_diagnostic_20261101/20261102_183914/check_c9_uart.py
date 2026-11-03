"""Strict C9 UART evidence checking. Pattern DMA and real camera stay distinct."""
from pathlib import Path
import argparse,json,re,hashlib
ROOT=Path(__file__).resolve().parents[1]
def fnv(data):
 h=2166136261
 for b in data:h=((h^b)*16777619)&0xffffffff
 return h
def snapshots(text):
 result={};current=None;sequences=[]
 for line in text.splitlines():
  if line.startswith('C9|SNAP_BEGIN '):
   assert current is None,'Nested snapshot';label=re.search(r'label=(\w+)',line)[1]
   assert label not in result,'Duplicate snapshot label';current=dict(start=int(re.search(r'start_ms=([\da-f]+)',line)[1],16),banks={});result[label]=current
  elif line.startswith('C9|BANK '):
   assert current is not None,'BANK outside snapshot';v={k:int(s,16) for k,s in re.findall(r'(pair|bank|sequence|lo|hi)=([\da-f]+)',line)}
   key=(v['pair'],v['bank']);assert key not in current['banks'] and 0<=key[0]<4 and 0<=key[1]<5,'Duplicate/invalid pair'
   current['banks'][key]=[v['lo'],v['hi'],v['sequence']]
  elif line.startswith('C9|SNAP_END '):
   assert current is not None and 'pairs=4' in line,'Incomplete snapshot end'
   current['end']=int(re.search(r'end_ms=([\da-f]+)',line)[1],16)
   assert len(current['banks'])==20,'Incomplete five-domain snapshot'
   for pair in range(4):
    seq={current['banks'][(pair,b)][2] for b in range(5)};assert len(seq)==1,'Domains disagree on sequence';sequences.append(seq.pop())
   current['words']={b:[w for pair in range(4) for w in current['banks'][(pair,b)][:2]] for b in range(5)}
   del current['banks'];current=None
 assert current is None and set(result)=={'before','after'},'Missing before/after snapshots'
 assert len(set(sequences))==8 and all(((b-a)&0xffffffff)==1 for a,b in zip(sequences,sequences[1:])),'Snapshot sequence discontinuity'
 return result
def check(text,mode):
 assert not re.search(r'\|(?:FAIL|TRAP)\b|CRASH',text),'Firmware failure/trap'
 assert 'C9|MAP status=PASS independent_locations=6 words=24 source_off=1' in text,'DDR map not verified before RUN'
 snap=snapshots(text);before=snap['before']['words'];after=snap['after']['words']
 assert ((snap['after']['end']-snap['before']['start'])&0xffffffff)>0,'Shared time does not progress'
 assert after[0][2:4]==[0,0],'DDR video AXI errors'
 assert after[1][1:3]==[0,0],'Capture format/overflow errors'
 assert after[1][5]==0,'AI source fault'
 assert after[2][3:5]==[0,0],'Display underflow/missed scans'
 assert after[0][0]>=3 and after[2][2]>before[2][2],'Video publish/display scan did not progress'
 result=dict(status='PASS',mode=mode,snapshots=snap,physical_hdmi_picture_verified=False,flash_cold_boot_verified=False)
 if mode=='dma':
  assert 'C9|BOOT mode=coherence version=' in text and 'C9|DONE status=PASS mode=coherence version=' in text,'Missing DMA BOOT/DONE'
  assert 'C9|CACHE_NEGATIVE stale_words=00000010 omit_invalidate=OLD_DATA' in text,'Stale-cache negative missing'
  assert 'C9|CACHE_POSITIVE fresh_words=00000010 invalidate=FRESH_DATA' in text,'Cache invalidate positive missing'
  assert 'C9|OWNERSHIP status=PASS stale_token_rejected=1 leased_slot_preserved=1 other_slot=1' in text,'Lease protection missing'
  frames=[{k:int(v,16) for k,v in re.findall(r'(frame|generation|raw_fnv|seed)=([\da-f]+)',l)} for l in text.splitlines() if l.startswith('C9|FRAME status=PASS ')]
  assert len(frames)==2 and [f['seed'] for f in frames]==[0xc3,0x5a],'Pattern verification frames missing'
  for f in frames:assert f['raw_fnv']==fnv(bytes(0 if n<2016 or n>=7200 else f['seed'] for n in range(9216))),'Pattern checksum differs from host'
  assert after[1][6]==3 and after[1][7]&12==12,'Three actual pattern commands not observed'
  assert after[1][4]==0,'Unexpected pattern source rejection'
  result.update(dma_cache_handoff_verified=True,real_camera_verified=False,frames=frames)
 else:
  assert 'C9|SOURCE mode=camera synthetic=0 physical_hdmi_sink=0' in text,'Camera source not committed'
  assert 'C9|TIME status=PASS ' in text and 'C9|DONE mode=camera ' in text,'Incomplete camera test'
  assert after[3][4]&1 and after[4][1]==0 and after[1][7]&5==0,'Camera register readback/transport fault'
  sensor_bytes=b''.join(int(w).to_bytes(4,'little') for w in after[3][:4])
  sensor_id=(sensor_bytes[0]<<8)|sensor_bytes[1];width=(sensor_bytes[2]<<8)|sensor_bytes[3];height=(sensor_bytes[4]<<8)|sensor_bytes[5]
  assert sensor_id not in [0,65535] and (width,height)==(1920,1080),'Sensor ID/1920x1080 readback does not match the active video profile'
  assert after[1][7]&8 and after[1][6]==0,'Camera run/pattern isolation failure'
  frames=[]
  for l in text.splitlines():
   if l.startswith('C24|FRAME '):
    v=dict(re.findall(r'(\w+)=(-?[\da-f]+)',l));frames.append(v)
  assert len(frames)>=12,'Fewer than 12 camera frame results'
  good=[f for f in frames if f['status']=='0' and f['valid']=='1'];assert len(good)>=6,'Fewer than six fresh camera inferences'
  result.update(real_camera_verified=True,valid_inferences=len(good),sensor_id_hex='%04x'%sensor_id,sensor_width=width,sensor_height=height,frames=frames,dma_cache_handoff_verified=False)
 return result
def main():
 ap=argparse.ArgumentParser();ap.add_argument('log',type=Path);ap.add_argument('--mode',choices=['dma','camera'],required=True);ap.add_argument('--output',type=Path);a=ap.parse_args()
 text=a.log.read_text(errors='replace')
 try:
  result=check(text,a.mode)
  frozen=a.log.parent/'firmware_build_record.json';attempt=a.log.parent/'attempt.json'
  assert frozen.is_file() and attempt.is_file(),'Missing captured firmware/attempt provenance'
  meta=json.loads(attempt.read_text());build=json.loads(frozen.read_text())
  assert hashlib.sha256(frozen.read_bytes()).hexdigest()==meta['build_record_sha256'],'Captured build manifest identity changed'
  assert meta['status']=='CAPTURED_DONE_REQUIRES_CHECKER' and meta['readback_sha256']==meta['firmware_sha256'],'Firmware was not fully verified before execution'
  assert meta['fpga_configured'] and meta['flash_written'] is False,'Missing isolated FPGA configuration provenance'
  assert build['version']==meta['firmware_version'] and 'version='+build['version'] in text,'Firmware version missing from UART'
  result['firmware_version']=build['version'];result['firmware_sha256']=meta['firmware_sha256'];result['fpga_image_sha256']=meta['fpga_image_sha256']
 except Exception as exc:result=dict(status='FAIL',mode=a.mode,error=str(exc),real_camera_verified=False,dma_cache_handoff_verified=False)
 result['uart_sha256']=hashlib.sha256(a.log.read_bytes()).hexdigest()
 if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2));return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
