"""Adapt only the working copy for GCC 13; preserve vendor archives."""
from pathlib import Path
import hashlib
import json
import shutil

root=Path(__file__).resolve().parents[1]
work=root/'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/software/standalone'
source=root/'vendor_projects/TinyML/tinyml-main/tinyml_hello_world/Ti60F225_tinyml_helloworld/embedded_sw/sapphire_soc_tinyml/software/standalone'
app=work/'tinyml_pdti8'
tf_source=source/'tinyml_ypd/src/tensorflow'
tf_target=app/'src/tensorflow'
schema=Path('lite/schema/schema_generated.h')
assert hashlib.sha256((tf_source/schema).read_bytes()).digest() == hashlib.sha256((tf_target/schema).read_bytes()).digest(), 'TensorFlow schema versions differ'
restored_headers=[]
previous_record=app/'PREPARATION_RECORD.json'
if previous_record.exists():
    previous=json.loads(previous_record.read_text(encoding='utf-8'))
    restored_headers=previous.get('restored_headers',previous.get('restored_headers_this_run',[]))
for file in tf_source.rglob('*'):
    if file.is_file() and file.suffix.lower() in ('.h','.hpp','.inc'):
        relative=file.relative_to(tf_source)
        destination=tf_target/relative
        if not destination.exists():
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(file,destination)
            restored_headers.append(relative.as_posix())
dependency=app/'src/tensorflow/third_party/flatbuffers'
vendor_dependency=source/'tinyml_ypd/src/tensorflow/third_party/flatbuffers'
if not (dependency/'include/flatbuffers/flatbuffers.h').exists():
    if not (vendor_dependency/'include/flatbuffers/flatbuffers.h').is_file():
        raise FileNotFoundError('Matching vendor FlatBuffers headers missing')
    shutil.copytree(vendor_dependency,dependency,dirs_exist_ok=True)
makefile=app/'makefile'
content=makefile.read_bytes()
marker=b'# Local GCC 13 compatibility: C++ uses supplied Newlib headers; no OS startup is linked.'
if marker in content:
    content=content.split(marker)[0].rstrip()
# C++ requires the default hosted standard-library declarations, while the
# runtime remains bare metal through the vendor linker/startup/nosys settings.
makefile.write_bytes(content+b'\r\n'+marker+b'\r\nCXXFLAGS := $(filter-out -ffreestanding -fhosted,$(CXXFLAGS))\r\n')
mainfile=app/'src/main.cc'
main=mainfile.read_bytes()
if b'extern "C" void main()' in main:
    assert main.count(b'extern "C" void main()') == 1
    assert main.count(b'   ops_unload();') == 1
    main=main.replace(b'extern "C" void main()', b'extern "C" int main(void)')
    main=main.replace(b'   ops_unload();', b'   ops_unload();\r\n   return 0;')
    mainfile.write_bytes(main)
record={
    'vendor_archive_unmodified':True,
    'flatbuffers_source':str(vendor_dependency),
    'matching_tensorflow_schema_checked':True,
    'restored_headers':sorted(set(restored_headers)),
    'flatbuffers_sha256':hashlib.sha256((dependency/'include/flatbuffers/flatbuffers.h').read_bytes()).hexdigest(),
    'makefile_sha256':hashlib.sha256(makefile.read_bytes()).hexdigest(),
    'main_sha256':hashlib.sha256(mainfile.read_bytes()).hexdigest(),
    'changes':['Restore pdti8 FlatBuffers headers from ypd in the same supplied archive',
               'Filter -ffreestanding from CXXFLAGS for GCC 13 C++ standard-library availability; C retains freestanding flags; -fno-builtin, nosys, custom startup unchanged',
               'Use standard int main(void) and return 0; vendor bare-metal startup still loops after main returns'],
    'model_unchanged':True,'static_images_unchanged':True,'physical_inference_executed':False,
}
(app/'PREPARATION_RECORD.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
