"""Compare actual simulated DDR bytes with C24 self-test and PC model inputs."""
from pathlib import Path
import argparse,json,sys,time
from pc_model_data import ROOT,array,fnv,sha
sys.path.insert(0,str(ROOT/'build/pc_ai_packages'))
import numpy as np
from ai_edge_litert.interpreter import Interpreter,OpResolverType
from pc_model_compat import desktop_compat

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--video-capture',action='store_true');args=parser.parse_args()
    record={'status':'RUNNING','source':'synthetic full GRAY8/VS/DE -> pinned A capture -> C2 DDR readback' if args.video_capture else 'synthetic A mailbox -> C2 DDR readback',
            'board_inference_passed':False,'live_camera':False,'policy_approved':False}
    report='logs/a_c2_video_pc_inference.json' if args.video_capture else 'logs/a_c2_pc_inference.json'
    try:
        path=ROOT/('build/c2/a_c2_video_frame0.gray' if args.video_capture else 'build/c2/a_c2_frame1.gray');raw=path.read_bytes()
        if args.video_capture:
            tests_path=ROOT/'logs/c2_selftest.json';tests=json.loads(tests_path.read_text(encoding='utf-8-sig'))
            cases=[t for t in tests['tests'] if t['name'].startswith('tb_c2_video_') and not t['name'].startswith('tb_c2_video_config')]
            if tests['status']!='PASS' or len(cases)!=3 or any(t['status']!='PASS' for t in cases):
                raise ValueError('Require the current three full-source-pixel regression cases, including 1080p')
            if not any(t['parameters'].get('EXTENDED')==0 for t in cases):raise ValueError('Full-HD capture case missing')
            meta_path=ROOT/'build/c2/a_c2_video_frame0.json';meta=json.loads(meta_path.read_text())
            if not meta['synthetic'] or meta['source']!='GRAY8_VS_DE_simulation' or meta['timestamp_origin']!='first_source_DE':
                raise ValueError('Source metadata scope/first-DE timestamp origin mismatch')
            if meta['source_frame_id']!=0 or meta['timestamp_ms']==meta['grid_sof_observed_ms']:
                raise ValueError('First-DE edge test did not distinguish grid SOF time')
            if f'{fnv(raw):08x}'!=meta['raw_fnv']:raise ValueError('Capture metadata image identity mismatch')
            record.update(capture_metadata=meta,capture_metadata_sha256=sha(meta_path.read_bytes()),
                          rtl_report_sha256=sha(tests_path.read_bytes()),
                          source_sha256=sha(Path(__file__).read_bytes()),
                          full_source_cases=[t['name'] for t in cases])
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
    (ROOT/report).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return 0 if record['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
