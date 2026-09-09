"""Chain-aware diagnostics and uncertainty; no data-selected equilibration cuts."""
from __future__ import annotations
import warnings
import numpy as np
from scipy.signal import savgol_filter
import arviz as az


def dimension(P):
    """Cooperman Eq. (3.10), along the last axis; endpoints are undefined."""
    p=np.asarray(P,float)
    if p.ndim<1 or p.shape[-1]<3:raise ValueError('return curve needs at least three times')
    result=np.full_like(p,np.nan);s=np.arange(1,p.shape[-1]-1)
    good=np.isfinite(p[...,1:-1])&(p[...,1:-1]>0)&np.isfinite(p[...,2:])&np.isfinite(p[...,:-2])&(p[...,2:]>=0)&(p[...,:-2]>=0)
    with np.errstate(divide='ignore',invalid='ignore'):
        result[...,1:-1]=np.where(good,-s*(p[...,2:]-p[...,:-2])/p[...,1:-1],np.nan)
    return result


def log_dimension(P,window=7):
    """Secondary derivative estimator on a uniform log-time interpolation grid."""
    p=np.asarray(P,float)
    if p.ndim!=1 or len(p)<window+3 or window%2!=1 or window<5:raise ValueError('invalid derivative window')
    result=np.full_like(p,np.nan)
    if not np.isfinite(p[1:]).all() or np.any(p[1:]<=0):return result
    x=np.log(np.arange(1,len(p)));u=np.linspace(x[0],x[-1],len(x))
    y=np.interp(u,x,np.log(p[1:]));der=savgol_filter(y,window,2,deriv=1,delta=u[1]-u[0])
    result[1:]=-2*np.interp(x,u,der);result[1:1+window//2]=np.nan;result[-window//2:]=np.nan
    return result


def diagnostic(x,limits):
    x=np.asarray(x,float)
    if x.ndim!=2 or x.shape[0]<2 or x.shape[1]<8 or not np.isfinite(x).all():
        return dict(pass_screen=False,reason='insufficient/non-finite chain array')
    if any(np.ptp(row)==0 for row in x):return dict(pass_screen=False,reason='constant chain is not evidence of mixing')
    if any(np.array_equal(x[i],x[j]) for i in range(len(x)) for j in range(i)):
        return dict(pass_screen=False,reason='identical traces are not independent-chain confirmation')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        values=dict(rank_folded_rhat=float(az.rhat(x,method='rank')),
                    bulk_ess=float(az.ess(x,method='bulk')),
                    tail_ess=float(az.ess(x,method='tail',prob=(.05,.95))),
                    mean_ess=float(az.ess(x,method='mean')),
                    mean_mcse=float(az.mcse(x,method='mean')))
    sd=float(x.std(ddof=1));values['mean_mcse_over_sd']=values['mean_mcse']/sd
    values.update(chains=x.shape[0],draws_per_chain=x.shape[1],chain_means=x.mean(axis=1).tolist(),
                  mean=float(x.mean()),sd=sd,split_mean_difference=float(x[:,x.shape[1]//2:].mean()-x[:,:x.shape[1]//2].mean()))
    checks=dict(finite=all(np.isfinite(v) for v in values.values() if isinstance(v,(float,int))),
                rhat=values['rank_folded_rhat']<=limits['rhat'],bulk=values['bulk_ess']>=limits['bulk_ess'],
                tail=values['tail_ess']>=limits['tail_ess'],mcse=values['mean_mcse_over_sd']<=limits['mean_mcse_sd'])
    values.update(checks=checks,pass_screen=all(checks.values()),tau_proxy=float(x.size/max(values['bulk_ess'],1e-30)))
    return values


def moving_block_indices(draws,block,rng):
    if type(draws) is not int or type(block) is not int or draws<1 or not 1<=block<=draws:
        raise ValueError('invalid circular moving-block dimensions')
    starts=rng.integers(draws,size=(draws+block-1)//block)
    return ((starts[:,None]+np.arange(block))%draws).ravel()[:draws]


def root_jackknife(P,population):
    """Root-mean/derivative jackknife, including finite-population correction."""
    p=np.asarray(P,float)
    if p.ndim!=4 or p.shape[2]<2:raise ValueError('need chain, geometry, root, time array and >=2 roots')
    R=p.shape[2];pop=np.asarray(population,float)
    if pop.shape!=p.shape[:2] or np.any(pop<R):raise ValueError('invalid root population sizes')
    leave=(p.sum(axis=2,keepdims=True)-p)/(R-1);ds=dimension(leave)
    center=ds[...,1:-1].mean(axis=2,keepdims=True)
    v=(R-1)/R*np.sum((ds[...,1:-1]-center)**2,axis=2)
    fpc=(pop-R)/(pop-1)
    var=np.zeros(p.shape[:2]+(p.shape[-1],));var[...,1:-1]=v*fpc[...,None]
    return np.sqrt(var.sum(axis=(0,1)))/(p.shape[0]*p.shape[1])


def block_curves(P,block,replicates,seed,*,chain_resampling=True):
    """Resample geometries in blocks inside a sampled independent chain.

    We do not pretend roots are independent Markov-chain states. Root sampling
    error is reported separately; a conservative additive jackknife margin may
    widen the block interval (the two contributions need not be independent).
    """
    p=np.asarray(P,float)
    if p.ndim!=3 or p.shape[0]<2 or p.shape[1]<2 or not np.isfinite(p).all() or np.any(p<0):
        raise ValueError('expected chain x configuration x time return probabilities')
    if type(replicates) is not int or replicates<20:raise ValueError('insufficient bootstrap replicates')
    C,S,L=p.shape;ds=dimension(p);rng=np.random.default_rng(seed)
    mean_ds=np.empty((replicates,L));annealed=np.empty_like(mean_ds)
    for b in range(replicates):
        chains=rng.integers(C,size=C) if chain_resampling else np.arange(C)
        ids=np.array([moving_block_indices(S,block,rng) for _ in chains]);sample=p[chains[:,None],ids]
        mean_ds[b]=ds[chains[:,None],ids].mean(axis=(0,1))
        annealed[b]=dimension(sample.mean(axis=(0,1)))
    return mean_ds,annealed
