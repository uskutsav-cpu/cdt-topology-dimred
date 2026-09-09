from itertools import product
import numpy as np
import pytest
from scipy.sparse import csr_matrix, eye
from spectral import operator, exact_returns
from conditioned import partition_returns
from conditioned_stochastic import (_partition,propagate_probe_block,estimate_conditioned,probe_effect)


def ring(n=8):
    return operator(np.array([[(i-1)%n,(i+1)%n] for i in range(n)]))


def masks(n=8):
    regular=np.arange(n)<n//2
    return {'regular':regular,'singular':~regular}


@pytest.mark.parametrize('steps',[0,1,2,3,7,8,13])
@pytest.mark.parametrize('method',['half_power','hutchinson'])
def test_exhaustive_sign_oracle_is_exact(steps,method):
    n=4;M=ring(n);m=masks(n)
    _,_,reduction=_partition(m,n)
    z=np.array(list(product((-1,1),repeat=n)),float).T
    samples=propagate_probe_block(M,z,reduction,steps,method=method)
    exact=exact_returns(M,steps)
    expected=np.stack([exact[a].mean(axis=0) for a in m.values()])
    np.testing.assert_allclose(samples.mean(axis=0),expected,atol=1e-14,rtol=1e-14)
    if method=='half_power':
        assert np.all(samples[:,:,::2]>=0)


@pytest.mark.parametrize('method',['half_power','hutchinson'])
def test_batch_and_continuation_invariance(method):
    M=ring();m=masks()
    a=estimate_conditioned(M,m,12,probes=32,batch_size=1,seed=67,method=method)
    b=estimate_conditioned(M,m,12,probes=32,batch_size=11,seed=67,method=method)
    c=estimate_conditioned(M,m,12,probes=16,batch_size=7,seed=67,method=method)
    d=estimate_conditioned(M,m,12,probes=16,batch_size=5,seed=67,first_probe=16,method=method)
    np.testing.assert_allclose(a.samples,b.samples,atol=1e-15,rtol=0)
    np.testing.assert_allclose(a.samples,np.concatenate([c.samples,d.samples]),atol=1e-15,rtol=0)


def test_site_population_restriction_not_operator_restriction():
    M=ring();start=np.arange(8)<6
    m={'regular':np.arange(8)<2,'singular':(np.arange(8)>=2)&start}
    estimate=estimate_conditioned(M,m,10,probes=4096,seed=10,start_mask=start)
    exact=partition_returns(M,m,10,start_mask=start)['P_class']
    assert np.max(np.abs(estimate.mean-exact))<0.03
    np.testing.assert_allclose(estimate.overall_samples,
       (estimate.samples[:,0]*2+estimate.samples[:,1]*4)/6,atol=1e-15)


def test_identity_zero_variance_and_symmetric_pairing():
    e=estimate_conditioned(eye(8),masks(),10,probes=16)
    np.testing.assert_array_equal(e.samples,1)
    np.testing.assert_array_equal(e.standard_error,0)
    effect=probe_effect(e,[1,2,3],replicates=50)
    assert effect['A']==0 and effect['CI95_probe_only']==[0,0]
    assert e.operator_applications==16*5


def test_unbiased_estimator_agrees_with_exact_with_reported_noise():
    # An asymmetric set of origin classes on a symmetric, nonhomogeneous M.
    rng=np.random.default_rng(1);a=rng.uniform(size=(12,12));a=(a+a.T)/2
    M=a/(1.1*a.sum(axis=1).max());M+=np.diag(1-M.sum(axis=1))
    e=estimate_conditioned(csr_matrix(M),masks(12),25,probes=4096,seed=44)
    exact=partition_returns(csr_matrix(M),masks(12),25)['P_class']
    assert np.max(np.abs(e.mean-exact)/(e.standard_error+1e-12))<5
    np.testing.assert_allclose(e.overall_samples.mean(axis=0),
                               np.mean(e.mean,axis=0),atol=1e-14)


@pytest.mark.parametrize('kwargs,error',[
    ({'max_bytes':1},MemoryError),({'max_scalar_updates':1},RuntimeError),
    ({'probes':1},ValueError),({'batch_size':0},ValueError),({'method':'bad'},ValueError),
    ({'steps':-1},ValueError),({'seed':-1},ValueError),({'first_probe':-1},ValueError)])
def test_fail_closed_parameters(kwargs,error):
    args={'steps':6,'probes':10};args.update(kwargs)
    with pytest.raises(error):estimate_conditioned(ring(),masks(),**args)


def test_bad_partition_and_operator_fail():
    with pytest.raises(ValueError):estimate_conditioned(ring(),{'a':np.ones(8,int)},5)
    with pytest.raises(ValueError):estimate_conditioned(ring(),{'a':np.ones(8,bool),'b':np.ones(8,bool)},5)
    with pytest.raises(ValueError):estimate_conditioned(ring(),{'a':np.arange(8)<2},5)
    M=np.eye(8);M[0,1]=.1;M[0,0]=.9
    with pytest.raises(ValueError):estimate_conditioned(M,masks(),5)


def test_invalid_nonlinear_return_is_not_silently_dropped():
    e=estimate_conditioned(eye(8),masks(),8,probes=20)
    e.samples[:,:,2]=-1
    assert probe_effect(e,[2],replicates=20)['CI95_probe_only'] is None
    with pytest.raises(ValueError):probe_effect(e,[0],replicates=20)
    with pytest.raises(ValueError):probe_effect(e,[1,1],replicates=20)
