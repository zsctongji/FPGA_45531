"""Compare actual simulated DDR bytes with C24 self-test and PC model inputs."""
from pathlib import Path
import json,sys,time
from pc_model_data import ROOT,array,fnv,sha
sys.path.insert(0,str(ROOT/'build/pc_ai_packages'))
import numpy as np
from ai_edge_litert.interpreter import Interpreter,OpResolverType
from pc_model_compat import desktop_compat

def main():
    record={'status':'RUNNING','source':'synthetic A mailbox -> C2 DDR readback',
            'board_inference_passed':False,'live_camera':False,'policy_approved':False}
    try:
        path=ROOT/'build/c2/a_c2_frame1.gray';raw=path.read_bytes()
        expected=bytes(0 if n<2016 or n>=7200 else ((n-2016)*17+1)&255 for n in range(9216))
        if raw!=expected:raise ValueError('A -> C2 DDR readback differs from generated source pattern')
        firmware=json.loads((ROOT/'firmware/c24_frame_person_detect/C24_INPUT_MANIFEST.json').read_text())
        if sha(raw)!=firmware['selftest_sha256'] or f'{fnv(raw):08x}'!=firmware['selftest_raw_fnv']:
            raise ValueError('Firmware self-test and real simulated DDR bytes are different')
        original=array('mobilenetv1_person_detect_model_data');model,compat=desktop_compat(original)
        if sha(original)!=firmware['model_sha256']:raise ValueError('Model identity changed')
        engine=Interpreter(model_content=model,num_threads=1,experimental_op_resolver_type=OpResolverType.BUILTIN_REF)
        engine.allocate_tensors();inp=engine.get_input_details()[0];out=engine.get_output_details()[0]
        tensor=bytes((v-128)&255 for v in raw)
        results=[]
        for candidate in [raw,expected]:
            values=np.array([v-128 for v in candidate],dtype=np.int8).reshape(1,96,96,1)
            engine.set_tensor(inp['index'],values);start=time.perf_counter_ns();engine.invoke()
            results.append(engine.get_tensor(out['index']).reshape(-1).tolist())
        if results[0]!=results[1]:raise ValueError('Transport and direct reference inference differ')
        if out['quantization']!=(1/256,-128):raise ValueError('Pinned display score mapping no longer applies')
        record.update(status='PASS',bytes=len(raw),raw_fnv=f'{fnv(raw):08x}',raw_sha256=sha(raw),
                      tensor_fnv=f'{fnv(tensor):08x}',tensor_sha256=sha(tensor),
                      no_person=results[0][0],person=results[0][1],person_u8=results[0][1]+128,
                      exact_transport_equals_reference=True,firmware_selftest_input_equal=True,
                      model_compatibility=compat,desktop_only=True)
        print(json.dumps({k:v for k,v in record.items() if k!='model_compatibility'}))
    except Exception as exc:record.update(status='FAIL',error=str(exc));print(str(exc))
    (ROOT/'logs/a_c2_pc_inference.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return 0 if record['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
