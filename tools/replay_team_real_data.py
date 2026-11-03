"""Pinned A/B saved hardware data through current C RTL and ABI; offline only.
Archive contents are read as data. Only the explicitly selected B policy sources
are compiled for the host, against C's current cooperation_v1.h.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys,zipfile
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/team_real_20261031'
P=ROOT/'projects/06_soc_c2'
ARCHIVES={
 'A':('A_video_source_20261029.zip','46fa61dcf79d6146f073ff8dc5b0095b6eb62b2691923e922ede3008290a1dfd','af3982298932c1a921e6bc2840e5866d3e6ae3a2'),
 'B':('B_thermal_dataset_20261030.zip','3fea1eeae8d124859ad1655ec68a81738d6f5cd26237210a1a0bd9d3aaf30c0c','c75a4ac'),
}
def sha(data):return hashlib.sha256(data).hexdigest()
def fnv(data):
    n=2166136261
    for b in data:n=((n^b)*16777619)&0xffffffff
    return f'{n:08x}'
def run(args,cwd=ROOT,timeout=90):
    r=subprocess.run([str(x) for x in args],cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    if r.returncode:raise RuntimeError(f'{args[0]} exit={r.returncode}\n{r.stdout}\n{r.stderr}')
    return r.stdout+r.stderr
def bind(report,path):
    report['source_sha256'][path.relative_to(ROOT).as_posix()]=sha(path.read_bytes())
def bench(report):
    base=P/'sim/tb_c2_a_bridge.sv';bind(report,base)
    s=base.read_text(encoding='utf-8-sig').replace('tb_c2_a_bridge','tb_c2_real_a')
    s=s.replace('function [7:0] pixel_value', 'reg [7:0] replay[0:9215];\ninitial $readmemh("input.hex",replay);\nfunction [7:0] pixel_value',1)
    old='pixel_value=(index<2016 || index>=7200)?0:((index-2016)*17+frame);'
    assert old in s;s=s.replace(old,'pixel_value=replay[index];')
    old='sample_gray=(n*17+seq)&255;';assert old in s;s=s.replace(old,'sample_gray=replay[n+2016];')
    s=s.replace('a_c2_frame1.gray','ddr.gray')
    start=s.index('task read_image');end=s.index('endtask',start)
    part=s[start:end].replace('integer burst,b,n;','integer burst,b,n,fd;')
    part=part.replace(' begin\n',' begin\n   fd=$fopen("cpu.gray","wb");\n',1)
    part=part.replace('checks=checks+1;','for(n=0;n<16;n=n+1) $fwrite(fd,"%c",s_rdata[n*8+:8]);\n       checks=checks+1;')
    part=part.rsplit(' end\n',1)[0]+'   $fclose(fd);\n end\n'
    s=s[:start]+part+s[end:]
    path=BUILD/'tb_c2_real_a.sv';path.write_text(s,encoding='utf-8')
    sources=[*sorted((P/'rtl').glob('*.sv')),*sorted((P/'a_side').glob('*.v')),P/'sim/c2_ddr_model.sv',path]
    for p in sources:bind(report,p)
    iv=ROOT/'tools/iverilog/bin/iverilog.exe';exe=BUILD/'real_a.vvp'
    output=run([iv,'-g2012','-Wall','-s','tb_c2_real_a','-o',exe,*[p.relative_to(ROOT) for p in sources]])
    if re.search(r'warning|error',output,re.I):raise ValueError(output)
    return iv.with_name('vvp.exe'),exe
def images(report,archive):
    import numpy as np
    sys.path.insert(0,str(ROOT/'build/pc_ai_packages'))
    from ai_edge_litert.interpreter import Interpreter,OpResolverType
    from pc_model_data import array
    from pc_model_compat import desktop_compat
    original=array('mobilenetv1_person_detect_model_data');model,compat=desktop_compat(original)
    fw=json.loads((ROOT/'firmware/c24_frame_person_detect/C24_INPUT_MANIFEST.json').read_text())
    assert sha(original)==fw['model_sha256']
    engine=Interpreter(model_content=model,num_threads=1,experimental_op_resolver_type=OpResolverType.BUILTIN_REF)
    engine.allocate_tensors();inp=engine.get_input_details()[0];out=engine.get_output_details()[0]
    vvp,exe=bench(report)
    prefix='team_work/01_video/ai_samples_20261029/'
    with zipfile.ZipFile(archive) as z:
        manifest=json.loads(z.read(prefix+'MANIFEST.json'));report['A_manifest']=manifest
        if len(manifest['samples'])!=5:raise ValueError('Expected five A samples')
        report['A_samples']=[]
        for sample in manifest['samples']:
            label=sample['label']
            if not re.fullmatch('[a-z0-9_]+',label):raise ValueError('Invalid sample label')
            for name,digest in sample['files'].items():
                if sha(z.read(prefix+name))!=digest:raise ValueError('A manifest hash: '+name)
            raw=z.read(prefix+label+'.gray');meta=json.loads(z.read(prefix+label+'.json'))
            assert len(raw)==9216 and not any(raw[:2016]) and not any(raw[7200:])
            assert sum(raw)==sample['checksum']==meta['checksum']
            assert meta['clock']=='local_148500000Hz_display_ms' and not meta['shared_soc_time']
            case=BUILD/label;case.mkdir(exist_ok=True)
            (case/'input.hex').write_text(''.join(f'{v:02x}\n' for v in raw))
            log=run([vvp,exe,'+SEED=12345'],cwd=case,timeout=180)
            (case/'simulation.log').write_text(log,encoding='utf-8')
            if 'PASS tb_c2_real_a ' not in log:raise ValueError(log)
            ddr=(case/'ddr.gray').read_bytes();cpu=(case/'cpu.gray').read_bytes()
            if raw!=ddr or raw!=cpu:raise ValueError('A -> BRAM -> DDR -> CPU byte mismatch')
            scores=[]
            for b in [raw,cpu]:
                tensor=np.array([v-128 for v in b],dtype=np.int8).reshape(1,96,96,1)
                engine.set_tensor(inp['index'],tensor);engine.invoke()
                scores.append(engine.get_tensor(out['index']).reshape(-1).tolist())
            assert scores[0]==scores[1]
            report['A_samples'].append({'label':label,'source_metadata':meta,'raw_sha256':sha(raw),
              'raw_sum32':sum(raw),'raw_fnv1a':fnv(raw),'tensor_fnv1a':fnv(bytes((v-128)&255 for v in raw)),
              'ddr_sha256':sha(ddr),'CPU_AXI_readback_sha256':sha(cpu),'desktop_scores':scores[0],
              'transport_equals_direct_inference':True,'simulation_evidence':[x for x in log.splitlines() if x.startswith('PASS ')],
              'replay_ids_and_time':'synthetic bench frame IDs/shared time; original display metadata retained separately',
              'scene_accuracy_assessed':False})
            print('PASS A '+label,flush=True)
    report['desktop_model_compatibility']=compat
def thermal(report,archive,repo):
    vendor=BUILD/'b_policy';vendor.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        prefix='independent_work/thermal_dataset/results/'
        manifest=json.loads(z.read(prefix+'dataset_report.json'));report['B_dataset_report']=manifest
        for n,digest in manifest['output_files_sha256'].items():
            if sha(z.read(prefix+n))!=digest:raise ValueError('B dataset hash: '+n)
        for stem in ['b4_publish_gate','b4_quality_policy','b4_temporal_policy']:
            for ext in ['.c','.h']:
                n=stem+ext;p=vendor/n;p.write_bytes(z.read('independent_work/offline_acceptance/vendor/'+n));bind(report,p)
        data=z.read(prefix+'thermal_probe_records.bin');assert len(data)==1656*100
        binary=BUILD/'thermal.bin';binary.write_bytes(data)
        report['B_binary_sha256']=sha(data)
    # Compile B's original strict reader against the CURRENT C ABI/HAL, not its bundled header.
    for name in ['b_sensors.h','b_thermal.c']:
        folder='include' if name.endswith('.h') else 'src'
        source=repo/f'team_work/02_sensors_alarm/{folder}/{name}'
        p=vendor/name;p.write_bytes(source.read_bytes());bind(report,p)
    sources=[ROOT/'team_work/03_ai_soc/replay/thermal_replay.c',vendor/'b_thermal.c',
             ROOT/'team_work/03_ai_soc/c3_hal/c3_hal.c',ROOT/'team_work/03_ai_soc/c3_hal/c3_thermal_publish.c',ROOT/'team_work/shared/src/cooperation_v1.c',
             *[vendor/(n+'.c') for n in ['b4_publish_gate','b4_quality_policy','b4_temporal_policy']]]
    for p in sources:bind(report,p)
    for p in [ROOT/'team_work/shared/include/cooperation_v1.h',ROOT/'team_work/03_ai_soc/c3_hal/c3_hal.h',ROOT/'team_work/03_ai_soc/c3_hal/c3_thermal_publish.h']:bind(report,p)
    vc=Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat')
    exe=BUILD/'thermal_replay.exe';cmd=BUILD/'compile_thermal.cmd'
    flags=['cl','/nologo','/std:c11','/W4','/WX','/TC',f'/I"{vendor}"',
           f'/I"{ROOT/"team_work/shared/include"}"',f'/I"{ROOT/"team_work/03_ai_soc/c3_hal"}"',
           *[f'"{p}"' for p in sources],f'/Fo"{BUILD.as_posix()}/"',f'/Fe"{exe}"']
    cmd.write_text('@echo off\ncall "'+str(vc)+'" >nul\nif errorlevel 1 exit /b 1\n'+' '.join(flags)+'\nexit /b %errorlevel%\n')
    (BUILD/'thermal_compile.log').write_text(run(['cmd','/c',cmd]),encoding='utf-8')
    report['B_C_ABI_policies']=json.loads(run([exe,binary]))
    bad=BUILD/'thermal_truncated.bin';bad.write_bytes(data[:-1]);r=subprocess.run([str(exe),str(bad)],capture_output=True)
    assert r.returncode==4
    changed=bytearray(data);changed[4+20+1536+620//8]|=1<<(620%8)
    bad=BUILD/'thermal_bad_mask.bin';bad.write_bytes(changed);r=subprocess.run([str(exe),str(bad)],capture_output=True)
    assert r.returncode==6
    report['B_negative_tests']={'truncated_rejected':True,'changed_bad_pixel_mask_rejected':True}
    print('PASS B: current ABI; strict reject vs B4 masked accept; age boundaries and corruption tests',flush=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--a-archive',type=Path,default=BUILD/ARCHIVES['A'][0]);ap.add_argument('--b-archive',type=Path,default=BUILD/ARCHIVES['B'][0]);ap.add_argument('--repo',type=Path,default=Path(r'C:/Users/16034/Documents/ChatGPT/FPGA/FPGA_cooperation_handoff'));args=ap.parse_args()
    BUILD.mkdir(parents=True,exist_ok=True)
    report={'status':'RUNNING','started':datetime.now(timezone.utc).isoformat(),'source_sha256':{},'archives':{},
            'hardware_accessed':False,'new_board_measurements':0,'full_system_acceptance':False,
            'A_B_same_session':False,'shared_time_verified_on_board':False}
    path=ROOT/'logs/team_real_replay_20261031.json'
    try:
        bind(report,Path(__file__))
        for k,p in [('A',args.a_archive),('B',args.b_archive)]:
            digest=sha(p.read_bytes())
            if digest!=ARCHIVES[k][1]:raise ValueError(k+' archive identity mismatch')
            report['archives'][k]={'name':p.name,'sha256':digest,'source_commit':ARCHIVES[k][2]}
        images(report,args.a_archive);thermal(report,args.b_archive,args.repo)
        for name,digest in report['source_sha256'].items():
            if sha((ROOT/name).read_bytes())!=digest:raise ValueError('Source changed during replay: '+name)
        report['status']='PASS';print('PASS C real-data offline integration. No synchronized/board inference claim.')
    except Exception as e:
        report.update(status='FAIL',error=str(e));print(str(e),file=sys.stderr)
    report['finished']=datetime.now(timezone.utc).isoformat();path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
