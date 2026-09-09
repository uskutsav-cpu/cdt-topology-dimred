import csv,json
from pathlib import Path
import numpy as np
import pytest
from cdt_confirmation.physical import diagnostic_screen,read_native_trace,load_native_job,audit_repository
from cdt_mechanisms.evidence import sha256
from cdt_mechanisms.triangulations import product_cdt,bipyramid,write_geometry,audit_cdt

@pytest.mark.parametrize('seed',range(4))
def test_stationary_iid_screen(seed):
    x=np.random.default_rng(seed).normal(size=(4,2500))
    report=diagnostic_screen(x)
    assert report['pass_screen'] and not report['reproduction_pass']

@pytest.mark.parametrize('case',['shift','trend','identical','constant','too_few_chains','autocorrelated'])
def test_bad_mcmc_screens(case):
    rng=np.random.default_rng(44);x=rng.normal(size=(4,1500))
    if case=='shift':x+=np.arange(4)[:,None]*2
    elif case=='trend':x+=np.linspace(0,4,1500)
    elif case=='identical':x[:]=x[0]
    elif case=='constant':x[0]=0
    elif case=='too_few_chains':x=x[:2]
    else:
        for t in range(1,x.shape[1]):x[:,t]+=.995*x[:,t-1]
    assert not diagnostic_screen(x)['pass_screen']

@pytest.mark.parametrize('shape',[(1,12),(4,3),(4,10,2)])
def test_bad_diagnostic_shape(shape):
    with pytest.raises(ValueError):diagnostic_screen(np.zeros(shape))


def native_fixture(tmp_path):
    # Parser-only synthetic test files. They are not research ensemble outputs.
    job='a'*20;raw=tmp_path/'data/raw'/job;raw.mkdir(parents=True)
    binary=tmp_path/'build/simulator/cdt-run';binary.parent.mkdir(parents=True);binary.write_text('synthetic parser fixture, not a simulator')
    g=product_cdt(bipyramid(6),3);v=audit_cdt(g)
    for i in range(8):write_geometry(g,raw/f'geometry_{i}.dat')
    columns=['sweep','phase','N0','N3','N31','k3','peak_slice','seconds']+[s for i in range(1,6) for s in [f'attempt_{i}',f'accept_{i}']]
    with (raw/'diagnostics.csv').open('w') as h:
        writer=csv.DictWriter(h,fieldnames=columns);writer.writeheader()
        for sweep in range(1,17):
            row=dict(sweep=sweep,phase='measure' if sweep>8 else 'burn',N0=18+sweep%2,N3=72+sweep%3,
                     N31=24+sweep%2,k3=1.2,peak_slice=8+sweep%2,seconds=1)
            row.update({f'attempt_{i}':5 for i in range(1,6)});row.update({f'accept_{i}':2 for i in range(1,6)});writer.writerow(row)
    m=dict(stage='simulation',status='complete',configuration_id=job,binary_sha256=sha256(binary),
        parameters=dict(seed=1,k0=1,k3=1.2,target=72,tune=0,burn=8,samples=8,sample_stride=1),geometry_validation=[v]*8,
        output_hashes={str(p.relative_to(tmp_path)):sha256(p) for p in raw.iterdir()})
    mp=tmp_path/'manifest.json';mp.write_text(json.dumps(m))
    return mp,m,raw


def test_native_parser_and_no_false_readiness(tmp_path):
    path,m,raw=native_fixture(tmp_path)
    loaded=load_native_job(tmp_path,path)
    assert loaded['trace']['values'].shape==(8,4) and len(loaded['geometry'])==8
    assert audit_repository(tmp_path)['status']=='BLOCKED'

@pytest.mark.parametrize('fault',['inherited_rng','corrupt','missing_geometry','failed','wrong_binary','wrong_schedule','escape','missing_validation'])
def test_native_provenance_faults(tmp_path,fault):
    path,m,raw=native_fixture(tmp_path)
    if fault=='inherited_rng':m['parameters']['initial_checkpoint']='old.bin'
    elif fault=='corrupt':(raw/'geometry_0.dat').write_text('altered')
    elif fault=='missing_geometry':m['output_hashes'].pop(str((raw/'geometry_0.dat').relative_to(tmp_path)))
    elif fault=='failed':m['status']='failed'
    elif fault=='wrong_binary':m['binary_sha256']='0'*64
    elif fault=='wrong_schedule':m['parameters']['samples']=7
    elif fault=='escape':m['output_hashes']['../outside']='0'*64
    else:m['geometry_validation']=[]
    path.write_text(json.dumps(m))
    with pytest.raises(ValueError):load_native_job(tmp_path,path)

@pytest.mark.parametrize('fault',['k3','sweeps','acceptance','empty'])
def test_native_trace_faults(tmp_path,fault):
    _,_,raw=native_fixture(tmp_path);path=raw/'diagnostics.csv'
    with path.open() as h:rows=list(csv.DictReader(h));columns=list(rows[0])
    if fault=='k3':rows[-1]['k3']='1.3'
    elif fault=='sweeps':rows[-1]['sweep']='18'
    elif fault=='acceptance':rows[-1]['accept_1']='100'
    else:rows=[]
    with path.open('w') as h:
        w=csv.DictWriter(h,fieldnames=columns);w.writeheader();w.writerows(rows)
    with pytest.raises(ValueError):read_native_trace(path)


def test_audit_cli_does_not_reuse_changed_report(tmp_path,monkeypatch):
    """Unchanged manifests must not cause reuse after raw-data corruption."""
    import runpy,sys,json
    from pathlib import Path
    import cdt_confirmation.physical as physical
    root=Path(__file__).resolve().parents[2]
    out=tmp_path/'reports';repo=tmp_path/'repo';repo.mkdir()
    for state in ['first_missing_trace','then_corrupted_trace']:
        monkeypatch.setattr(physical,'audit_repository',lambda *a,_state=state,**kw:dict(
            status='BLOCKED',missing_requirements=['physical data'],detail=_state))
        monkeypatch.setattr(sys,'argv',['audit','--repo',str(repo),'--output',str(out)])
        with pytest.raises(SystemExit) as error:
            runpy.run_path(str(root/'workflows/audit_physical_confirmation.py'),run_name='__main__')
        assert error.value.code==2
    reports=list(out.glob('*/audit.json'))
    assert len(reports)==2
    assert {json.loads(p.read_text())['detail'] for p in reports}=={'first_missing_trace','then_corrupted_trace'}
