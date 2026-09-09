from pathlib import Path
import importlib.util,json,subprocess,sys
import pytest
from cdt_baseline.operations import budget,status,extension_design
from cdt_baseline.io import atomic_json,load_json
from cdt_baseline.design import stage_seed


def test_pilot_proposal_budget(root):
    cfg=load_json(root/'configs/baseline/native_pilot.json');r=budget(cfg)
    assert r['total_proposed_moves']==10_670_500_000
    assert sum(e['saved_production_geometries'] for e in r['ensembles'])==1536
    assert r['time_estimate'] is None


def test_production_schedule_is_explicitly_larger(root):
    p=budget(load_json(root/'configs/baseline/production.json'))
    q=budget(load_json(root/'configs/baseline/native_pilot.json'))
    assert p['total_proposed_moves']>50*q['total_proposed_moves']
    assert all(e['attempts_per_sweep']==10*e['volume'] for e in p['ensembles'])


def test_status_never_infers_process_liveness(tmp_path):
    r=status(tmp_path)
    assert r['jobs']==[] and r['analysis'] is None
    assert 'not inferred' in r['process_liveness']


def test_extension_only_changes_length(root,tmp_path):
    cfg=load_json(root/'configs/baseline/native_pilot.json')
    atomic_json(tmp_path/'requested_schedule.json',cfg)
    new=extension_design(tmp_path,256)
    assert new['samples']==256
    assert {k:v for k,v in new.items() if k!='samples'}=={k:v for k,v in cfg.items() if k!='samples'}
    assert stage_seed(cfg,'production',10000,1.,0)==stage_seed(new,'production',10000,1.,0)

@pytest.mark.parametrize('n',[None,0,128,-1,128.,True])
def test_invalid_extension_rejected(root,tmp_path,n):
    atomic_json(tmp_path/'requested_schedule.json',load_json(root/'configs/baseline/native_pilot.json'))
    with pytest.raises(ValueError):extension_design(tmp_path,n)


def test_plan_cli_never_runs_simulation(root,tmp_path):
    p=subprocess.run([sys.executable,str(root/'workflows/baseline.py'),'plan','--config',str(root/'configs/baseline/native_pilot.json'),'--output',str(tmp_path/'do-not-create')],capture_output=True,text=True,check=True)
    assert json.loads(p.stdout)['total_proposed_moves']==10_670_500_000
    assert not (tmp_path/'do-not-create').exists()


def _fresh(root):
    spec=importlib.util.spec_from_file_location('baseline_fresh_test',root/'workflows/fresh_baseline_checkout.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

@pytest.mark.parametrize('flag,value',[('--branch','-bad'),('--config','../outside.json'),('--config','/tmp/out.json')])
def test_clean_clone_preflight_rejects_unsafe_inputs(root,tmp_path,flag,value):
    p=subprocess.run([sys.executable,str(root/'workflows/fresh_baseline_checkout.py'),str(tmp_path/'clone'),f'{flag}={value}'],capture_output=True,text=True)
    assert p.returncode!=0 and not (tmp_path/'clone').exists()


def test_clean_clone_never_replaces_existing_directory(root,tmp_path):
    target=tmp_path/'keep';target.mkdir();(target/'proof').write_text('retained')
    p=subprocess.run([sys.executable,str(root/'workflows/fresh_baseline_checkout.py'),str(target)],capture_output=True,text=True)
    assert p.returncode!=0 and (target/'proof').read_text()=='retained'


def test_clean_clone_receipt_with_mocked_network(root,tmp_path,monkeypatch):
    m=_fresh(root);dest=tmp_path/'new-clone';calls=[]
    real_run=subprocess.run
    def run(cmd,**kw):
        calls.append(cmd)
        if cmd[:2]==['git','clone']:
            dest.mkdir();(dest/'src/cdt_baseline').mkdir(parents=True)
            (dest/'src/cdt_baseline/native.py').write_text('# explicit test fixture, not real clone\n')
            real_run(['git','init',str(dest)],check=True,capture_output=True)
            real_run(['git','-C',str(dest),'add','.'],check=True,capture_output=True)
            real_run(['git','-C',str(dest),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture'],check=True,capture_output=True)
            return subprocess.CompletedProcess(cmd,0)
        return real_run(cmd,**kw)
    monkeypatch.setattr(m.subprocess,'run',run)
    monkeypatch.setattr(sys,'argv',['fresh',str(dest)])
    assert m.main()==0
    receipt=json.loads((dest/'.git/baseline-clean-checkout.json').read_text())
    assert receipt['clean'] and receipt['branch']=='native-baseline-review'
    assert '--recurse-submodules' in calls[0]
    assert not dest.with_name(dest.name+'-venv').exists()
    assert not dest.with_name(dest.name+'-results').exists()


def test_cli_uses_spawn_before_parallel_measurement(root,tmp_path):
    script=root/'workflows/baseline.py'
    program="""import importlib.util,multiprocessing as mp,sys
spec=importlib.util.spec_from_file_location('baseline_cli',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sys.argv=['baseline','plan','--config',sys.argv[2]];m.main()
assert mp.get_start_method()=='spawn'
"""
    result=subprocess.run([sys.executable,'-c',program,str(script),str(root/'configs/baseline/smoke.json')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
