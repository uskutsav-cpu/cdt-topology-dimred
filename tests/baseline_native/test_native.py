import csv,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
import numpy as np
import pytest
from cdt_baseline.chain import run_native_job,checkpoint_header,PARAMETERS,read_trace,native_environment
from cdt_baseline.io import sha256,load_json,blob_sha,atomic_json
from cdt_baseline.native import build_native,check_sources
from cdt_baseline.geometry import validate_geometry
from geometry import read_geometry


def raw(study,m):return study/'raw'/m['job_id']
def geometry_hashes(folder):return {p.name:sha256(p) for p in folder.glob('geometry_*.dat')}

def direct(root,binary,seedfile,out,p,stop=None):
    out.mkdir(parents=True,exist_ok=True)
    cmd=[str(root/binary),str(seedfile),str(out),*[str(p[k]) for k in PARAMETERS]]
    with (out/'test.log').open('ab') as f:return subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=native_environment(stop),timeout=60).returncode


def test_exact_source_build(root,build):
    records,checkout=check_sources(root)
    assert records['upstream_commit']=='5720c0b98d809b35974d5c6fe067a828fe6b1267'
    assert build['original_research_build_succeeded']
    assert sha256(root/build['binary'])==build['binary_sha256']


def test_fresh_native_reproducibility(root,build,native_seed,tmp_path,parameters):
    study=tmp_path/'study'
    a=run_native_job(root,build,study,'same-A',native_seed,parameters,stage='debug')
    b=run_native_job(root,build,study,'same-B',native_seed,parameters,stage='debug')
    assert geometry_hashes(raw(study,a))==geometry_hashes(raw(study,b))
    p=dict(parameters,seed=parameters['seed']+1)
    c=run_native_job(root,build,study,'independent',native_seed,p,stage='debug')
    assert geometry_hashes(raw(study,a))!=geometry_hashes(raw(study,c))
    for geo in raw(study,a).glob('geometry_*.dat'):assert validate_geometry(read_geometry(geo))['all_vertex_links_S2']

@pytest.mark.parametrize('stop',[1,13,23,29])
def test_restart_exact(root,build,native_seed,tmp_path,parameters,stop):
    study=tmp_path/'study'
    full=run_native_job(root,build,study,'full',native_seed,parameters,stage='debug')
    pause=run_native_job(root,build,study,'paused',native_seed,parameters,stage='debug',stop_after=stop)
    assert pause['status']=='paused' and pause['exit_code']==75
    before=geometry_hashes(raw(study,pause));done=run_native_job(root,build,study,'paused',native_seed,parameters,stage='debug')
    assert done['status']=='complete'
    assert geometry_hashes(raw(study,full))==geometry_hashes(raw(study,done))
    for name,h in before.items():assert sha256(raw(study,done)/name)==h
    a=checkpoint_header(raw(study,full)/'checkpoint.bin');b=checkpoint_header(raw(study,done)/'checkpoint.bin');assert a==b


def test_extension_preserves_states(root,build,native_seed,tmp_path,parameters):
    study=tmp_path/'study';p=dict(parameters,samples=2)
    a=run_native_job(root,build,study,'extended',native_seed,p,stage='debug');old=geometry_hashes(raw(study,a))
    b=run_native_job(root,build,study,'extended',native_seed,parameters,stage='debug')
    assert a['job_id']==b['job_id'] and b['previous_revision']
    for name,h in old.items():assert sha256(raw(study,b)/name)==h
    full=run_native_job(root,build,study,'full',native_seed,parameters,stage='debug')
    assert geometry_hashes(raw(study,b))==geometry_hashes(raw(study,full))
    with pytest.raises(ValueError):run_native_job(root,build,study,'extended',native_seed,p,stage='debug')


def test_corrupted_completed_output_refused(root,build,native_seed,tmp_path,parameters):
    s=tmp_path/'s';m=run_native_job(root,build,s,'raw',native_seed,parameters,stage='debug')
    p=raw(s,m)/'geometry_0.dat';p.write_bytes(p.read_bytes()+b'corruption')
    with pytest.raises(ValueError):run_native_job(root,build,s,'raw',native_seed,parameters,stage='debug')


