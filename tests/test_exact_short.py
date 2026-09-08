import numpy as np
from spectral import operator,exact_returns
from spectral_exact_short import diagonal_returns,batched_diagonal_returns

def test_sparse_half_powers_equal_direct_returns():
    nb=np.array([[(i-1)%15,(i+1)%15] for i in range(15)]);M=operator(nb)
    for steps in [0,1,2,15,16]:
        p,report=diagonal_returns(M,steps)
        assert p.shape==(15,steps+1)
        assert np.allclose(p,exact_returns(M,steps),rtol=1e-13,atol=1e-14)
        assert report['computed_steps']==steps

def test_sparse_limit_reports_partial_result():
    nb=np.array([[(i-1)%15,(i+1)%15] for i in range(15)]);M=operator(nb)
    p,report=diagonal_returns(M,20,max_nnz=46)
    assert report['computed_steps']<20 and report['stop']['reason']=='nnz_limit'
    assert np.allclose(p,exact_returns(M,p.shape[1]-1))

def test_row_batches_preserve_full_graph_diffusion():
    nb=np.array([[(i-1)%15,(i+1)%15] for i in range(15)]);M=operator(nb)
    p,r=batched_diagonal_returns(M,26,max_nnz=60,batch=4)
    assert len(r['batches'])==4 and np.allclose(p,exact_returns(M,26))
