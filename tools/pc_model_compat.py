"""Audited desktop-only metadata compatibility copy.
Original model and board firmware are never modified. This is NOT a claim of
measured equivalence to the vendor's RISC-V/TinyML execution."""
import struct
from pc_model_data import sha
def desktop_compat(model_bytes):
    from ai_edge_litert import schema_py_generated as schema
    source=schema.Model.GetRootAsModel(model_bytes,0)
    graph=source.Subgraphs(0)
    bad=[]
    for i in range(graph.TensorsLength()):
        tensor=graph.Tensors(i); q=tensor.Quantization()
        if q and q.QuantizedDimension()>=tensor.ShapeLength():
            if tensor.ShapeLength()!=1 or tensor.Type()!=schema.TensorType.INT32 or \
               q.QuantizedDimension()!=3 or q.ScaleLength()!=tensor.Shape(0):
                raise ValueError("Unrecognized quantization problem at tensor "+str(i))
            # Every consumer of this tensor must use it only as convolution bias.
            users=[]
            for j in range(graph.OperatorsLength()):
                op=graph.Operators(j)
                opcode=source.OperatorCodes(op.OpcodeIndex())
                code=max(opcode.BuiltinCode(),opcode.DeprecatedBuiltinCode())
                for k in range(op.InputsLength()):
                    if op.Inputs(k)==i: users.append((code,k))
            if not users or any(k!=2 or code not in (schema.BuiltinOperator.CONV_2D,schema.BuiltinOperator.DEPTHWISE_CONV_2D) for code,k in users):
                raise ValueError("Invalid dimension is not confined to convolution bias")
            field=q._tab.Offset(16)
            if not field: raise ValueError("Missing explicit quantized_dimension")
            bad.append({"tensor":i,"name":tensor.Name().decode(),
                        "offset":q._tab.Pos+field,"before":3,"after":0})
    if [x["tensor"] for x in bad]!=[33,36,40,44,48,52,56,60,64,68,72,76,80,84]:
        raise ValueError("Unexpected metadata patch set; manual inspection required")
    patched=bytearray(model_bytes)
    for item in bad: struct.pack_into("<i",patched,item["offset"],0)
    patched=bytes(patched)
    result=schema.Model.GetRootAsModel(patched,0)
    if source.BuffersLength()!=result.BuffersLength(): raise ValueError("Buffer count changed")
    for i in range(source.BuffersLength()):
        a,b=source.Buffers(i),result.Buffers(i)
        da=bytes(a.DataAsNumpy()) if a.DataLength() else b""
        db=bytes(b.DataAsNumpy()) if b.DataLength() else b""
        if da!=db: raise ValueError("Model data changed")
    for i in range(graph.TensorsLength()):
        old=graph.Tensors(i); new=result.Subgraphs(0).Tensors(i)
        if old.Type()!=new.Type() or old.ShapeAsNumpy().tolist()!=new.ShapeAsNumpy().tolist() or old.Buffer()!=new.Buffer():
            raise ValueError("Tensor changed")
        qo,qn=old.Quantization(),new.Quantization()
        if qo and qn:
            for method in ["ScaleAsNumpy","ZeroPointAsNumpy"]:
                va,vb=getattr(qo,method)(),getattr(qn,method)()
                if hasattr(va,"tolist"): va=va.tolist()
                if hasattr(vb,"tolist"): vb=vb.tolist()
                if va!=vb: raise ValueError("Quantization values changed")
            expected=0 if i in [x["tensor"] for x in bad] else qo.QuantizedDimension()
            if qn.QuantizedDimension()!=expected: raise ValueError("Unexpected shared quantization edit")
    return patched,{"source_model_sha256":sha(model_bytes),"runtime_model_sha256":sha(patched),
                    "transform":"desktop_only_bias_quantized_dimension_3_to_0",
                    "patches":bad,"all_model_data_buffers_unchanged":True,
                    "board_model_modified":False,"board_equivalence_measured":False}