def test_truncated_checkpoint_refused_native(root,build,native_seed,tmp_path,parameters):
    p=dict(parameters,samples=1);out=tmp_path/'x';assert direct(root,build['binary'],native_seed,out,p,13)==75
    cp=out/'checkpoint.bin';cp.write_bytes(cp.read_bytes()[:100]);assert direct(root,build['binary'],native_seed,out,p)==70


def test_original_vs_adapter_and_acceptance_bug(root,build,native_seed,tmp_path):
    p=dict(seed=12345,k0=1.,k3=2.,target=144,tune=0,burn=3000,samples=1,attempts=1,check_every_move=0,sample_stride=1)
    old=tmp_path/'original';new=tmp_path/'adapter'
    assert direct(root,build['original_binary'],native_seed,old,p)==0
    assert direct(root,build['binary'],native_seed,new,p)==0
    assert geometry_hashes(old)==geometry_hashes(new)
    def false_accepts(folder):
        rows=list(csv.DictReader((folder/'diagnostics.csv').open()));previous=40;false=0
        for row in rows:
            n=int(row['N0'])
            if int(row['accept_2']) and n==previous:false+=1
            previous=n
        return false
    # This legitimate fixture need not visit the rare rejected-deletion branch.
    assert false_accepts(new)==0


def test_debug_check_each_move(root,build,native_seed,tmp_path,parameters):
    p=dict(parameters,check_every_move=1,burn=4,samples=2,attempts=100)
    assert direct(root,build['binary'],native_seed,tmp_path/'debug',p)==0


def test_inherited_checkpoint_not_adopted(root,build,native_seed,tmp_path,parameters,monkeypatch):
    monkeypatch.setenv('CDT_INITIAL_CHECKPOINT','/no/such/checkpoint')
    a=run_native_job(root,build,tmp_path/'s','fresh',native_seed,parameters,stage='debug')
    assert a['status']=='complete' and a['initial_checkpoint_inherited'] is False


def test_pause_via_timeout(root,build,native_seed,tmp_path,parameters):
    p=dict(parameters,burn=1000000,samples=1)
    a=run_native_job(root,build,tmp_path/'s','deadline',native_seed,p,stage='debug',timeout_seconds=.2)
    assert a['status']=='paused' and a['exit_code']==75 and a['error']=='TimeoutExpired'
    assert checkpoint_header(raw(tmp_path/'s',a)/'checkpoint.bin')['completed_sweeps']<p['burn']


def test_crash_tail_and_orphan_geometry_replay(root,build,native_seed,tmp_path,parameters):
    s=tmp_path/'s';a=run_native_job(root,build,s,'full',native_seed,parameters,stage='debug')
    b=run_native_job(root,build,s,'crash',native_seed,parameters,stage='debug',stop_after=23)
    folder=raw(s,b);mp=folder/'manifest.json';m=load_json(mp);m['status']='running';m.pop('outputs');atomic_json(mp,m)
    lines=(raw(s,a)/'diagnostics.csv').read_bytes().splitlines(keepends=True)
    with (folder/'diagnostics.csv').open('ab') as f:f.write(b''.join(lines[24:27]))
    shutil.copy2(raw(s,a)/'geometry_1.dat',folder/'geometry_1.dat')
    c=run_native_job(root,build,s,'crash',native_seed,parameters,stage='debug')
    assert c['recovery'] and c['status']=='complete'
    assert geometry_hashes(folder)==geometry_hashes(raw(s,a))


def test_tuning_forbidden_in_production(root,build,native_seed,tmp_path,parameters):
    parameters['tune']=10
    with pytest.raises(ValueError):run_native_job(root,build,tmp_path/'s','bad',native_seed,parameters,stage='production')


