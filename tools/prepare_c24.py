"""Separate linked C2/C4 app; preserve C1 and the original vendor app."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
STANDALONE=ROOT/'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/software/standalone'
SOURCE=STANDALONE/'tinyml_pdti8';TARGET=STANDALONE/'tinyml_c24'

def fnv(data):
    h=2166136261
    for b in data:h=((h^b)*16777619)&0xffffffff
    return h

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--enable-live',action='store_true')
    parser.add_argument('--verified-map',action='store_true');parser.add_argument('--verified-shared-time',action='store_true')
    parser.add_argument('--shared-base',type=lambda s:int(s,0),default=0x09010000);args=parser.parse_args()
    if args.enable_live and not(args.verified_map and args.verified_shared_time):
        raise ValueError('Live build requires explicit verified mapping AND shared time; default build touches no C2 MMIO.')
    if args.shared_base&0xffff or not 0<=args.shared_base<=0xfffe0000:raise ValueError('Invalid shared base')
    if TARGET.exists() and not (TARGET/'C24_PREPARATION.json').exists():raise ValueError('Unrelated app exists')
    if not TARGET.exists():shutil.copytree(SOURCE,TARGET,ignore=shutil.ignore_patterns('build','build_ours','.settings'))
    else:shutil.copytree(SOURCE/'src',TARGET/'src',dirs_exist_ok=True)
    overlay={ROOT/'team_work/03_ai_soc/c24/main.cc':'main.cc',
             ROOT/'team_work/shared/include/cooperation_v1.h':'cooperation_v1.h',
             ROOT/'team_work/shared/src/cooperation_v1.c':'cooperation_v1.c'}
    for folder,names in {'c2':['c2_driver.c','c2_driver.h','c2_sapphire.c','c2_sapphire.h'],
                         'c24':['c24_pipeline.c','c24_pipeline.h','c24_log_format.h'],
                         'c3_hal':['c3_hal.c','c3_hal.h','c3_sapphire_time.c','c3_shared_time.c','c3_shared_time.h'],
                         'c4':['c4_bridge.c','c4_bridge.h','c4_tflm_adapter.cc','c4_tflm_adapter.h']}.items():
        for name in names:overlay[ROOT/'team_work/03_ai_soc'/folder/name]=name
    for src,name in overlay.items():shutil.copy2(src,TARGET/'src'/name)
    makefile=(SOURCE/'makefile').read_text().replace('PROJ_NAME=tinyml_pdti8','PROJ_NAME=tinyml_c24')
    makefile=makefile.replace('include ${STANDALONE}/common/tinyml_standalone.mk','include c24_standalone.mk')
    (TARGET/'makefile').write_text(makefile)
    local=(STANDALONE/'common/tinyml_standalone.mk').read_text().replace('@mkdir -p $(dir $(OBJS))','@echo C24 object directories prepared')
    (TARGET/'c24_standalone.mk').write_text(local)
    for p in (TARGET/'src').rglob('*'):
        if p.is_file():(TARGET/'build_ours/out'/p.relative_to(TARGET).parent).mkdir(parents=True,exist_ok=True)
    (TARGET/'build_ours/common').mkdir(parents=True,exist_ok=True)
    previous=json.loads((ROOT/'firmware/c1_static_person_detect/C1_INPUT_MANIFEST.json').read_text(encoding='utf-8-sig'))
    hashes={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in overlay}
    for p in (SOURCE/'src').rglob('*'):
        if p.is_file() and p.name!='main.cc':hashes[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [STANDALONE/'common/tinyml_lib.a',ROOT/'tools/prepare_c24.py']:
        hashes[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    options=vars(args);version='c24-'+hashlib.sha256(json.dumps([hashes,options],sort_keys=True).encode()).hexdigest()[:16]
    raw=bytes(0 if n<2016 or n>=7200 else ((n-2016)*17+1)&255 for n in range(9216))
    header=f'''#define C24_BUILD_ID "{version}"
#define C24_ENABLE_LIVE {int(args.enable_live)}u
#define C24_MAP_VERIFIED {int(args.verified_map)}u
#define C24_SHARED_TIME_VERIFIED {int(args.verified_shared_time)}u
#define C24_SHARED_BASE 0x{args.shared_base:08x}u
#define C24_MODEL_FNV 0x{previous['model_fnv']}u
#define C24_SELFTEST_RAW_FNV 0x{fnv(raw):08x}u
'''
    (TARGET/'src/c24_build_id.h').write_text(header)
    record={'version':version,'app':str(TARGET),'source_hashes':hashes,'config':options,
            'source_policy':'pad54_candidate','model_sha256':previous['model_sha256'],
            'selftest_raw_fnv':f'{fnv(raw):08x}','selftest_tensor_fnv':f'{fnv(bytes((b-128)&255 for b in raw)):08x}',
            'model_fnv':previous['model_fnv'],'transport_version':0x00020002,'time_kind':1,'time_hz':100000000,
            'selftest_sha256':hashlib.sha256(raw).hexdigest(),
            'board_executed':False,'live_camera_verified':False}
    (TARGET/'C24_PREPARATION.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    out=ROOT/'firmware/c24_frame_person_detect';out.mkdir(parents=True,exist_ok=True)
    (out/'C24_INPUT_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'version':version,'app':str(TARGET),'live_enabled':args.enable_live}))

if __name__=='__main__':main()
