"""Independent-unit tests, prespecified directions, and cluster-aware diagnostics."""
from __future__ import annotations
import numpy as np
from cdt_mechanisms.inference import within_effect,demean


def paired_vectors(x,y,min_n=4):
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
    if x.ndim!=1 or y.shape!=x.shape or len(x)<min_n or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('finite paired independent-unit vectors required')
    if np.std(x)<1e-14 or np.std(y)<1e-14:raise ValueError('constant variable: correlation undefined')
    return x,y


def correlation_test(x,y,*,direction='negative',permutations=9999,bootstraps=4999,seed=0):
    x,y=paired_vectors(x,y)
    if direction not in ['negative','positive','two-sided'] or permutations<99 or bootstraps<99:raise ValueError('invalid testing settings')
    n=len(x);xx=x-x.mean();yy=y-y.mean();xn=xx/np.linalg.norm(xx);yn=yy/np.linalg.norm(yy)
    r=float(xn@yn);slope=float(xx@yy/(xx@xx));rng=np.random.default_rng(seed)
    null=np.asarray([xn@rng.permutation(yn) for _ in range(permutations)])
    if direction=='negative':exceed=null<=r+1e-15
    elif direction=='positive':exceed=null>=r-1e-15
    else:exceed=np.abs(null)>=abs(r)-1e-15
    ix=rng.integers(n,size=(bootstraps,n));bx=x[ix];by=y[ix];bx-=bx.mean(axis=1,keepdims=True);by-=by.mean(axis=1,keepdims=True)
    den=np.sqrt((bx*bx).sum(axis=1)*(by*by).sum(axis=1));valid=den>1e-14
    bc=(bx[valid]*by[valid]).sum(axis=1)/den[valid]
    bs=(bx[valid]*by[valid]).sum(axis=1)/(bx[valid]*bx[valid]).sum(axis=1)
    return dict(n_independent_geometries=n,pearson_r=r,slope=slope,direction=direction,
        permutation_p=float((1+exceed.sum())/(1+permutations)),correlation_ci95=np.quantile(bc,[.025,.975]),
        slope_ci95=np.quantile(bs,[.025,.975]),permutations=permutations,bootstrap_repetitions=bootstraps,
        invalid_bootstrap_draws=int((~valid).sum()),null_distribution=null,causal_claim=False)


def holm(pvalues):
    p=np.asarray(pvalues,dtype=float)
    if p.ndim!=1 or not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('invalid p values')
    order=np.argsort(p);adjusted=np.empty_like(p);running=0.
    for i,j in enumerate(order):running=max(running,(len(p)-i)*p[j]);adjusted[j]=min(1.,running)
    return adjusted


def within_with_null(x,y,controls,configurations,clusters,*,seed=0,permutations=1999):
    estimate=within_effect(x,y,controls,configurations,clusters)
    rng=np.random.default_rng(seed);x=np.asarray(x,dtype=float);cfg=np.asarray(configurations);cl=np.asarray(clusters)
    shuffled=x.copy()
    for g in np.unique(cfg):
        mask=np.flatnonzero(cfg==g);shuffled[mask]=rng.permutation(x[mask])
    destroyed=within_effect(shuffled,y,controls,cfg,cl)
    # Restricted score sign-flips respect clusters; not independent root permutations.
    xx=demean(x,cfg);yy=demean(y,cfg);cc=demean(controls,cfg)
    if cc.shape[1]:
        u,s,_=np.linalg.svd(cc,full_matrices=False);rank=np.sum(s>max(cc.shape)*np.finfo(float).eps*s[0]) if len(s) else 0
        q=u[:,:rank];xx-=q@(q.T@xx);yy-=q@(q.T@yy)
    scores=np.asarray([np.sum(xx[cl==g]*yy[cl==g]) for g in np.unique(cl)])
    norm=np.linalg.norm(scores);obs=float(scores.sum()/norm) if norm else 0.
    null=(rng.choice([-1,1],size=(permutations,len(scores)))@scores)/norm if norm else np.zeros(permutations)
    return dict(estimate=estimate,label_destroyed_estimate=destroyed,
        wild_cluster_score_p=float((1+np.sum(np.abs(null)>=abs(obs)-1e-15))/(permutations+1)),
        wild_cluster_score_statistic=obs,wild_test_assumption='approximately sign-symmetric independent cluster scores',
        root_shuffle_interpretation='diagnostic destruction only; not a valid spatial exchangeability argument')


def paired_effect(differences,*,seed=0,repetitions=4999):
    d=np.asarray(differences,dtype=float)
    if d.ndim!=1 or len(d)<4 or not np.isfinite(d).all() or repetitions<99:raise ValueError('>=4 finite independent paired differences required')
    rng=np.random.default_rng(seed);boot=d[rng.integers(len(d),size=(repetitions,len(d)))].mean(axis=1)
    obs=float(d.mean());null=(rng.choice([-1,1],size=(repetitions,len(d)))*d).mean(axis=1)
    return dict(n_independent_pairs=len(d),mean_difference=obs,ci95=np.quantile(boot,[.025,.975]),
        sign_flip_p=float((1+np.sum(np.abs(null)>=abs(obs)-1e-15))/(repetitions+1)),
        inference='paired independent-unit bootstrap; sign flip assumes symmetric paired null')
