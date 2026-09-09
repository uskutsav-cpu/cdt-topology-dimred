"""Exact sparse propagation with full displacement distributions, not sqrt-time assumptions."""
from __future__ import annotations
import numpy as np
from cdt_mechanisms.graph import adjacency, checked_roots, degrees, distances
from cdt_mechanisms.diffusion import transition, log_slope


def propagate(value,roots,max_steps,*,moving_probability=.5,batch_size=32,max_work=500_000_000):
    a=adjacency(value);roots=checked_roots(roots,len(a.indptr)-1);n=a.shape[0]
    if isinstance(max_steps,bool) or not isinstance(max_steps,int) or max_steps<4: raise ValueError('max_steps>=4 required')
    if not isinstance(batch_size,int) or batch_size<1: raise ValueError('batch_size>=1 required')
    if a.nnz*len(roots)*max_steps>max_work: raise ValueError('propagation work budget exceeded')
    pt=transition(a,moving_probability).T.tocsr();nt=max_steps+1
    ret=np.empty((len(roots),nt));msd=np.empty_like(ret);mean=np.empty_like(ret)
    hist=np.zeros((nt,n));err=0.
    for lo in range(0,len(roots),batch_size):
        rr=roots[lo:lo+batch_size];b=len(rr);ix=np.arange(b)
        d=distances(a,rr).T.astype(np.int64);d2=d*d
        state=np.zeros((n,b));state[rr,ix]=1.
        for t in range(nt):
            ret[lo:lo+b,t]=state[rr,ix];msd[lo:lo+b,t]=np.sum(state*d2,axis=0)
            mean[lo:lo+b,t]=np.sum(state*d,axis=0)
            hist[t]+=np.bincount(d.ravel(),weights=state.ravel(),minlength=n)
            err=max(err,float(np.max(np.abs(state.sum(axis=0)-1))))
            if t<max_steps:state=pt@state
    hist/=len(roots);last=int(np.max(np.flatnonzero(hist.sum(axis=0)>0)))+1;hist=hist[:,:last]
    if err>1e-9 or not np.allclose(hist.sum(axis=1),1,atol=1e-10):raise ArithmeticError('mass conservation failed')
    cdf=np.cumsum(hist,axis=1);quantiles={str(q):np.argmax(cdf>=q,axis=1) for q in [.5,.9]}
    sigma=np.arange(nt);ds=-2*log_slope(sigma,ret);full=ret.mean(axis=0);full_ds=-2*log_slope(sigma,full)
    stationary=degrees(a)[roots]/degrees(a).sum();above=ret>2*stationary[:,None]
    valid=np.zeros_like(above)
    for j in range(2,nt-2): valid[:,j]=above[:,j-2:j+3].all(axis=1)&np.isfinite(ds[:,j])
    return dict(roots=roots,sigma=sigma,returns=ret,msd=msd,mean_distance=mean,ds=ds,
        stationary=stationary,pre_mix=valid,full_return=full,full_ds=full_ds,
        distance_distribution=hist,median_distance=quantiles['0.5'],q90_distance=quantiles['0.9'],
        rms_distance=np.sqrt(msd.mean(axis=0)),mass_error=err,moving_probability=moving_probability,
        full_root_census=bool(len(roots)==n))
