"""Verify a locally captured final camera frame against the desktop model.
Raw camera buffers stay private; this tool publishes only hashes and scores.
"""
from pathlib import Path
import argparse,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build/pc_ai_packages'))
import numpy as np
from ai_edge_litert.interpreter import Interpreter,OpResolverType
from pc_model_data import array,fnv
from pc_model_compat import desktop_compat
sha=lambda data:hashlib.sha256(data).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('attempt',type=Path);a=ap.parse_args();out=a.attempt
 result=dict(status='FAIL',raw_camera_buffers_uploaded=False)
 try:
  meta=json.loads((out/'attempt.json').read_text());inputs=meta['private_inputs']
  raw=Path(inputs['gray']['path']).read_bytes();tensor=Path(inputs['tensor']['path']).read_bytes()
  assert len(raw)==len(tensor)==9216
  assert sha(raw)==inputs['gray']['sha256'] and sha(tensor)==inputs['tensor']['sha256'],'Private dump hash mismatch'
  text=(out/'uart.log').read_text(errors='replace');frames=[dict(re.findall(r'(\w+)=(-?(?:0x)?[\da-f]+)\b',l)) for l in text.splitlines() if l.startswith('C24|FRAME ')]
  assert frames,'No camera records';last=frames[-1]
  assert last['status']=='0' and last['valid']=='1','Last copied frame did not produce a valid inference'
  assert fnv(raw)==int(last['raw_fnv'],16) and fnv(tensor)==int(last['tensor_fnv'],16),'Private copy does not match logged frame'
  assert tensor==bytes(b^128 for b in raw),'GRAY8 to INT8 transformation differs'
  model=array('mobilenetv1_person_detect_model_data');manifest=json.loads((ROOT/'firmware/c1_static_person_detect/C1_INPUT_MANIFEST.json').read_text())
  assert sha(model)==manifest['model_sha256'],'Pinned model identity differs'
  runtime,compatibility=desktop_compat(model)
  interpreter=Interpreter(model_content=runtime,num_threads=1,experimental_op_resolver_type=OpResolverType.BUILTIN_REF);interpreter.allocate_tensors()
  inp=interpreter.get_input_details()[0];output=interpreter.get_output_details()[0]
  interpreter.set_tensor(inp['index'],np.frombuffer(tensor,dtype=np.int8).reshape(inp['shape']));interpreter.invoke();scores=interpreter.get_tensor(output['index']).reshape(-1).tolist()
  board=[int(last['no_person']),int(last['person'])];assert scores==board,'Raw INT8 scores differ: desktop=%s board=%s'%(scores,board)
  result.update(status='PASS_REAL_CAMERA_PRIVATE_COPY_AND_REFERENCE',frame_id=int(last['frame_id']),gray_sha256=sha(raw),tensor_sha256=sha(tensor),desktop_scores=scores,board_scores=board,source_model_sha256=sha(model),runtime_model_sha256=sha(runtime),compatibility=compatibility)
 except Exception as exc:result['error']=str(exc)
 (out/'camera_reference_check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['status'].startswith('PASS') else 1
if __name__=='__main__':raise SystemExit(main())
