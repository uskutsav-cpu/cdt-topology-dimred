import numpy as np
import pytest
from cdt_mechanisms.inference import *
from cdt_mechanisms.scales import *


def fixture(seed=1):
    rng=np.random.default_rng(seed); n=800
    chain=np.repeat(np.arange(20),40); cfg=np.repeat(np.arange(80),10)
    control=rng.normal(size=(n,2)); x=control[:,0]+rng.normal(size=n)
    y=-.75*x+.9*control[:,0]-.4*control[:,1]+rng.normal(size=80)[cfg]+rng.normal(scale=.1,size=n)
    return x,y,control,cfg,chain

@pytest.mark.parametrize('seed',range(12))
def test_known_within_coefficient(seed):
    x,y,c,cfg,chain=fixture(seed); result=within_effect(x,y,c,cfg,chain)
    assert abs(result['coefficient']+.75)<.02
    assert result['independent_chains']==20 and result['status']=='clustered_estimate'
    assert not result['causal_claim']

def test_within_no_pseudoreplication():
    x,y,c,cfg,chain=fixture()
    with pytest.raises(ValueError,match='independent chains'): within_effect(x,y,c,cfg,np.zeros(len(x)))

def test_configuration_straddles_chains_rejected():
    x,y,c,cfg,chain=fixture(); chain[0]=19
    with pytest.raises(ValueError,match='multiple chains'): within_effect(x,y,c,cfg,chain)

def test_no_exposure_overlap():
    x,y,c,cfg,chain=fixture(); x=cfg.astype(float)
    with pytest.raises(ValueError,match='no independent'): within_effect(x,y,c,cfg,chain)

def test_collinear_exposure():
    x,y,c,cfg,chain=fixture(); c=np.column_stack([c,x])
    with pytest.raises(ValueError,match='no independent'): within_effect(x,y,c,cfg,chain)

def test_constant_controls_counted_not_fake_effect():
    x,y,c,cfg,chain=fixture(); c=np.column_stack([c,np.ones(len(x)),c[:,0]])
    r=within_effect(x,y,c,cfg,chain)
    assert r['constant_or_redundant_controls']==2

def test_small_cluster_warning():
    x,y,c,cfg,chain=fixture(); chain=chain//10
    r=within_effect(x,y,c,cfg,chain)
    assert r['status']=='exploratory_few_clusters'

@pytest.mark.parametrize('seed',range(8))
def test_matching_exact_covariates(seed):
    rng=np.random.default_rng(seed); c=rng.normal(size=(20,3))
    r=matched_pairs(np.repeat([0,1],20),np.vstack([c,c]),np.zeros(40),caliper=.001)
    assert r['n_pairs']==20 and r['balance_pass'] and r['unmatched']==0
    assert all(distance==0 for _,_,distance in r['pairs'])

def test_matching_unsupported_strata():
    x=np.repeat([0,1],4); c=np.arange(8)[:,None]
    r=matched_pairs(x,c,x,caliper=1)
    assert r['n_pairs']==0 and r['status']=='insufficient_overlap'
    assert len(r['unsupported_strata'])==2

def test_matching_caliper_enforced():
    x=np.repeat([0,1],4); c=np.r_[np.arange(4),100+np.arange(4)][:,None]
    r=matched_pairs(x,c,np.zeros(8),caliper=.01)
    assert r['n_pairs']==0 and r['standardized_difference_after'] is None

def test_matching_memory_guard():
    with pytest.raises(ValueError,match='budget'):
        matched_pairs(np.repeat([0,1],4),np.arange(8)[:,None],np.zeros(8),max_pairs_matrix=2)

def test_balance_zero_variance():
    np.testing.assert_equal(standardized_difference(np.ones((4,2)),np.ones((4,2))),[0,0])
    assert np.isinf(standardized_difference(np.ones((4,1)),np.zeros((4,1)))[0])

def test_coupling_simpson_decomposition():
    group=np.repeat([0,1,2],10); within=np.tile(np.arange(10)/10,3)
    x=group+within; y=2*group-within
    r=coupling_decomposition(x,y,group)
    assert r['between_coupling_slope']>0 and r['within_coupling_slope']<0
    assert r['descriptive_only'] and not r['causal_claim']

def test_chain_bootstrap_keeps_chain_average():
    y=np.repeat(np.arange(10),5)[:,None]*np.array([[1.,2.]])
    ids=np.repeat(np.arange(10),5)
    r=chain_bootstrap_curves(y,ids,repetitions=199)
    np.testing.assert_allclose(r['mean'],[4.5,9])
    assert r['independent_chains']==10
    with pytest.raises(ValueError): chain_bootstrap_curves(y,np.zeros(50))

@pytest.mark.parametrize('seed',range(6))
def test_max_scan_positive_signal(seed):
    rng=np.random.default_rng(seed); x=rng.normal(size=(48,4)); y=rng.normal(size=(48,5)); y[:,2]=x[:,1]
    r=max_statistic_scan(x,y,np.arange(48),permutations=99,seed=seed)
    assert r['global_p']==.01 and r['adjusted_p'][1,2]==.01
    assert np.isclose(r['correlation'][1,2],1.)

def test_max_scan_deterministic_and_constant_column():
    rng=np.random.default_rng(99); x=rng.normal(size=(30,3)); x[:,0]=1; y=rng.normal(size=(30,4))
    a=max_statistic_scan(x,y,np.arange(30),permutations=99,seed=91)
    b=max_statistic_scan(x,y,np.arange(30),permutations=99,seed=91)
    assert np.isnan(a['adjusted_p'][0]).all()
    np.testing.assert_allclose(a['null_maxima'],b['null_maxima'])
    assert np.all(a['adjusted_p'][1:]>=.01)

def test_max_scan_duplicate_units_rejected():
    x=np.arange(20)[:,None]
    with pytest.raises(ValueError,match='distinct'): max_statistic_scan(x,x,np.zeros(20),permutations=99)

def test_max_scan_exchangeability_guard():
    x=np.arange(20)[:,None]
    with pytest.raises(ValueError,match='exchangeable'): max_statistic_scan(x,x,np.arange(20),strata=np.arange(20),permutations=99)

def test_max_scan_all_constant():
    with pytest.raises(ValueError,match='constant'):
        max_statistic_scan(np.ones((20,3)),np.ones((20,2)),np.arange(20),permutations=99)

def test_partial_correlation_removes_confounder():
    rng=np.random.default_rng(18); c=rng.normal(size=(1000,1))
    x=c+rng.normal(scale=.01,size=(1000,1)); y=c+rng.normal(scale=.01,size=(1000,1))
    assert residual_correlations(x,y)[0,0]>.99
    assert abs(residual_correlations(x,y,c)[0,0])<.1

def test_ridge_selection_uses_training_only():
    rng=np.random.default_rng(771); x=rng.normal(size=(80,4)); y=x[:,[0,1,2,3]]
    xv=rng.normal(size=(80,4)); yv=-xv
    result=held_out_ridge(x,y,xv,yv,[1,2,4,8],[1,2,4,8],[1,4,16,64])
    assert result['selected_radius']==[1.,2.,4.,8.]
    assert all(v<-.99 for v in result['signed_replication_score'])
    assert abs(result['descriptive_ridge_exponent']-.5)<1e-12
    assert not result['confirmatory']
