import hashlib
import importlib.util
import json
from pathlib import Path
import os
import subprocess
import sys
import pytest
from runtime_safety import atomic_json, job_lock, JobLockedError
from research_gates import require_production_gates, REQUIRED_GATES, GateClosedError
from saved_state import comparison_screen, audit_saved_state

ROOT = Path(__file__).resolve().parents[1]


def test_atomic_json_preserves_previous_on_invalid_data(tmp_path):
    path = tmp_path/'record.json'
    atomic_json(path, {'version': 1})
    with pytest.raises(ValueError):
        atomic_json(path, {'bad': float('nan')})
    assert json.loads(path.read_text()) == {'version': 1}
    atomic_json(path, {'version': 2})
    assert json.loads(path.read_text()) == {'version': 2}
    assert not list(tmp_path.glob('.record.json.*'))


def test_job_lock_competing_process_and_release(tmp_path):
    path = tmp_path/'job.lock'
    script = 'from runtime_safety import job_lock,JobLockedError\nimport sys\ntry:\n with job_lock(sys.argv[1]): pass\nexcept JobLockedError:\n sys.exit(7)\n'
    env = {**os.environ, 'PYTHONPATH': str(ROOT/'src')}
    with job_lock(path):
        inode = path.stat().st_ino
        out = subprocess.run([sys.executable, '-c', script, str(path)], env=env)
        assert out.returncode == 7
    out = subprocess.run([sys.executable, '-c', script, str(path)], env=env)
    assert out.returncode == 0 and path.stat().st_ino == inode


def test_lock_released_after_exception(tmp_path):
    path = tmp_path/'job.lock'
    with pytest.raises(RuntimeError):
        with job_lock(path):
            raise RuntimeError('interrupted')
    with job_lock(path):
        pass


def test_safe_launcher_preserves_hash_and_forwarding(tmp_path, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location('safe_runner_test', ROOT/'workflows/run_chain_safe.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = tmp_path
    for p in ['build/simulator/cdt-run','data/raw/init.dat','workflows/run_chain.py']:
        dest = tmp_path/p
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(p)
    cfg = {'name':'test','input':'data/raw/init.dat','samples':2}
    path = tmp_path/'config.json'
    path.write_text(json.dumps(cfg))
    digest = lambda p: hashlib.sha256((tmp_path/p).read_bytes()).hexdigest()
    contract = {'parameters':{**cfg,'sample_stride':1},
                'binary_sha256':digest('build/simulator/cdt-run'),
                'input_sha256':digest('data/raw/init.dat'),
                'driver_sha256':digest('workflows/run_chain.py')}
    expected = hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()[:20]
    assert mod.resolve_job(tmp_path,path) == expected
    mod.main([str(path),'--dry-run'])
    assert json.loads(capsys.readouterr().out)['job'] == expected
    called = []
    def run(path, run_name):
        called.append((path,run_name,list(sys.argv)))
        with pytest.raises(JobLockedError):
            with job_lock(tmp_path/'results/locks'/f'{expected}.lock'):
                pass
    monkeypatch.setattr(mod.runpy,'run_path',run)
    mod.main([str(path),'--extend-job',expected,'--resume'])
    assert called[0][1] == '__main__'
    assert called[0][2][-3:] == ['--resume','--extend-job',expected]
    with pytest.raises(ValueError):
        mod.resolve_job(tmp_path,path,'../../escape')


def make_comparison(sweeps=200, ess=70):
    obs = {'rank_folded_split_rhat':1.005,'minimum_split_single_chain_ess':ess,
           'full_chain_summaries':[{'effective_samples':100,'split_z':.5,'screen_pass':True} for _ in range(2)]}
    return {'jobs':['a','b'],'common_prefix_sweeps':sweeps,
            'observables':{k:obs.copy() for k in ['N0','N3','N31','peak_slice']}}


def test_saved_screens_fail_closed_and_not_equilibrium_proof():
    assert not comparison_screen({})['configured_screens_pass']
    assert comparison_screen(make_comparison())['configured_screens_pass']
    assert not comparison_screen(make_comparison())['equilibrium_certified']
    assert not comparison_screen(make_comparison(ess=49))['configured_screens_pass']
    bad = make_comparison()
    bad['observables']['N0']['rank_folded_split_rhat'] = float('nan')
    assert not comparison_screen(bad)['configured_screens_pass']


def test_latest_comparison_selected_by_sweeps_not_filename(tmp_path):
    path = tmp_path/'results/tables'
    path.mkdir(parents=True)
    atomic_json(path/'chain_comparison_zzz.json',make_comparison(100,80))
    atomic_json(path/'chain_comparison_aaa.json',make_comparison(300,20))
    report = audit_saved_state(tmp_path, jobs=('a','b'))
    assert report['baseline_comparison']['common_prefix_sweeps'] == 300
    assert not report['baseline_comparison']['configured_screens_pass']
    assert report['live_process_status'] == 'NOT_OBSERVED'


def test_running_manifests_are_not_live_evidence(tmp_path):
    d = tmp_path/'results/manifests'
    d.mkdir(parents=True)
    atomic_json(d/'a.json',{'stage':'simulation','status':'running','configuration_id':'a'})
    report = audit_saved_state(tmp_path)
    assert report['simulation_manifests'][0]['saved_status'] == 'running'
    assert report['live_process_status'] == 'NOT_OBSERVED'
    assert not report['raw_geometry_hashes_verified']


def test_production_gates_require_exact_evidence(tmp_path):
    gate = tmp_path/'gates.json'
    atomic_json(gate,{})
    with pytest.raises(GateClosedError):
        require_production_gates(tmp_path,gate)
    evidence = tmp_path/'evidence.txt'
    evidence.write_text('test fixture, not real scientific evidence')
    h = hashlib.sha256(evidence.read_bytes()).hexdigest()
    atomic_json(gate,{k:{'status':'PASS','evidence':[{'path':'evidence.txt','sha256':h}]} for k in REQUIRED_GATES})
    assert len(require_production_gates(tmp_path,gate)) == 4
    evidence.write_text('changed')
    with pytest.raises(GateClosedError):
        require_production_gates(tmp_path,gate)
