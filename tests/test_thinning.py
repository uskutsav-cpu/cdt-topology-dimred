import numpy as np
import pytest
from spectral import operator,exact_returns
from spectral_thinning import thin_returns

def test_thinning_equals_direct_slower_walk_and_bounds_truncation():
    nb=np.array([[(i-1)%19,(i+1)%19] for i in range(19)])
    old=exact_returns(operator(nb,.8),24,starts=np.array([0,7]))
    got,tail=thin_returns(old,.5,24)
    assert np.allclose(got,exact_returns(operator(nb,.4),24,starts=np.array([0,7])),rtol=1e-13,atol=1e-14)
    bounded,tail=thin_returns(old,.25,64,max_tail=.02)
    truth=exact_returns(operator(nb,.2),64,starts=np.array([0,7]))
    assert np.all(truth-bounded>=-1e-14)
    assert np.all(truth-bounded<=tail+1e-14)
    with pytest.raises(ValueError):thin_returns(old,.8,64)
