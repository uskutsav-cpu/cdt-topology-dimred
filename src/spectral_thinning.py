"""Obtain slower lazy-walk returns from a saved faster-walk sequence."""
import numpy as np
from scipy.stats import binom

def thin_returns(returns,q,steps,max_tail=1e-12):
    """For M_new=(1-q)I+q M_old, binomially mix powers of M_old.

    Missing powers contribute at most the omitted binomial mass for Markov
    return probabilities in [0,1]. Raise if this absolute bound is too large.
    """
    P=np.asarray(returns,float)
    if P.ndim<1 or P.shape[-1]<1 or not np.isfinite(P).all() or np.any((P<0)|(P>1)):
        raise ValueError('finite return probabilities required')
    if not 0<q<=1 or steps<0:raise ValueError('invalid thinning ratio or steps')
    k=np.arange(P.shape[-1]);s=np.arange(steps+1)
    weights=binom.pmf(k[None,:],s[:,None],q)
    tail=binom.sf(len(k)-1,s,q)
    if tail.max()>max_tail:raise ValueError('insufficient saved powers for requested tail bound')
    return P@weights.T,tail
