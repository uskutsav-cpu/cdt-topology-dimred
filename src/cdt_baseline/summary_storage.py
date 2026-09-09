"""Exact per-geometry reductions avoid retaining the root dimension in memory.

The raw root curves remain in immutable NPZ evidence. This is not statistical
compression: the means, nested-half estimate, and full root jackknife variance
are exactly the quantities needed by the declared downstream analysis.
"""
from dataclasses import dataclass
import numpy as np
from .statistics import dimension

@dataclass(frozen=True)
class RootSummary:
    shape: tuple
    mean: np.ndarray
    half_ds: np.ndarray
    root_variance: np.ndarray


def reduce_roots(returns,population):
    p=np.asarray(returns,float)
    if p.ndim!=2 or p.shape[0]<2 or p.shape[1]<3 or not np.isfinite(p).all() or np.any(p<0):
        raise ValueError('expected finite nonnegative root x time curves with >=2 roots')
    R,L=p.shape
    if type(population) not in (int,float) or not np.isfinite(population) or population<R:
        raise ValueError('root population smaller than sample')
    mean=p.mean(axis=0);half=dimension(p[:max(2,R//2)].mean(axis=0))
    leave=(p.sum(axis=0,keepdims=True)-p)/(R-1);ds=dimension(leave)
    center=ds[:,1:-1].mean(axis=0,keepdims=True)
    variance=np.zeros(L)
    variance[1:-1]=(R-1)/R*np.sum((ds[:,1:-1]-center)**2,axis=0)*(population-R)/(population-1)
    return RootSummary(p.shape,mean,half,variance)

@dataclass(frozen=True)
class CompactRootCube:
    shape: tuple
    means: np.ndarray
    half_ds: np.ndarray
    root_error: np.ndarray

    @classmethod
    def from_summaries(cls,values,chains,draws):
        if set(values)!={(c,s) for c in range(chains) for s in range(draws)}:
            raise ValueError('missing or duplicate chain/geometry reductions')
        shapes={v.shape for v in values.values()}
        if len(shapes)!=1:raise ValueError('unequal root counts or diffusion horizons')
        R,L=next(iter(shapes))
        means=np.array([[values[c,s].mean for s in range(draws)] for c in range(chains)])
        half=np.array([[values[c,s].half_ds for s in range(draws)] for c in range(chains)])
        variance=np.array([[values[c,s].root_variance for s in range(draws)] for c in range(chains)])
        error=np.sqrt(variance.sum(axis=(0,1)))/(chains*draws)
        return cls((chains,draws,R,L),means,half,error)
