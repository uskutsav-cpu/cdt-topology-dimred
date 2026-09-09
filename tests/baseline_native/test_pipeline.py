from pathlib import Path
import json,shutil
import numpy as np
import pytest
from cdt_baseline.pipeline import simulate
from cdt_baseline.measure import measure_study
from cdt_baseline.analysis import analyze_study
from cdt_baseline.verify import verify_study
from cdt_baseline.io import load_json,atomic_json,sha256

@pytest.fixture(scope='session')
def executed(root,tmp_path_factory):
    study=tmp_path_factory.mktemp('full-smoke');cfg=load_json(root/'configs/baseline/smoke.json')
    assert simulate(root,cfg,study,workers=2)['status']=='NATIVE_RUNS_COMPLETE'
    assert measure_study(root,cfg,study,workers=2)['status']=='MEASUREMENTS_COMPLETE'
    answer=analyze_study(root,cfg,study)
    assert answer['decision']['reproduction_pass'] is False
    return study,cfg


def test_end_to_end_verified(root,executed):
    study,cfg=executed;r=verify_study(root,study)
    assert r['verified'] and r['independent_production_chains']==8 and r['geometries']==128
    assert not r['REPRODUCTION_PASS'] and not r['production_gates_changed']
    assert all(p['k3']==load_json(study/'raw'/p['job']/'manifest.json')['parameters']['k3'] for p in load_json(study/'chain_index.json'))


def test_idempotent_cached_stages(root,executed):
    study,cfg=executed;index=load_json(study/'measurement_index.json');before={p['raw']:sha256(study/p['raw']) for p in index}
    result=simulate(root,cfg,study,workers=2);assert result['status']=='NATIVE_RUNS_COMPLETE'
    measure_study(root,cfg,study,workers=2);analyze_study(root,cfg,study);assert verify_study(root,study)['verified']
    assert before=={p['raw']:sha256(study/p['raw']) for p in index}

@pytest.mark.parametrize('case',['raw_geometry','returns','native_manifest','measurement_manifest','missing_geometry','missing_chain','duplicate_chain','snapshot_identity','summary','fake_pass'])
def test_evidence_tampering_rejected(root,executed,tmp_path,case):
    original,cfg=executed;study=tmp_path/'study';shutil.copytree(original,study)
    ci=load_json(study/'chain_index.json');mi=load_json(study/'measurement_index.json');ai=load_json(study/'analysis_index.json')
    if case=='raw_geometry':
        p=study/mi[0]['raw'];p.write_bytes(p.read_bytes()+b'x')
    elif case=='returns':
        p=study/'measurements'/mi[0]['measurement']/'returns.npz';p.write_bytes(b'bad')
    elif case=='native_manifest':
        p=study/'raw'/ci[0]['job']/'manifest.json';d=load_json(p);d['parameters']['k3']+=.1;atomic_json(p,d)
    elif case=='measurement_manifest':
        p=study/'measurements'/mi[0]['measurement']/'manifest.json';d=load_json(p);d['exact_probability_propagation']=False;atomic_json(p,d)
    elif case=='missing_geometry':(study/mi[0]['raw']).unlink()
    elif case=='missing_chain':atomic_json(study/'chain_index.json',ci[1:])
    elif case=='duplicate_chain':atomic_json(study/'chain_index.json',ci[:1]+ci[:-1])
    elif case=='snapshot_identity':
        mi[0]['snapshot']=mi[1]['snapshot'];atomic_json(study/'measurement_index.json',mi)
    elif case=='summary':
        p=study/'analyses'/ai['analysis']/'summary.json';p.write_bytes(p.read_bytes()+b'x')
    elif case=='fake_pass':
        p=study/'analyses'/ai['analysis']/'summary.json';d=load_json(p);d['decision']['reproduction_pass']=True;atomic_json(p,d)
    with pytest.raises((ValueError,FileNotFoundError,ArithmeticError,KeyError)):verify_study(root,study)


def test_source_snapshot_enforced(root,executed,tmp_path):
    study,cfg=executed;fake=tmp_path/'root';needed=set()
    for m in (study/'measurements').glob('*/manifest.json'):needed.update(load_json(m)['contract']['sources'])
    ai=load_json(study/'analysis_index.json');needed.update(load_json(study/'analyses'/ai['analysis']/'manifest.json')['contract']['sources'])
    for name in needed:
        p=fake/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,p)
    assert verify_study(fake,study)['verified']
    p=fake/'src/cdt_baseline/analysis.py';p.write_text(p.read_text()+'\n# altered\n')
    with pytest.raises(ValueError):verify_study(fake,study)


def test_frozen_protocol_cannot_be_changed(root,executed):
    study,cfg=executed;new=dict(cfg,burn_sweeps=cfg['burn_sweeps']+1)
    with pytest.raises(ValueError):simulate(root,new,study)
    with pytest.raises(ValueError):analyze_study(root,new,study)
