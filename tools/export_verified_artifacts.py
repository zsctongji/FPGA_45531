"""Archive fresh standalone FPGA outputs after checking their final timing."""
from pathlib import Path
from datetime import datetime
import hashlib, json, re, shutil
root=Path(__file__).resolve().parents[1]
projects=[('led','01_led','LED_8bit_Test','led'),('camera','02_camera','ti60f225_oob','camera_color'),('camera_preprocess','04_camera_preprocess','ti60f225_oob','camera_preprocess'),('tinyml','03_tinyml','Ti60F225_tinyml_helloworld','tinyml_225mhz'),('camera_motion','05_camera_motion','ti60f225_oob','camera_motion')]
records=[]
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for key,folder,design,dest_name in projects:
    status=json.loads((root/f'logs/efinity_{key}_compile.json').read_text(encoding='utf-8-sig'))
    assert status['status']=='PASS' and status['flow']=='compile',f'Not verified: {key}'
    start=datetime.fromisoformat(status['started']).timestamp()
    out=root/'projects'/folder/'outflow'
    report=out/f'{design}.timing.rpt'
    assert report.stat().st_mtime >= start-2
    summary=re.search(r'Clock Relationship Summary \(begin\)(.*?)Clock Relationship Summary \(end\)',report.read_text(),re.S)[1]
    setup,hold=summary.split('Hold (Min) Clock Relationship')
    pattern=r'^\s*\S+\s+\S+\s+[-+]?\d+(?:\.\d+)?\s+([-+]?\d+(?:\.\d+)?)\s+\('
    setup_slacks=[float(x) for x in re.findall(pattern,setup,re.M)]
    hold_slacks=[float(x) for x in re.findall(pattern,hold,re.M)]
    assert setup_slacks and hold_slacks and min(setup_slacks)>=0 and min(hold_slacks)>=0
    destination=root/'fpga_bitstreams'/dest_name
    destination.mkdir(parents=True,exist_ok=True)
    artifacts=[]
    expected={Path(x['path']).name:x['sha256'].lower() for x in status['artifacts']}
    for extension in ('.hex','.bit'):
        source=out/f'{design}{extension}'
        if extension=='.bit' and not source.exists(): continue
        assert source.stat().st_mtime>=start-2 and source.stat().st_size>0
        sha=digest(source)
        if source.name in expected: assert sha==expected[source.name]
        target=destination/source.name
        shutil.copy2(source,target)
        assert digest(target)==sha
        artifacts.append({'file':str(target),'bytes':target.stat().st_size,'sha256':sha})
    shutil.copy2(report,destination/'final_timing.rpt')
    record={'project':key,'source_project':status['file'],'compiled_at':status['finished'],'minimum_setup_slack_ns':min(setup_slacks),'minimum_hold_slack_ns':min(hold_slacks),'artifacts':artifacts,'physical_board_test_passed':False,'scope':'Independent bring-up example; not integrated competition system'}
    (destination/'BUILD_RECORD.json').write_text(json.dumps(record,indent=2))
    records.append(record)
    print(f'{key}: fresh outputs archived; setup={min(setup_slacks)} ns hold={min(hold_slacks)} ns')
(root/'logs/verified_artifacts.json').write_text(json.dumps(records,indent=2))
