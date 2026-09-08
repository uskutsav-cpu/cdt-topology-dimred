import numpy as np
import pytest
from scipy.sparse import csr_matrix
from spectral import operator, exact_returns, dimension
from conditioned import partition_returns, decompose_dimension, checked_operator
from uncertainty import paired_block_effect, circular_block_indices


def cycle(n):
    return np.array([[(i-1)%n,(i+1)%n] for i in range(n)])


def test_partition_exact_matrix_powers_and_unchanged_operator():
    m = operator(cycle(13))
    before = m.copy()
    mask = np.arange(13) < 4
    out = partition_returns(m, {'regular':mask,'other':~mask}, 25, block_size=3)
    exact = np.stack([np.diag(np.linalg.matrix_power(m.toarray(), s)) for s in range(26)], axis=1)
    assert np.allclose(out['P_class'][0], exact[mask].mean(axis=0), atol=1e-14)
    assert np.allclose(out['P_all'], exact.mean(axis=0), atol=1e-14)
    assert (m != before).nnz == 0
    assert decompose_dimension(out['P_class'], out['counts'])['maximum_identity_error'] < 1e-12


def test_condensate_starts_do_not_excise_operator():
    m = operator(cycle(9))
    start = np.arange(9) < 5
    a = np.arange(9) < 2
    b = start & ~a
    out = partition_returns(m, {'a':a,'b':b}, 10, start_mask=start, block_size=2)
    assert np.allclose(out['P_all'], exact_returns(m,10,np.flatnonzero(start)).mean(axis=0))
    assert out['start_count'] == 5


def test_return_weights_not_size_weights():
    curves = np.array([np.exp(-.35*np.arange(30)), np.exp(-.01*np.arange(30))])
    out = decompose_dimension(curves, [99,1])
    assert out['weights'][1,20] > .8  # one percent of starts can dominate returns
    assert out['maximum_identity_error'] < 1e-12
    assert not np.allclose(out['Ds_all'][1:-1], ([.99,.01] @ dimension(curves))[1:-1])


@pytest.mark.parametrize('bad', [np.ones((2,3)), [[1,0],[-.1,1.1]], [[.5,.5],[0,1]], [[.5,0],[0,.5]]])
def test_invalid_transition(bad):
    with pytest.raises(ValueError):
        checked_operator(bad)


def test_duplicate_sparse_entries_do_not_mutate_original():
    m = csr_matrix((np.array([.25,.25,.5,.5,.5]),np.array([0,0,1,0,1]),np.array([0,3,5])),shape=(2,2))
    before = (m.data.copy(),m.indices.copy(),m.indptr.copy())
    checked_operator(m)
    assert all(np.array_equal(a,b) for a,b in zip(before,(m.data,m.indices,m.indptr)))


def test_invalid_masks_steps_and_block_size():
    m = operator(cycle(5))
    with pytest.raises(ValueError):
        partition_returns(m, {'a':np.ones(5,bool),'b':np.ones(5,bool)}, 5)
    with pytest.raises(ValueError):
        partition_returns(m, {'a':np.ones(5)}, 5)
    for bad in (-1, 1.5, True):
        with pytest.raises(ValueError):
            partition_returns(m, {'a':np.ones(5,bool)}, bad)
    with pytest.raises(ValueError):
        partition_returns(m, {'a':np.ones(5,bool)}, 5, block_size=0)


def make_chains():
    rng = np.random.default_rng(42)
    time = np.arange(24)
    return [np.exp(-rng.uniform(.02,.15,(48,2,1))*time) for _ in range(2)]


def test_paired_bootstrap_preserves_exact_zero_null():
    chains = make_chains()
    for c in chains:
        c[:,1] = c[:,0]
    result = paired_block_effect(chains, [5,6,7,8], block_length=6, replicates=60, seed=2)
    assert result['A'] == 0
    assert np.all(result['bootstrap_A'] == 0)
    assert np.all(result['A_CI95'] == 0)


def test_bootstrap_reproducible_and_estimands_explicit():
    a = paired_block_effect(make_chains(), [5,6,7,8], block_length=4, replicates=80, seed=3)
    b = paired_block_effect(make_chains(), [5,6,7,8], block_length=4, replicates=80, seed=3)
    assert np.array_equal(a['bootstrap_A'], b['bootstrap_A'])
    assert not np.allclose(a['Ds_of_mean_return'][:,5:15], a['mean_of_configuration_Ds'][:,5:15])
    assert a['configuration_count'] == 96


def test_block_indices_are_contiguous_inside_blocks():
    idx = circular_block_indices(24,6,np.random.default_rng(5)).reshape(4,6)
    assert np.all(np.diff(idx,axis=1) % 24 == 1)
    with pytest.raises(ValueError):
        circular_block_indices(10,6,np.random.default_rng(1))


@pytest.mark.parametrize('window', [[], [0,1], [23], [3,3], [2.5]])
def test_invalid_analysis_window(window):
    with pytest.raises(ValueError):
        paired_block_effect(make_chains(), window, block_length=4, replicates=40)
