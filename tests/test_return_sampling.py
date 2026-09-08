import numpy as np
from return_sampling import precision_pilot
from spectral import operator,exact_returns

def test_complete_population_has_no_start_sampling_error():
    nb=np.array([[(i-1)%9,(i+1)%9] for i in range(9)]);M=operator(nb)
    r=precision_pilot(M,20,np.arange(9),113,(5,15),batch=10)
    assert len(set(r['starts']))==9 and r['history'][-1]['maximum_relative_se']==0
    assert np.allclose(r['returns'].mean(axis=0),exact_returns(M,20).mean(axis=0))