def test_native_inverse_families(root,build,native_seed,tmp_path,parameters):
    ref=Path(__file__).parent/'reference/move_inverse.cpp'
    assert blob_sha(ref)=='9f7ec7bfebb1331e8740819531d4afe9a64512e0'
    src=root/'build/baseline'/build['build_id']/'source/build/simulator'
    exe=tmp_path/'inverse'
    command=['c++','-std=c++14','-O2','-Wno-format','-I',str(src),str(ref),*[str(src/f) for f in ['universe.cpp','vertex.cpp','tetra.cpp','triangle.cpp','halfedge.cpp']],'-o',str(exe)]
    subprocess.run(command,check=True,capture_output=True,timeout=60)
    p=dict(parameters,target=1000,burn=500,samples=1,attempts=1000)
    m=run_native_job(root,build,tmp_path/'s','pilot',native_seed,p,stage='debug')
    geometry=raw(tmp_path/'s',m)/'geometry_0.dat'
    for kind in ['26','44','23u','23d']:
        r=subprocess.run([str(exe),str(geometry),kind],capture_output=True,text=True,timeout=30)
        assert r.returncode==0,(kind,r.stdout,r.stderr)
        assert f'PASS inverse {kind}' in r.stdout


def test_rejected_delete_counter_with_fault_injection(root,build,native_seed,tmp_path):
    """Force move62 to reject, proving the return-value bug without claiming a physical run."""
    original=root/'build/baseline'/build['build_id']/'source/build/simulator'
    src=tmp_path/'source';src.mkdir()
    for p in original.glob('*.hpp'):shutil.copy2(p,src/p.name)
    for p in original.glob('*.cpp'):
        if p.name!='runner.cpp':shutil.copy2(p,src/p.name)
    h=src/'simulation.hpp';h.write_text(h.read_text().replace('static bool moveDelete();','public:\n static bool moveDelete();\nprivate:'))
    u=src/'universe.cpp';u.write_text(u.read_text().replace('bool Universe::move62(Vertex::Label v) {','bool Universe::move62(Vertex::Label v) {\n return false; // TEST-ONLY forced rejection\n'))
    probe=src/'probe.cpp';probe.write_text('''#include "universe.hpp"
#include "simulation.hpp"
#include <iostream>
int main(int argc,char**argv){
 if(argc!=2)return 2;Universe::initialize(argv[1],"test",3,1);
 Universe::move26(*Universe::tetras31.begin());
 Simulation::seed_rng(123);Universe::seed_rng(789);
 Simulation::k0=1.;Simulation::k3=10.;Simulation::targetVolume=0;
 int yes=0;for(int i=0;i<400;++i)yes+=Simulation::moveDelete();std::cout<<"reported_accepted="<<yes<<"\\n";
 return yes==0?0:11;
}''')
    fixed=(src/'simulation.cpp').read_text();cpp=[str(p) for p in src.glob('*.cpp')]
    for buggy in (False,True):
        text=fixed.replace('return Universe::move62(v);','Universe::move62(v); return true;') if buggy else fixed
        (src/'simulation.cpp').write_text(text);exe=tmp_path/('buggy' if buggy else 'fixed')
        subprocess.run(['c++','-std=c++14','-O1','-Wno-format','-I',str(src),*cpp,'-o',str(exe)],check=True,capture_output=True,timeout=60)
        r=subprocess.run([str(exe),str(native_seed)],capture_output=True,text=True,timeout=30)
        assert r.returncode==(11 if buggy else 0),r.stdout+r.stderr


def test_genuinely_fresh_isolated_native_rebuild(root,tmp_path):
    import shutil
    from cdt_baseline.native import build_native
    from cdt_baseline.io import load_json,verify_inventory
    export=tmp_path/'isolated-source';lockfile=root/'configs/baseline/source_lock.json'
    paths=list(load_json(lockfile)['git_blobs'])+['configs/baseline/source_lock.json']
    for relative in paths:
        target=export/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/relative,target)
    m=build_native(export,capacity=10000)
    assert m['original_research_build_succeeded']
    assert m['source_checkout']['kind']=='hash_verified_source_export'
    assert not m['source_checkout']['clean_git_checkout']
    verify_inventory(export/'build/baseline'/m['build_id'],m['outputs'])
    assert (export/m['binary']).is_file()
    assert build_native(export,capacity=10000)['binary_sha256']==m['binary_sha256']
