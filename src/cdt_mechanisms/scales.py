"""Exploration-scale fits and multiplicity-aware delta-by-sigma scans."""
from __future__ import annotations
import numpy as np


def _matrix(value,name):
    x=np.asarray(value,dtype=float)
    if x.ndim!=2 or not np.isfinite(x).all(): raise ValueError(f"{name} must be a finite matrix")
    return x


def _projector(controls,n):
    c=_matrix(controls,'controls')
    if c.shape[0]!=n: raise ValueError("control row count mismatch")
    design=np.column_stack((np.ones(n),c)); u,s,_=np.linalg.svd(design,full_matrices=False)
    rank=int(np.sum(s>max(design.shape)*np.finfo(float).eps*s[0]))
    return u[:,:rank],rank


def residual_correlations(features,outcomes,controls=None) -> np.ndarray:
    x=_matrix(features,'features'); y=_matrix(outcomes,'outcomes')
    if len(x)!=len(y) or len(x)<4: raise ValueError("at least four paired rows required")
    if controls is None: controls=np.empty((len(x),0))
    q,rank=_projector(controls,len(x))
    if len(x)-rank<3: raise ValueError("insufficient residual degrees of freedom")
    x=x-q@(q.T@x); y=y-q@(q.T@y)
    xx=np.sqrt(np.sum(x*x,axis=0)); yy=np.sqrt(np.sum(y*y,axis=0))
    denom=np.outer(xx,yy); out=np.full(denom.shape,np.nan)
    valid=denom>1e-12
    np.divide(x.T@y,denom,out=out,where=valid)
    return np.clip(out,-1.,1.)


def max_statistic_scan(features,outcomes,unit_ids,*,controls=None,strata=None,
                        permutations=499,seed=0) -> dict:
    """Freedman-Lane residual permutation, maximum |partial correlation| family.

    Each row MUST represent one independent unit (usually one independent chain
    aggregate, not one start). The p-values assume exchangeable residuals within
    the declared strata. With nuisance covariates this is an approximate test;
    it is not a replacement for a design-specific randomization argument.
    """
    x=_matrix(features,'features'); y=_matrix(outcomes,'outcomes'); n=len(x)
    ids=np.asarray(unit_ids)
    if len(y)!=n or n<8 or ids.shape!=(n,) or len(np.unique(ids))!=n:
        raise ValueError("need >=8 distinct independent unit IDs; no pseudoreplication")
    if not isinstance(permutations,int) or permutations<99: raise ValueError("need >=99 permutations")
    if controls is None: controls=np.empty((n,0))
    q,rank=_projector(controls,n)
    if n-rank<5: raise ValueError("insufficient residual degrees of freedom")
    if strata is None: strata=np.zeros(n,dtype=int)
    groups=np.asarray(strata)
    if groups.shape!=(n,): raise ValueError("invalid permutation strata")
    blocks=[np.flatnonzero(groups==g) for g in np.unique(groups)]
    if not any(len(b)>1 for b in blocks): raise ValueError("no exchangeable units within strata")
    fitted=q@(q.T@y); residual=y-fitted
    observed=residual_correlations(x,y,controls)
    if not np.any(np.isfinite(observed)): raise ValueError("all scanned exposures/outcomes are constant")
    rng=np.random.default_rng(seed); maxima=[]
    for _ in range(permutations):
        perm=np.arange(n)
        for b in blocks: perm[b]=rng.permutation(b)
        shuffled=fitted+residual[perm]
        r=residual_correlations(x,shuffled,controls)
        maxima.append(float(np.nanmax(np.abs(r))))
    maxima=np.asarray(maxima); adjusted=np.full(observed.shape,np.nan)
    valid=np.isfinite(observed)
    adjusted[valid]=(1+np.sum(maxima[:,None]>=np.abs(observed[valid])[None,:]-1e-15,axis=0))/(permutations+1)
    peak=float(np.nanmax(np.abs(observed)))
    return dict(correlation=observed,adjusted_p=adjusted,null_maxima=maxima,
                global_p=float((1+np.sum(maxima>=peak-1e-15))/(permutations+1)),
                independent_units=n,permutations=permutations,
                assumption='exchangeable independent-unit residuals within strata',
                approximate_with_nuisance_covariates=bool(rank>1),
                family='all supplied feature-scale by diffusion-time cells',causal_claim=False)


def held_out_ridge(features_train,outcomes_train,features_test,outcomes_test,
                    radii,rms_test,sigma) -> dict:
    """Choose peak scale on TRAIN only, evaluate its signed correlation on TEST.

    Radius-matching summaries remain exploratory: this function does not test a
    universal exponent or claim that coarse-graining scale equals a diffusion
    distance. Input feature radii must use the declared matching metric.
    """
    xt=_matrix(features_train,'training features'); yt=_matrix(outcomes_train,'training outcomes')
    xv=_matrix(features_test,'test features'); yv=_matrix(outcomes_test,'test outcomes')
    radii=np.asarray(radii,dtype=float); sigma=np.asarray(sigma,dtype=float); rms=np.asarray(rms_test,dtype=float)
    if radii.shape!=(xt.shape[1],) or sigma.shape!=(yt.shape[1],) or rms.shape!=sigma.shape:
        raise ValueError("scale shapes mismatch")
    if xv.shape[1]!=xt.shape[1] or yv.shape[1]!=yt.shape[1] or min(len(xt),len(xv))<4:
        raise ValueError("need >=4 train/test units and matching dimensions")
    if np.any(radii<=0) or np.any(sigma<=0) or np.any(rms<=0): raise ValueError("positive scales required")
    if not np.isfinite(radii).all() or not np.isfinite(sigma).all() or not np.isfinite(rms).all(): raise ValueError("nonfinite scales")
    train=residual_correlations(xt,yt); test=residual_correlations(xv,yv)
    selected=[]; test_r=[]; score=[]
    for j in range(yt.shape[1]):
        if not np.any(np.isfinite(train[:,j])):
            selected.append(None); test_r.append(None); score.append(None); continue
        k=int(np.nanargmax(np.abs(train[:,j]))); selected.append(float(radii[k]))
        r=float(test[k,j]) if np.isfinite(test[k,j]) else None
        test_r.append(r); score.append(float(np.sign(train[k,j])*r) if r is not None else None)
    valid=np.asarray([r is not None for r in selected]); delta=np.asarray([r if r is not None else np.nan for r in selected])
    def matching_error(distance):
        z=np.log(delta[valid]/distance[valid]); offset=np.mean(z)
        return dict(fitted_c=float(np.exp(offset)),log_rmse=float(np.sqrt(np.mean((z-offset)**2)))) if len(z) else None
    slope=float(np.polyfit(np.log(sigma[valid]),np.log(delta[valid]),1)[0]) if valid.sum()>=3 else None
    return dict(selected_radius=selected,test_correlation=test_r,signed_replication_score=score,
                measured_radius_alignment=matching_error(rms),sqrt_sigma_alignment=matching_error(np.sqrt(sigma)),
                descriptive_ridge_exponent=slope,selection='training data only',confirmatory=False)
