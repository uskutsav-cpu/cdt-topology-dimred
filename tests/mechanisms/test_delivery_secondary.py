"""Offline tests of safe additive delivery and paired persistence data joins."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'workflows'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

installer=load('apply_mechanisms_update')
secondary=load('analyze_mechanism_secondary')

@pytest.mark.parametrize('url',[
 'https://github.com/uskutsav-cpu/cdt-topology-dimred',
 'https://github.com/uskutsav-cpu/cdt-topology-dimred.git',
 'git@github.com:uskutsav-cpu/cdt-topology-dimred.git',
 'ssh://git@github.com/uskutsav-cpu/cdt-topology-dimred.git'])
def test_remote_forms(url):
    assert installer.canonical_origin(url)==installer.REPOSITORY

@pytest.mark.parametrize('value',['../escape','/tmp/escape','src/../escape','src/cdt_mechanisms/../x',
'.git/config','README.md','src\\evil','src//cdt_mechanisms/x',''])
def test_unsafe_relative(value):
    with pytest.raises(ValueError): installer.safe_relative(value)

def fixture_bundle(tmp_path):
    bundle=tmp_path/'bundle';payload=bundle/'payload';payload.mkdir(parents=True)
    rel='src/cdt_mechanisms/new.py';p=payload/rel;p.parent.mkdir(parents=True);p.write_text('x=1\n')
    manifest=dict(schema='cdt-mechanisms-additive-bundle-v1',repository=installer.REPOSITORY,
                  base_commit=installer.BASE_COMMIT,files={rel:installer.sha256(p)})
    (bundle/'BUNDLE_MANIFEST.json').write_text(json.dumps(manifest))
    repo=tmp_path/'repo';repo.mkdir()
    return bundle,repo,rel

def test_dry_run_and_exclusive_addition(tmp_path,monkeypatch):
    bundle,repo,rel=fixture_bundle(tmp_path)
    monkeypatch.setattr(installer,'preflight_repository',lambda _:None)
    result=installer.install(bundle,repo);assert result['new_files']==1;assert not (repo/rel).exists()
    result=installer.install(bundle,repo,apply=True);assert (repo/rel).read_text()=='x=1\n'
    assert result['overwritten_files']==0 and not result['pushed']
    assert installer.install(bundle,repo)['identical_files']==1

def test_existing_different_file_is_untouched(tmp_path,monkeypatch):
    bundle,repo,rel=fixture_bundle(tmp_path);target=repo/rel;target.parent.mkdir(parents=True);target.write_text('keep')
    monkeypatch.setattr(installer,'preflight_repository',lambda _:None)
    with pytest.raises(ValueError,match='existing file differs'):installer.install(bundle,repo,apply=True)
    assert target.read_text()=='keep'

def test_tampered_payload_refused(tmp_path):
    bundle,repo,rel=fixture_bundle(tmp_path);(bundle/'payload'/rel).write_text('tampered')
    with pytest.raises(ValueError,match='hash'):installer.inspect_bundle(bundle)

def test_destination_symlink_refused(tmp_path,monkeypatch):
    bundle,repo,rel=fixture_bundle(tmp_path);(repo/'src').symlink_to(tmp_path,target_is_directory=True)
    monkeypatch.setattr(installer,'preflight_repository',lambda _:None)
    with pytest.raises(ValueError,match='symlink'):installer.install(bundle,repo,apply=True)

def test_extra_payload_refused(tmp_path):
    bundle,repo,rel=fixture_bundle(tmp_path);(bundle/'payload/extra').write_text('unlisted')
    with pytest.raises(ValueError,match='file set'):installer.inspect_bundle(bundle)

def test_main_branch_refused(tmp_path,monkeypatch):
    bundle,repo,rel=fixture_bundle(tmp_path)
    def fake_git(_, *args,**kwargs):
        if args[0]=='rev-parse':return str(repo)
        if args[0]=='remote':return 'https://github.com/'+installer.REPOSITORY
        if args[0]=='branch':return 'main'
        return ''
    monkeypatch.setattr(installer,'git',fake_git)
    with pytest.raises(ValueError,match='review branch'):installer.install(bundle,repo,apply=True)

def test_dirty_tree_refused(tmp_path,monkeypatch):
    bundle,repo,rel=fixture_bundle(tmp_path)
    def fake_git(_, *args,**kwargs):
        return {'rev-parse':str(repo),'remote':'https://github.com/'+installer.REPOSITORY,
                'branch':'review','status':' M live-manifest.json'}[args[0]]
    monkeypatch.setattr(installer,'git',fake_git)
    with pytest.raises(ValueError,match='not clean'):installer.install(bundle,repo,apply=True)

def topology():
    return dict(root=7,summary=[dict(dimension=d,observed_persistence=4.,finite_total_persistence=1.,censored_intervals=2)
             for d in (1,2)])

def test_censored_and_finite_doses_separate():
    row=secondary.doses(topology())
    assert row['H1_observed_persistence']==4 and row['H1_finite_total_persistence']==1

@pytest.mark.parametrize('field',['observed_persistence','finite_total_persistence','censored_intervals'])
def test_bad_dose_refused(field):
    top=topology();top['summary'][0][field]=-1
    with pytest.raises(ValueError):secondary.doses(top)

def test_join_uses_root_identity_not_position():
    controls=dict(time_extent=4,lower_time=[0,2],lower_vertex_count=[1,2],root_equilateral_deficit=[1.,2.])
    features=[dict(root=7,radius=4,ball_vertices=10,conductance=.2,annular_components=1,
                   spanning_annular_branches=1,graph_cycle_fraction=.1)]
    diff=dict(roots=np.array([11,7]),ds=np.array([[0,3],[0,2]]),pre_mix=np.ones((2,2),bool))
    row=secondary.joined_rows(dict(controls=controls,features=features),[topology()],diff,4,1)[0]
    assert row['outcome']==2 and row['controls'][1]==2
    diff['pre_mix'][1,1]=False
    assert secondary.joined_rows(dict(controls=controls,features=features),[topology()],diff,4,1)==[]

def test_join_unknown_root_refused():
    with pytest.raises(ValueError,match='no paired'):
        secondary.joined_rows(dict(controls={'time_extent':4},features=[]),[topology()],
               dict(roots=np.array([1])),4,1)

@pytest.mark.parametrize('wrong_origin',[False,True])
def test_real_git_preflight_and_additive_install(tmp_path,monkeypatch,wrong_origin):
    import subprocess
    bundle,repo,rel=fixture_bundle(tmp_path)
    def run(*args):
        return subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,check=True).stdout.strip()
    run('init','-b','mechanisms-review')
    run('config','user.name','Offline Test');run('config','user.email','test@example.invalid')
    run('commit','--allow-empty','-m','fixture base')
    base=run('rev-parse','HEAD');monkeypatch.setattr(installer,'BASE_COMMIT',base)
    manifest=json.loads((bundle/'BUNDLE_MANIFEST.json').read_text());manifest['base_commit']=base
    (bundle/'BUNDLE_MANIFEST.json').write_text(json.dumps(manifest))
    run('remote','add','origin','https://github.com/'+('other/repo' if wrong_origin else installer.REPOSITORY)+'.git')
    if wrong_origin:
        with pytest.raises(ValueError,match='origin is not'):installer.install(bundle,repo,apply=True)
        assert not (repo/rel).exists()
    else:
        assert installer.install(bundle,repo,apply=True)['new_files']==1
        assert run('status','--porcelain').startswith('?? src/')
        assert run('rev-parse','HEAD')==base
        with pytest.raises(ValueError,match='not clean'):installer.install(bundle,repo,apply=True)
