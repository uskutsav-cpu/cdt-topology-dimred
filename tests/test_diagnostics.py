import numpy as np
from diagnostics import autocorrelation,summary,bootstrap_return
from condensate import excised_operator
from spectral import exact_returns

def test_autocorrelation_detects_correlated_samples():
    rng=np.random.default_rng(42); x=np.zeros(100000)
    for i in range(1,len(x)): x[i]=.8*x[i-1]+rng.normal()
    _,tau=autocorrelation(x)
    assert 3.7<tau<5.4  # analytic (1+.8)/(2*(1-.8))=4.5
    assert summary(x)['effective_samples']<len(x)/7

def test_bootstrap_seed():
    x=np.arange(40).reshape(4,10)
    assert np.array_equal(list(bootstrap_return(x,10,44)),list(bootstrap_return(x,10,44)))

def test_excision_boundary_conventions_conserve_mass_and_differ():
    n=8; nb=np.array([[(i-1)%n,(i+1)%n] for i in range(n)]); mask=np.arange(n)<4
    a,ids=excised_operator(nb,mask,boundary='renormalize')
    b,_=excised_operator(nb,mask,boundary='hold')
    assert np.allclose(np.asarray(a.sum(axis=0)),1)
    assert np.allclose(np.asarray(b.sum(axis=0)),1)
    assert not np.allclose(exact_returns(a,10),exact_returns(b,10))
    assert np.array_equal(ids,[0,1,2,3])
