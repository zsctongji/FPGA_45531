"""Actual local CPU inference plus C4 frame transport/preprocessing replay.
No board, camera acquisition, external upload, or physical sensor access."""
import argparse,ctypes as ct,json,sys,time,struct,platform,importlib.metadata
from pathlib import Path
from pc_model_data import ROOT,SAMPLES,array,tensor_bytes,fnv,sha
sys.path.insert(0,str(ROOT/"build/pc_ai_packages"))
import numpy as np
from ai_edge_litert.interpreter import Interpreter,OpResolverType
U=ct.c_uint32; I=ct.c_int32; P=ct.c_void_p
class Frame(ct.Structure): _fields_=[("words",U*16)]
class Slot(ct.Structure): _fields_=[("state",U),("generation",U),("frame",Frame)]
class Pool(ct.Structure): _fields_=[("slots",Slot*2),("dropped",U)]
class Consumer(ct.Structure): _fields_=[("last",U),("have_last",U),("accepted",U),("rejected",U)]
class Result(ct.Structure):
    _fields_=[("status",I),("valid",U),("frame_id",U),("timestamp_ms",U),
              ("raw_fnv",U),("tensor_fnv",U),("person",I),("no_person",I),("predicted",I)]
CB=ct.CFUNCTYPE(ct.c_int,P,P,U,P)
def buffer(data): return (ct.c_uint8*len(data)).from_buffer_copy(data)
def floatscale_bits(value): return format(struct.unpack("<I",struct.pack("<f",value))[0],"x")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--gray",type=Path,help="Additional recorded RAW GRAY8 input (not live acquisition)")
    ap.add_argument("--height",type=int,choices=[54,96],default=96)
    a=ap.parse_args()
    output=ROOT/"logs/pc_ai"; output.mkdir(parents=True,exist_ok=True)
    model=array("mobilenetv1_person_detect_model_data")
    manifest=json.loads((ROOT/"firmware/c1_static_person_detect/C1_INPUT_MANIFEST.json").read_text(encoding="utf-8"))
    if sha(model)!=manifest["model_sha256"]: raise ValueError("Model identity mismatch")
    from pc_model_compat import desktop_compat
    runtime_model,compatibility=desktop_compat(model)
    work=ROOT/"build/pc_ai"; work.mkdir(parents=True,exist_ok=True)
    (work/"person_desktop_compat.tflite").write_bytes(runtime_model)
    (output/"model_compatibility.json").write_text(json.dumps(compatibility,indent=2),encoding="utf-8")
    interpreter=Interpreter(model_content=runtime_model,num_threads=1,
                            experimental_op_resolver_type=OpResolverType.BUILTIN_REF)
    interpreter.allocate_tensors()
    inp=interpreter.get_input_details()[0]; out=interpreter.get_output_details()[0]
    for detail,kind in [(inp,"input"),(out,"output")]:
        expected=manifest["model_contract"][kind]
        if detail["dtype"]!=np.int8 or detail["shape"].tolist()!=expected["shape"] or \
           floatscale_bits(detail["quantization"][0])!=expected["scale_bits"] or detail["quantization"][1]!=expected["zero"]:
            raise ValueError("Runtime tensor contract mismatch: "+kind)
    def invoke(data):
        value=np.frombuffer(data,dtype=np.int8).reshape(1,96,96,1).copy()
        interpreter.set_tensor(inp["index"],value)
        start=time.perf_counter_ns(); interpreter.invoke(); elapsed=time.perf_counter_ns()-start
        scores=interpreter.get_tensor(out["index"]).reshape(-1).tolist()
        return scores,elapsed
    reference=[]
    raw_images=[]
    for idx,(name,symbol,pre,expected) in enumerate(SAMPLES):
        source=array(symbol); tensor=tensor_bytes(source,pre)
        if len(source)!=9216 or sha(tensor)!=manifest["samples"][idx]["tensor_sha256"]:
            raise ValueError("Static input mismatch")
        scores,elapsed=invoke(tensor)
        again,_=invoke(tensor)
        if scores!=again: raise ValueError("Repeated reference inference differs")
        predicted=1 if scores[1]>scores[0] else (0 if scores[0]>scores[1] else -1)
        reference.append({"sample":name,"tensor_sha256":sha(tensor),"input_fnv":format(fnv(tensor),"x"),
                          "no_person":scores[0],"person":scores[1],"predicted":predicted,"expected":expected,
                          "host_invoke_ns":elapsed})
        raw=bytes(b^128 for b in tensor) # inverse of the vendor pixel-128 byte mapping
        raw_images.append((name,raw))
    golden={"status":"PASS","scope":"Actual PC CPU reference inference with audited metadata compatibility copy; not FPGA execution or accuracy evaluation",
            "runtime":"ai-edge-litert","runtime_version":importlib.metadata.version("ai-edge-litert"),
            "resolver":"BUILTIN_REF","num_threads":1,"numpy_version":np.__version__,
            "python":platform.python_version(),"model_sha256":sha(model),"runtime_model_sha256":sha(runtime_model),
            "compatibility":compatibility,"c1_version":manifest["version"],
            "samples":reference,"static_label_matches":sum(r["predicted"]==r["expected"] for r in reference),
            "board_compared":False}
    (output/"c1_reference.json").write_text(json.dumps(golden,indent=2),encoding="utf-8")
    dll_path=ROOT/"build/c4/c4_bridge.dll"
    lib=ct.CDLL(str(dll_path))
    lib.c4_frame_size.restype=U; lib.c4_pool_size.restype=U
    if lib.c4_frame_size()!=ct.sizeof(Frame) or lib.c4_pool_size()!=ct.sizeof(Pool): raise ValueError("ctypes ABI mismatch")
    lib.c4_pool_reset.argtypes=[ct.POINTER(Pool)]
    lib.c4_publish_gray_reference.argtypes=[ct.POINTER(Pool),P,U,P,U,U,U,ct.POINTER(U),ct.POINTER(U)]
    lib.c4_pad_gray54.argtypes=[P,U,P,U]
    lib.c4_process.argtypes=[ct.POINTER(Consumer),ct.POINTER(Pool),U,U,P,U,U,P,U,CB,P,ct.POINTER(Result)]
    memory=(ct.c_uint8*65536)(); tensor=(ct.c_int8*9216)(); pool=Pool(); consumer=Consumer()
    lib.c4_pool_reset(ct.byref(pool))
    callback_errors=[]
    @CB
    def callback(context,ptr,n,scores_ptr):
        try:
            scores,_=invoke(ct.string_at(ptr,n))
            destination=ct.cast(scores_ptr,ct.POINTER(ct.c_int8))
            destination[0],destination[1]=scores
            return 0
        except Exception as exc:
            callback_errors.append(str(exc)); return -7
    rows=[]; sequence=0
    def replay(name,raw,source_kind):
        nonlocal sequence
        source=buffer(raw); slot=U(); gen=U(); result=Result()
        sequence+=1; timestamp=sequence*100
        status=lib.c4_publish_gray_reference(ct.byref(pool),memory,65536,source,9216,sequence,timestamp,ct.byref(slot),ct.byref(gen))
        if status: raise ValueError("Publish failed "+str(status))
        raw_before=bytes(memory)
        status=lib.c4_process(ct.byref(consumer),ct.byref(pool),slot.value,gen.value,memory,65536,timestamp+10,
                              tensor,9216,callback,None,ct.byref(result))
        if status or not result.valid: raise ValueError("C4 processing failed "+str(status)+str(callback_errors))
        if bytes(memory)!=raw_before or pool.slots[slot.value].state!=0: raise ValueError("Raw frame mutated or slot leaked")
        expected_tensor=tensor_bytes(raw,False)
        if bytes(tensor)!=expected_tensor or result.raw_fnv!=fnv(raw) or result.tensor_fnv!=fnv(expected_tensor):
            raise ValueError("C/Python preprocessing mismatch")
        direct,_=invoke(expected_tensor)
        if [result.no_person,result.person]!=direct: raise ValueError("Bridge/direct inference mismatch")
        rows.append({"case":name,"source_kind":source_kind,"frame_id":sequence,
                     "raw_fnv":format(result.raw_fnv,"x"),"tensor_fnv":format(result.tensor_fnv,"x"),
                     "no_person":result.no_person,"person":result.person,"predicted":result.predicted,
                     "bridge_equals_direct":True,"slot_released":True,"raw_preserved":True})
    for name,raw in raw_images:
        replay(name+"_full",raw,"vendor_static_reconstructed_GRAY8")
        source=np.frombuffer(raw,dtype=np.uint8).reshape(96,96)
        small_array=source[(np.arange(54)*96//54),:].copy()
        small=small_array.tobytes()
        padded=(ct.c_uint8*9216)()
        if lib.c4_pad_gray54(buffer(small),len(small),padded,9216): raise ValueError("Pad failed")
        expected=bytes(21*96)+small+bytes(21*96)
        if bytes(padded)!=expected: raise ValueError("Padding mismatch")
        replay(name+"_padded",expected,"vendor_static_resampled96x54_then_padded")
        stretch=small_array[(np.arange(96)*54//96),:].copy().tobytes()
        replay(name+"_stretch",stretch,"offline_policy_comparison_vertical_nearest_resize")
        crop=small_array[:,21:75]
        sample_axis=np.arange(96)*54//96
        crop=crop[sample_axis[:,None],sample_axis[None,:]].copy().tobytes()
        replay(name+"_crop",crop,"offline_policy_comparison_center54x54_nearest_resize")
    if a.gray:
        raw=a.gray.read_bytes()
        if len(raw)!=96*a.height: raise ValueError("Recorded input length mismatch")
        if a.height==54: raw=bytes(21*96)+raw+bytes(21*96)
        replay(a.gray.name,raw,"user_recorded_GRAY8_unverified_source")
    policies=[]
    for name,_,_,expected_class in SAMPLES:
        entries={policy:next(r for r in rows if r['case']==name+'_'+policy) for policy in ['full','padded','stretch','crop']}
        policies.append({"sample":name,"original_static_expected":expected_class,
                         "scores":{p:{"person":r['person'],"predicted":r['predicted']} for p,r in entries.items()},
                         "policies_differing_from_full":[p for p,r in entries.items() if r['predicted']!=entries['full']['predicted']]})
    (output/"preprocess_policy.json").write_text(json.dumps({"scope":"Six static sample policy comparison, not camera accuracy",
         "policies":policies,"camera_policy_approved":False},indent=2),encoding="utf-8")
    report={"status":"PASS","scope":"Host serialized C4 replay with real PC model inference; no DMA/CDC or live camera",
            "model_sha256":sha(model),"runtime_model_sha256":sha(runtime_model),
            "native_dll_sha256":sha(dll_path.read_bytes()),
            "cases":rows,"accepted":consumer.accepted,"board_inference_passed":False,
            "camera_preprocess_quality_validated":False,
            "padding_class_changes":[p['sample'] for p in policies if 'padded' in p['policies_differing_from_full']]}
    (output/"c4_replay.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"status":"PASS","reference_samples":len(reference),"static_label_matches":golden["static_label_matches"],
                      "c4_real_inference_replays":len(rows),"model_sha256":sha(model)}))
if __name__=="__main__":
    try: main()
    except Exception as exc:
        error={"status":"FAIL","scope":"PC inference/replay only","error":str(exc),"board_inference_passed":False}
        out=ROOT/"logs/pc_ai"; out.mkdir(parents=True,exist_ok=True)
        (out/"c4_replay.json").write_text(json.dumps(error,indent=2),encoding="utf-8")
        print(json.dumps(error)); raise SystemExit(1)

