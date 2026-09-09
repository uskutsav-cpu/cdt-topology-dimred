import json,subprocess
import numpy as np
import pytest
from scipy.sparse import csr_matrix,eye
from geometry import Geometry,read_geometry,write_geometry
from cdt_baseline.initial import seed_geometry,write_seed
from cdt_baseline.geometry import validate_geometry
from cdt_baseline.measure import exact_returns,full_operator,draw_roots,profile_statistics
from cdt_baseline.statistics import dimension,root_jackknife,diagnostic,moving_block_indices,block_curves

@pytest.mark.parametrize('T',[3,4,8,16,64])
def test_native_seed_both_validators(tmp_path,validator,T):
    p=tmp_path/'g.dat';write_seed(T,p);slow=validate_geometry(read_geometry(p))
    fast=json.loads(subprocess.check_output([str(validator),str(p)],text=True))
    for k,v in fast.items():assert slow[k]==v
    assert slow['N3']==18*T and slow['N0']==5*T

@pytest.mark.parametrize('case',['self','outofrange','duplicate','wrongface','badtime','unused','truncated'])
def test_invalid_geometry(tmp_path,validator,case):
    g=seed_geometry(8);t=g.time.copy();c=g.tetra.copy();n=g.neighbors.copy()
    if case=='self':n[0,0]=0
    elif case=='outofrange':n[0,0]=len(c)
    elif case=='duplicate':c[1]=c[0]
    elif case=='wrongface':n[0,[0,1]]=n[0,[1,0]]
    elif case=='badtime':t[0]=100
    elif case=='unused':t=np.r_[t,0]
    q=Geometry(t,c,n,True);p=tmp_path/'bad.dat';write_geometry(q,p)
    if case=='truncated':p.write_bytes(p.read_bytes()[:-20])
    result=subprocess.run([str(validator),str(p)],capture_output=True)
    assert result.returncode!=0
    if case!='truncated':
        with pytest.raises(ValueError):validate_geometry(q)

@pytest.mark.parametrize('rho',[.2,.4,.8,.95])
def test_exact_dense_agreement(rho):
    g=seed_geometry(3);M=full_operator(g.neighbors,rho);roots=np.array([0,4,22]);P,error=exact_returns(M,roots,20,2)
    Q=np.eye(len(g.tetra));truth=[]
    for s in range(21):truth.append(Q.diagonal()[roots]);Q=M@Q
    assert np.allclose(P,np.array(truth).T,rtol=1e-13,atol=1e-14);assert error<1e-12

@pytest.mark.parametrize('batch',[1,3,9])
def test_batch_independence(batch):
    g=seed_geometry(3);M=full_operator(g.neighbors,.8);roots=np.array([1,2,7,11,32]);a,_=exact_returns(M,roots,32,batch);b,_=exact_returns(M,roots,32,1)
    assert np.array_equal(a,b)

def test_mass_and_stationary():
    g=seed_geometry(3);M=full_operator(g.neighbors,.4);P,error=exact_returns(M,np.arange(len(g.tetra)),1000,8)
    assert np.allclose(P[:,-1],1/len(g.tetra),atol=1e-10);assert error<1e-10

@pytest.mark.parametrize('bad',[np.array([1]),np.array([-1,0]),np.array([1.,2.])])
def test_bad_roots(bad):
    M=csr_matrix([[.5,.5],[.5,.5]])
    if bad.dtype.kind in 'iu' and bad.min()>=0:
        result,error=exact_returns(M,bad,20);assert result.shape==(1,21) and error<1e-12;return
    with pytest.raises(ValueError):exact_returns(M,bad,20)

def test_nonstochastic():
    with pytest.raises(ValueError):exact_returns(2*eye(4),np.array([0]),10)

def test_root_sampling_not_low_labels():
    ids=np.arange(1000);means=[draw_roots(ids,16,s)[:8].mean() for s in range(256)]
    assert abs(np.mean(means)-499.5)<20
    x=draw_roots(ids,16,99);assert len(set(x))==16 and not np.array_equal(x,np.sort(x))

def test_profile_ties_translation_invariant():
    p=np.array([4,8,4,8,4,4,4,4]);a=profile_statistics(p);b=profile_statistics(np.roll(p,3))
    for k in ('profile_width','profile_participation','profile_peak_fraction'):assert a[k]==pytest.approx(b[k])

def test_distinct_estimands():
    s=np.arange(50);P=np.stack([np.exp(-.02*s),np.exp(-.10*s)])
    assert not np.allclose(dimension(P).mean(axis=0)[2:-2],dimension(P.mean(axis=0))[2:-2])

def test_powerlaw_dimension():
    s=np.arange(1,1001);P=np.r_[1,s**-1.5];D=dimension(P)
    assert np.max(np.abs(D[30:-1]-3))<.01

def test_census_root_jackknife_zero():
    p=np.random.default_rng(1).uniform(.1,1,(4,16,8,33));p[:,:,:,0]=1
    assert np.all(root_jackknife(p,np.full((4,16),8))==0)

def test_good_and_bad_chain_screens(root):
    from cdt_baseline.io import load_json
    limits=load_json(root/'configs/baseline/native_pilot.json')['limits'];rng=np.random.default_rng(910)
    x=rng.normal(size=(4,3000));assert diagnostic(x,limits)['pass_screen']
    y=x+np.arange(4)[:,None];assert not diagnostic(y,limits)['pass_screen']
    assert not diagnostic(np.zeros((4,30)),limits)['pass_screen']
    assert not diagnostic(np.tile(x[0],(4,1)),limits)['pass_screen']
    x[0,0]=np.nan;assert not diagnostic(x,limits)['pass_screen']

@pytest.mark.parametrize('block',[1,2,4,8])
def test_block_indices(block):
    x=moving_block_indices(32,block,np.random.default_rng(71));assert len(x)==32 and x.min()>=0 and x.max()<32
    for a in range(0,32,block):assert np.all(np.diff(x[a:a+block])%32==1)

def test_bootstrap_reproducible():
    s=np.arange(33);x=np.exp(-.1*s)[None,None,:]*np.ones((4,16,1));a,b=block_curves(x,4,30,71);c,d=block_curves(x,4,30,71)
    assert np.array_equal(a,c,equal_nan=True) and np.array_equal(b,d,equal_nan=True)
    assert np.allclose(a[:,2:-2],dimension(x)[0,0,2:-2])
