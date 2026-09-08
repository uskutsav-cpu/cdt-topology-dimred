import numpy as np
from diagnostics import rank_split_rhat

def test_rank_rhat_detects_location_scale_and_drift():
    x=np.random.default_rng(143).normal(size=(4,4000))
    assert rank_split_rhat(x)<1.01
    shifted=x+np.arange(4)[:,None]
    scaled=x*np.array([1,1,4,4])[:,None]
    drifted=x+np.linspace(-3,3,4000)
    assert rank_split_rhat(shifted)>1.1
    assert rank_split_rhat(scaled)>1.1
    assert rank_split_rhat(drifted)>1.1

def test_rank_rhat_constant_and_chain_order():
    x=np.random.default_rng(144).integers(0,20,size=(4,401))
    assert rank_split_rhat(x)==rank_split_rhat(x[::-1])
    assert np.isnan(rank_split_rhat(np.ones((2,100))))
