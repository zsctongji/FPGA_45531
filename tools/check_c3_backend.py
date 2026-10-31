"""C3 peripheral acceptance: actual RTL, host driver, RV32 and saved thermal ABI.
No serial/JTAG/GPIO access. Physical pad/clock/timing acceptance remains separate.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    build=ROOT/'build/c3';build.mkdir(parents=True,exist_ok=True)
    report={'status':'RUNNING','started':datetime.now(timezone.utc).isoformat(),
            'board_verified':False,'physical_pins_frozen':False,'electrical_signoff':False,'steps':[],
            'source_sha256':{}}
    def step(name,args,timeout=90):
        r=subprocess.run([str(a) for a in args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        (build/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
        report['steps'].append({'name':name,'status':'PASS' if r.returncode==0 else 'FAIL','evidence':r.stdout.splitlines()[-5:]})
        if r.returncode:raise ValueError(r.stdout+r.stderr)
        return r.stdout+r.stderr
    try:
        files=[*sorted((ROOT/'team_work/03_ai_soc/c3_hal').glob('*.[ch]')),
               ROOT/'team_work/03_ai_soc/tests/test_c3_peripheral.c',
               ROOT/'projects/06_soc_c2/rtl/c3_apb_peripheral.sv',
               ROOT/'projects/06_soc_c2/sim/tb_c3_peripheral.sv',ROOT/'projects/06_soc_c2/sim/tb_c3_timing.sv',
               ROOT/'projects/06_soc_c2/sim/tb_c3_shared_epoch.sv',
               *[ROOT/'projects/06_soc_c2/rtl'/n for n in ['c2_apb_control.sv','c2_shared_time.sv','c2_cdc_mailbox.sv']],
               ROOT/'tools/build_c3_host.cmd',ROOT/'tools/check_c2_riscv.py',Path(__file__)]
        report['source_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in files}
        iv=ROOT/'tools/iverilog/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
        for name,params in [('peripheral',{}),('shared_epoch',{})]+[('timing',{'RATE':n}) for n in [100000,400000,1000000]]:
            top='tb_c3_'+name;key=top+''.join('_'+str(v) for v in params.values());exe=build/(key+'.vvp')
            args=[iv,'-g2012','-Wall','-s',top,'-o',exe,*[f'-P{top}.{k}={v}' for k,v in params.items()],
                  'projects/06_soc_c2/rtl/c3_apb_peripheral.sv',f'projects/06_soc_c2/sim/{top}.sv']
            if name=='shared_epoch':args.extend('projects/06_soc_c2/rtl/'+n for n in ['c2_apb_control.sv','c2_shared_time.sv','c2_cdc_mailbox.sv'])
            output=step(key+'_compile',args)
            if output.strip():raise ValueError('Unexpected compiler diagnostics: '+output)
            output=step(key,[vvp,exe])
            if 'PASS '+top+' ' not in output:raise ValueError(output)
        step('host_driver',['cmd','/c',ROOT/'tools/build_c3_host.cmd'])
        step('RV32_objects',[sys.executable,ROOT/'tools/check_c2_riscv.py'])
        # Bind new C publication policy to B's 100 real saved records; do not
        # duplicate A model runs here (the separate replay report binds those).
        from replay_team_real_data import thermal,BUILD,ARCHIVES
        saved={'source_sha256':{}}
        thermal(saved,BUILD/ARCHIVES['B'][0],Path(r'C:/Users/16034/Documents/ChatGPT/FPGA/FPGA_cooperation_handoff'))
        assert saved['B_C_ABI_policies']['C_masked_accepted']==100
        report['thermal']=saved
        for name,digest in report['source_sha256'].items():
            if sha(ROOT/name)!=digest:raise ValueError('Source changed '+name)
        report['status']='PASS'
    except Exception as e:report.update(status='FAIL',error=str(e));print(str(e),file=sys.stderr)
    report['finished']=datetime.now(timezone.utc).isoformat()
    (ROOT/'logs/c3_backend_check.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('C3 backend '+report['status']);return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
