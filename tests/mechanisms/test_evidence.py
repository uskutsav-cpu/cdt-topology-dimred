from pathlib import Path
import json
import numpy as np
import pytest
from cdt_mechanisms.evidence import *
from cdt_mechanisms.triangulations import product_cdt,bipyramid,write_geometry


def producer(root):
    write_json(root/'answer.json',{'answer':42,'undefined':float('nan')})
    np.savez_compressed(root/'values.npz',values=np.arange(10))

def test_completed_run_reuse(tmp_path):
    root,reused=create_run(tmp_path,{'test':1},producer)
    assert not reused and verify_run(root)['completed']
    second,reused=create_run(tmp_path,{'test':1},producer)
    assert root==second and reused
    assert json.loads((root/'answer.json').read_text())['undefined'] is None

@pytest.mark.parametrize('corruption',['change','delete','add','manifest','empty','unsafe'])
def test_hash_tampering_refused(tmp_path,corruption):
    root,_=create_run(tmp_path,{'test':1},producer)
    if corruption=='change': (root/'answer.json').write_text('{}')
    elif corruption=='delete': (root/'values.npz').unlink()
    elif corruption=='add': (root/'extra').write_text('unexpected')
    elif corruption=='unsafe':
        (root/'answer.json').unlink(); (root/'answer.json').symlink_to(tmp_path/'outside')
    else:
        m=json.loads((root/'manifest.json').read_text())
        if corruption=='manifest': m['completed']=False
        else: m['artifacts']={}
        (root/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError): verify_run(root)
    with pytest.raises(ValueError): create_run(tmp_path,{'test':1},producer)

def test_config_changes_identity(tmp_path):
    a,_=create_run(tmp_path,{'seed':1},producer); b,_=create_run(tmp_path,{'seed':2},producer)
    assert a!=b

def test_failed_run_not_published(tmp_path):
    def fail(root):
        write_json(root/'partial.json',{'partial':True}); raise RuntimeError('stop')
    with pytest.raises(RuntimeError): create_run(tmp_path,{'failure':1},fail)
    assert not list(tmp_path.glob('*/manifest.json')) and not list(tmp_path.glob('*.lock'))

def test_lock_is_exclusive(tmp_path):
    p=tmp_path/'lock'
    with exclusive_lock(p):
        with pytest.raises(FileExistsError):
            with exclusive_lock(p): pass
    assert not p.exists()

def make_manifest(tmp_path):
    p=tmp_path/'geometry.dat'; write_geometry(product_cdt(bipyramid(6),3),p)
    return dict(schema='cdt-mechanisms-ensemble-v1',configurations=[
        dict(configuration_id='a',chain_id='chain-a',coupling=1.,sweep=100,
             geometry='geometry.dat',geometry_sha256=sha256(p))])

def test_manifest_is_exploratory_not_gate_pass(tmp_path):
    m=make_manifest(tmp_path); m['thermalized']=True
    audit=require_ensemble_manifest(m,root=tmp_path)
    assert audit['scientific_status']=='EXPLORATORY_ONLY' and not audit['production_gates_changed']

@pytest.mark.parametrize('kind',['no_data','bad_hash','duplicate','missing_id','coupling','sweep','wrong_schema'])
def test_bad_ensemble_rejected(tmp_path,kind):
    m=make_manifest(tmp_path)
    if kind=='no_data': m['configurations']=[]
    elif kind=='bad_hash': m['configurations'][0]['geometry_sha256']='0'*64
    elif kind=='duplicate': m['configurations'].append(m['configurations'][0].copy())
    elif kind=='missing_id': del m['configurations'][0]['chain_id']
    elif kind=='coupling': m['configurations'][0]['coupling']=float('nan')
    elif kind=='sweep': m['configurations'][0]['sweep']=-1
    else: m['schema']='legacy'
    with pytest.raises(ValueError): require_ensemble_manifest(m,root=tmp_path)

def test_json_strict_nonfinite_conversion(tmp_path):
    p=tmp_path/'a.json'; write_json(p,{'a':np.array([np.inf,np.nan,1.])})
    assert json.loads(p.read_text())=={'a':[None,None,1.]}
    with pytest.raises(FileExistsError): write_json(p,{})

def test_nested_fake_manifest_not_ignored(tmp_path):
    root,_=create_run(tmp_path,{'test':1},producer)
    (root/'nested').mkdir(); (root/'nested/manifest.json').write_text('{}')
    with pytest.raises(ValueError,match='artifact set'): verify_run(root)

def test_symlink_root_rejected(tmp_path):
    root,_=create_run(tmp_path/'runs',{'test':1},producer)
    alias=tmp_path/'alias'; alias.symlink_to(root,target_is_directory=True)
    with pytest.raises(ValueError,match='symlink'): verify_run(alias)
