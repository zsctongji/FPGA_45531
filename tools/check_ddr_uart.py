"""Validate one saved DDR diagnostic attempt; never opens a serial port."""
from pathlib import Path
import argparse,json,re,hashlib
LINE=re.compile(r'DDR\|S=([0-9A-F]{2}) L=([0-3]) C=([01]) I=([0-9A-F]{2}) E=([0-9A-F]{2}) A=([0-9A-F]{8}) N=([0-9A-F]{8}) P=([0-9A-F]{8})')
EXPECTED=25+4*16777216
def validate(text):
 rows=[];problems=[]
 for line in text.splitlines():
  if 'DDR|' not in line:continue
  m=LINE.fullmatch(line[line.index('DDR|'):])
  if not m:problems.append('Malformed/truncated DDR record');continue
  row=dict(zip(['status','locks','cal','init','error','address','checked','progress'],[int(v,16) for v in m.groups()]));rows.append(row)
  if row['status'] not in [0,1,2,3,6,0xe0,0xf0,0xf1]:problems.append('Unknown diagnostic status')
  if row['status'] in [0xe0,0xf0,0xf1] or row['error']:problems.append('Diagnostic failure/timeout')
  if row['checked']>EXPECTED:problems.append('Unexpected test count/profile')
 good=[r for r in rows if r['status']==6 and r['locks']==3 and r['cal']==1 and r['error']==0 and r['checked']==EXPECTED]
 if len(good)<2:problems.append('Two full-capacity PASS records required')
 if rows and rows[-1] not in good:problems.append('Last record is not a complete PASS')
 return {'status':'PASS_LOG' if not problems else 'FAIL_LOG','records':len(rows),'complete_pass_records':len(good),'expected_checked_words':EXPECTED,'problems':sorted(set(problems)),'last':rows[-1] if rows else None,'scope':'Saved UART content only; bind actual bitstream SHA256 and board identity separately'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('log',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();data=a.log.read_bytes()
 result=validate(data.decode('utf-8-sig',errors='replace'));result['log_sha256']=hashlib.sha256(data).hexdigest()
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='PASS_LOG' else 1
if __name__=='__main__':raise SystemExit(main())
