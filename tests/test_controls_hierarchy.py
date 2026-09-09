import numpy as np
import pytest
from conditioned_controls import (overlap_weights,weighted_effect,stratified_permutation_test,
                                   configuration_group_folds)
from hierarchical_uncertainty import hierarchical_block_effect


def test_overlap_weights_have_exact_stratum_balance_and_report_exclusions():
    labels=np.array([1,1,1,0,1,0,0,0,1,1],bool)
    strata=np.array([0,0,0,0,1,1,1,1,2,2])
    result=overlap_weights(labels,strata);weights=result['weights']
    np.testing.assert_allclose(weights.sum(axis=1),1)
    for h in np.unique(strata):
        assert weights[0,strata==h].sum()==pytest.approx(weights[1,strata==h].sum())
    assert result['excluded_sites']==2
    assert result['overlap_mass_per_class']==2


def test_pure_geometric_confound_removed():
    labels=np.array([1,1,1,0,1,0,0,0],bool);strata=np.array([0]*4+[1]*4)
    curves=np.exp(-(.05+.15*strata[:,None])*np.arange(12))
    weighted=overlap_weights(labels,strata)
    effect=weighted_effect(curves,weighted['weights'],[3,4,5])
    assert effect['A']==pytest.approx(0,abs=1e-14)
    result=stratified_permutation_test(curves,labels,strata,[3,4,5],
        exchangeability_assumption='TEST_ONLY exchangeable within two synthetic bins',replicates=30)
    assert result['p_one_sided']==pytest.approx(1)
    assert not result['assumption_validated_by_code']


def test_directional_null_and_assumption_rejection():
    labels=np.arange(10)<5;strata=np.zeros(10,int)
    curves=np.exp(-np.where(labels,.2,.02)[:,None]*np.arange(14))
    result=stratified_permutation_test(curves,labels,strata,[2,3,4],
        exchangeability_assumption='TEST_ONLY randomized synthetic labels',replicates=99,seed=33)
    assert result['A_observed']>0
    assert 0<result['p_one_sided']<=.1
    with pytest.raises(ValueError):stratified_permutation_test(curves,labels,strata,[2],
        exchangeability_assumption='')
    with pytest.raises(ValueError):overlap_weights(labels,np.arange(10))
    with pytest.raises(ValueError):overlap_weights(labels.astype(int),strata)


def test_configurations_never_leak_across_folds():
    ids=np.repeat(np.arange(9),[1,3,4,7,2,8,1,4,2])
    fold=configuration_group_folds(ids,folds=3,seed=4)
    assert set(fold)=={0,1,2}
    for i in set(ids):assert len(set(fold[ids==i]))==1
    np.testing.assert_array_equal(fold,configuration_group_folds(ids,folds=3,seed=4))
    with pytest.raises(ValueError):configuration_group_folds([1,1,2],folds=3)


def data(seed=0,effect=False):
    rng=np.random.default_rng(seed);chains=[]
    for length in (8,10):
        chain=[]
        for i in range(length):
            config=[]
            for j in range(1+i%3):
                rate=rng.uniform(.03,.1,(3+j,1,1))
                curves=np.exp(-rate*np.arange(15))
                paired=np.repeat(curves,2,axis=1)
                if effect:paired[:,0]*=np.exp(-.1*np.arange(15))
                config.append(paired)
            chain.append(config)
        chains.append(chain)
    return chains


def test_hierarchy_pairing_zero_and_reproducible():
    chains=data()
    a=hierarchical_block_effect(chains,[3,4,5],block_length=2,replicates=30)
    b=hierarchical_block_effect(chains,[3,4,5],block_length=2,replicates=30)
    assert a['A']==0
    np.testing.assert_array_equal(a['bootstrap_A'],0)
    np.testing.assert_array_equal(a['bootstrap_A'],b['bootstrap_A'])
    assert a['configuration_count']==18 and a['chain_count']==2


def test_hierarchy_positive_known_effect_and_estimand():
    a=hierarchical_block_effect(data(effect=True),[3,4,5],block_length=2,replicates=40,seed=12)
    assert a['A']>0 and a['A_CI95'][0]>0
    assert a['invalid_bootstrap_replicates']==0
    assert np.max(np.abs(a['Ds_of_mean_return'][:,1:-1]-a['mean_of_configuration_Ds'][:,1:-1]))>1e-6


def test_hierarchy_budgets_and_empty_units():
    with pytest.raises(RuntimeError):hierarchical_block_effect(data(),[3],block_length=2,
        replicates=20,max_resampled_values=1)
    with pytest.raises(ValueError):hierarchical_block_effect([], [3],block_length=2)
    with pytest.raises(ValueError):hierarchical_block_effect(data(),[0],block_length=2)
    bad=data();bad[0][0]=[]
    with pytest.raises(ValueError):hierarchical_block_effect(bad,[3],block_length=2)
