"""Format compatibility only; all original acceptance failures must stay failures."""
from pathlib import Path
import json,re
from check_c9_uart import check
R=Path(__file__).resolve().parents[1]
def prefixed(text):
 return re.sub(r'\b(start_ms|end_ms|pair|bank|sequence|lo|hi)=([0-9a-f]+)\b',lambda m:m[1]+'=0x'+m[2],text)
def main():
 good=(R/'logs/ram_diagnostic_20261101/20261102_193055/uart.log').read_text()
 bad=(R/'logs/ram_diagnostic_20261101/20261102_183914/uart.log').read_text()
 tests=[]
 for name,text,want in [('original_hardware_pass',good,True),('synthetic_0x_format_only',prefixed(good),True),('original_hardware_missed_scan',bad,False),('same_error_with_0x',prefixed(bad),False),('malformed_hex',prefixed(good).replace('pair=0x00000001','pair=0xz',1),False)]:
  try:result=check(text,'dma');actual=result['status']=='PASS';error=''
  except Exception as exc:actual=False;error=str(exc)
  tests.append(dict(name=name,expected_pass=want,actual_pass=actual,error=error))
 status='PASS' if all(t['expected_pass']==t['actual_pass'] for t in tests) else 'FAIL'
 out=dict(status=status,scope='Host format fixtures plus original real PASS/FAIL logs; no new hardware evidence',tests=tests)
 (R/'build/c9_uart_hex_format_20261102.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
