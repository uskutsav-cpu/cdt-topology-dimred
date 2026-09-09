import json,os,subprocess,sys,time
from pathlib import Path
import pytest
from cdt_baseline.io import *
from cdt_baseline.chain import validate_parameters,native_environment,repair_trace
from cdt_baseline.design import validate_design,stage_seed

@pytest.mark.parametrize('key,value',[('seed',True),('seed',0),('seed',2147483647),('samples',-1),('samples',2.2),('k3',float('nan')),('k0',float('inf')),('target',0),('burn',-1),('tune',-1),('attempts',0),('sample_stride',0),('check_every_move',2),('samples',2147483647)])
def test_invalid_native_parameters(parameters,key,value):
    parameters[key]=value
    with pytest.raises(ValueError):validate_parameters(parameters)

def test_unknown_native_parameter(parameters):
    parameters['foo']=1
    with pytest.raises(ValueError):validate_parameters(parameters)

@pytest.mark.parametrize('text',['{"a":1,"a":2}','{"x":NaN}','{"x":Infinity}','{"x":-Infinity}'])
def test_strict_json(tmp_path,text):
    p=tmp_path/'x.json';p.write_text(text)
    with pytest.raises(ValueError):load_json(p)

def test_immutable_and_corruption(tmp_path):
    p=tmp_path/'a.json';immutable_json(p,{'a':1});immutable_json(p,{'a':1})
    with pytest.raises(ValueError):immutable_json(p,{'a':2})
    inv=inventory(tmp_path);verify_inventory(tmp_path,inv);p.write_text('x')
    with pytest.raises(ValueError):verify_inventory(tmp_path,inv)

@pytest.mark.parametrize('name',['../outside','/etc/passwd','foo/../../outside'])
def test_path_escape(tmp_path,name):
    with pytest.raises(ValueError):inside(tmp_path,name)

def test_symlink_refusal(tmp_path):
    p=tmp_path/'link';p.symlink_to('/etc/passwd')
    with pytest.raises(ValueError):inside(tmp_path,'link')
    with pytest.raises(ValueError):atomic_bytes(p,b'no')

def test_lock_refusal_and_release(tmp_path):
    p=tmp_path/'job.lock'
    with lock(p):
        with pytest.raises(RuntimeError):
            with lock(p):pass
    with lock(p):pass

def test_child_inherits_lock(tmp_path):
    p=tmp_path/'job.lock'
    with lock(p) as fd:
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(.25)'],pass_fds=(fd,))
    try:
        with pytest.raises(RuntimeError):
            with lock(p):pass
    finally:child.wait()
    with lock(p):pass

def test_strip_checkpoint_environment(monkeypatch):
    monkeypatch.setenv('CDT_INITIAL_CHECKPOINT','foreign');monkeypatch.setenv('CDT_STOP_AFTER_SWEEP','5')
    env=native_environment();assert 'CDT_INITIAL_CHECKPOINT' not in env and 'CDT_STOP_AFTER_SWEEP' not in env
    assert native_environment(7)['CDT_STOP_AFTER_SWEEP']=='7'

@pytest.mark.parametrize('change',[{'chains':1},{'samples':1},{'time_extent':2},{'roots':0},{'rho':1.},{'rho':float('nan')},{'volumes':[10000,10000]},{'couplings':[1.,1.]},{'max_steps':10},{'sample_stride':False}])
def test_invalid_design(root,change):
    c=load_json(root/'configs/baseline/native_pilot.json');c.update(change)
    with pytest.raises((ValueError,TypeError)):validate_design(c)

@pytest.mark.parametrize('key,value',[('bulk_ess',50),('tail_ess',50),('rhat',1.2),('reference_reviewed',True),('block_lengths',[1000])])
def test_no_weak_or_fake_pass(root,key,value):
    c=load_json(root/'configs/baseline/native_pilot.json');c['limits'][key]=value
    with pytest.raises(ValueError):validate_design(c)

def test_seeds_stable_on_extension(root):
    c=load_json(root/'configs/baseline/native_pilot.json');d=dict(c,samples=1024)
    assert stage_seed(c,'production',10000,1.,0)==stage_seed(d,'production',10000,1.,0)
    values=[stage_seed(c,s,v,k,ch) for s in ('tuning','dispersal','production') for v in c['volumes'] for k in c['couplings'] for ch in range(c['chains'])]
    assert len(values)==len(set(values))

def test_retains_crash_tail(tmp_path):
    p=tmp_path/'diagnostics.csv';head=b'sweep,phase,N0,N3,N31,k3,peak_slice,seconds\n';a=b'1,burn,5,30,10,1.2,4,0.1\n';b=b'2,burn,5,30,10,1.2,4,0.2\n'
    p.write_bytes(head+a+b+b'3,burn,PARTIAL')
    report=repair_trace(tmp_path,1);assert p.read_bytes()==head+a
    assert (tmp_path/report['path']).read_bytes()==b+b'3,burn,PARTIAL'
    assert repair_trace(tmp_path,1) is None

def test_reject_trace_before_checkpoint(tmp_path):
    (tmp_path/'diagnostics.csv').write_text('sweep,phase,N0,N3,N31,k3,peak_slice,seconds\n')
    with pytest.raises(ValueError):repair_trace(tmp_path,4)
