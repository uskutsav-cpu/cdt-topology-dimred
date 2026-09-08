import numpy as np
import pytest
from pathlib import Path
from geometry import read_geometry,write_geometry,validate
from spectral import operator,exact_returns,hutchinson,walkers,dimension

def lattice(L,d):
    coords=np.array(list(np.ndindex(*(L,)*d)))
    return np.array([[np.ravel_multi_index(tuple((c+sgn*np.eye(d,dtype=int)[axis])%L),(L,)*d) for axis in range(d) for sgn in [-1,1]] for c in coords])

@pytest.mark.parametrize('d,L',[(1,100),(2,22),(3,12)])
def test_regular_lattice_dimension(d,L):
    nb=lattice(L,d); M=operator(nb,.5)
    P=exact_returns(M,35,[0])[0]
    assert abs(dimension(P)[20]-d)<.22
    assert np.max(np.abs(np.asarray(M.sum(axis=0)).ravel()-1))<1e-14

def test_estimators():
    nb=lattice(10,1); M=operator(nb); truth=exact_returns(M,20).mean(axis=0)
    H=hutchinson(M,20,2048,17)
    assert np.all(np.abs(H.mean(axis=0)-truth)<=5*H.std(axis=0)/np.sqrt(len(H))+1e-14)
    W=walkers(nb,20,200000,21)
    assert np.all(np.abs(W-truth)<5*np.sqrt(truth*(1-truth)/200000)+1e-14)
    mask=np.arange(10)<3; C=hutchinson(M,20,2048,19,mask)
    assert np.all(np.abs(C.mean(axis=0)-truth)<5*C.std(axis=0)/np.sqrt(len(C))+1e-14)

def test_roundtrip(tmp_path):
    g=read_geometry(Path(__file__).resolve().parents[1]/'data/raw/initial_T8.dat')
    a=validate(g); p=tmp_path/'roundtrip.dat'; write_geometry(g,p); h=read_geometry(p)
    assert np.array_equal(g.tetra,h.tetra) and np.array_equal(g.neighbors,h.neighbors)
    assert a==validate(h)

def test_volume_fix_reverse():
    eps=4e-5; V=107; target=100
    for dv in [-4,-2,-1,1,2,4]:
        logf=-eps*((V+dv-target)**2-(V-target)**2)
        logr=-eps*((V-target)**2-(V+dv-target)**2)
        assert logf+logr==0
    # Regression against exactly the patched C++ reverse expressions.
    assert -8*eps*(target-V+2)==pytest.approx(-eps*((V-4-target)**2-(V-target)**2))
    assert -eps*(2*target-2*V+1)==pytest.approx(-eps*((V-1-target)**2-(V-target)**2))

def test_proposal_inverse():
    n0,n31=35,54
    forward=n31/(n0+1); reverse=(n0+1)/((n31+2)-2)
    assert forward*reverse==1
    # The stock factors are reciprocal, but not the proposal ratio in paper eq.26.
    assert n31/(n31+2)!=forward

def test_mixture_identity():
    M=operator(lattice(9,1)); P=exact_returns(M,20); mask=np.arange(9)<4
    assert np.allclose(P.mean(axis=0),mask.mean()*P[mask].mean(axis=0)+(~mask).mean()*P[~mask].mean(axis=0))

def test_reject_nonpositive_returns():
    assert np.isnan(dimension(np.array([1.,.1,-.01,.02]))[1])
