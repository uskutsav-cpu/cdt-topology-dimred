"""Exercise registry recovery/extension, not only the low-level checkpoint."""
import importlib.util,json,sys,subprocess,hashlib
from pathlib import Path
import pytest
PROJECT=Path(__file__).resolve().parents[1]

@pytest.fixture
def project(tmp_path,monkeypatch):
    for d in ['build/simulator','data/raw','data/geometry','logs','results/manifests']:(tmp_path/d).mkdir(parents=True,exist_ok=True)
    (tmp_path/'build/simulator/cdt-run').symlink_to(PROJECT/'build/simulator/cdt-run')
    (tmp_path/'data/raw/init.dat').symlink_to(PROJECT/'data/raw/initial_T8.dat')
    subprocess.run(['git','init',str(tmp_path)],check=True,capture_output=True)
    subprocess.run(['git','-C',str(tmp_path),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','--allow-empty','-m','test fixture'],check=True,capture_output=True)
    spec=importlib.util.spec_from_file_location('run_chain_test',PROJECT/'workflows/run_chain.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=tmp_path
    c={'name':'test','input':'data/raw/init.dat','seed':77,'k0':1.,'k3':1.,'target':300,'tune':5,'burn':5,'samples':3,'sample_stride':1,'attempts':100,'check_every_move':0,'timeout_seconds':30}
    path=tmp_path/'config.json';path.write_text(json.dumps(c))
    def run(*flags):monkeypatch.setattr(sys,'argv',['run_chain',str(path),*flags]);m.main()
    return tmp_path,path,c,run

def test_completed_job_extension_preserves_raw(project):
    root,path,c,run=project;run();manifest=next((root/'results/manifests').glob('*.json'));job=manifest.stem
    raw=root/'data/raw'/job;old={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.glob('*.dat')}
    c['samples']=5;path.write_text(json.dumps(c));run('--extend-job',job)
    assert len(list(raw.glob('*.dat')))==5
    for name,h in old.items():assert hashlib.sha256((raw/name).read_bytes()).hexdigest()==h
    record=json.loads(manifest.read_text());assert record['status']=='complete' and record['previous_revision']['completed_samples']==3

def test_failed_job_resumes_from_checkpoint(project,monkeypatch):
    root,path,c,run=project;monkeypatch.setenv('CDT_STOP_AFTER_SWEEP','12')
    with pytest.raises(subprocess.CalledProcessError):run()
    manifest=next((root/'results/manifests').glob('*.json'));assert json.loads(manifest.read_text())['status']=='failed'
    monkeypatch.delenv('CDT_STOP_AFTER_SWEEP');run('--resume')
    assert json.loads(manifest.read_text())['status']=='complete'
    assert len(list((root/'data/raw'/manifest.stem).glob('*.dat')))==3
