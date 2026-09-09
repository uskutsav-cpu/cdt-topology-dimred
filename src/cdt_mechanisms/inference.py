"""Overlap-aware controls and chain-clustered, configuration-fixed-effect inference.

Starting points are NOT independent ensemble samples. Statistical significance
from a single graph/configuration or a single chain is intentionally refused.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import t as student_t


def _finite_vector(x,name,n=None):
    x=np.asarray(x,dtype=float)
    if x.ndim!=1 or not np.isfinite(x).all() or (n is not None and len(x)!=n):
        raise ValueError(f"{name} must be a finite vector of the correct length")
    return x


def demean(x, groups):
    out=np.asarray(x,dtype=float).copy(); groups=np.asarray(groups)
    if groups.shape!=(len(out),): raise ValueError("group length mismatch")
    for g in np.unique(groups): out[groups==g]-=out[groups==g].mean(axis=0)
    return out


def within_effect(x,y,controls,configuration,chain,*,minimum_clusters=8) -> dict:
    x=_finite_vector(x,'x'); y=_finite_vector(y,'y',len(x)); n=len(x)
    c=np.asarray(controls,dtype=float)
    if c.ndim!=2 or c.shape[0]!=n or not np.isfinite(c).all(): raise ValueError("invalid controls")
    config=np.asarray(configuration); cluster=np.asarray(chain)
    if config.shape!=(n,) or cluster.shape!=(n,): raise ValueError("invalid grouping")
    # A configuration may not straddle independent chains.
    for cfg in np.unique(config):
        if len(np.unique(cluster[config==cfg]))!=1: raise ValueError("configuration belongs to multiple chains")
    groups=np.unique(cluster); G=len(groups)
    if G<2: raise ValueError("need >=2 independent chains; many starting points do not replace chains")
    xx=demean(x,config); yy=demean(y,config); cc=demean(c,config)
    if cc.shape[1]:
        u,s,_=np.linalg.svd(cc,full_matrices=False)
        rank=int(np.sum(s>max(cc.shape)*np.finfo(float).eps*(s[0] if len(s) else 1)))
        q=u[:,:rank]; rx=xx-q@(q.T@xx); ry=yy-q@(q.T@yy)
    else: rank=0; rx=xx; ry=yy
    ss=float(rx@rx)
    if ss<1e-12*max(1,float(xx@xx)):
        raise ValueError("exposure has no independent within-configuration variation")
    beta=float(rx@ry/ss); residual=ry-beta*rx
    dof=n-len(np.unique(config))-rank-1
    if dof<=0: raise ValueError("insufficient residual degrees of freedom")
    scores=np.asarray([np.sum(rx[cluster==g]*residual[cluster==g]) for g in groups])
    variance=float(G/(G-1)*(n-1)/dof*(scores@scores)/(ss*ss))
    se=float(np.sqrt(max(variance,0))); critical=float(student_t.ppf(.975,G-1))
    p=float(2*student_t.sf(abs(beta/se),G-1)) if se>0 else (0. if beta else 1.)
    return dict(coefficient=beta,cluster_standard_error=se,
                ci95=[beta-critical*se,beta+critical*se],p_value=p,
                independent_chains=G,configurations=len(np.unique(config)),n_rows=n,
                control_rank=rank,constant_or_redundant_controls=c.shape[1]-rank,
                residual_dof=dof,approximate_inference=True,
                status='exploratory_few_clusters' if G<minimum_clusters else 'clustered_estimate',
                causal_claim=False)


def standardized_difference(a,b) -> np.ndarray:
    a=np.asarray(a,dtype=float); b=np.asarray(b,dtype=float)
    if a.ndim!=2 or b.ndim!=2 or a.shape[1]!=b.shape[1] or min(len(a),len(b))<2:
        raise ValueError("each group needs >=2 rows with identical columns")
    if not np.isfinite(a).all() or not np.isfinite(b).all(): raise ValueError("nonfinite balance input")
    diff=a.mean(axis=0)-b.mean(axis=0); den=np.sqrt((a.var(axis=0,ddof=1)+b.var(axis=0,ddof=1))/2)
    out=np.zeros_like(diff); nonzero=den>1e-12
    out[nonzero]=diff[nonzero]/den[nonzero]
    out[~nonzero & (np.abs(diff)>1e-12)]=np.inf*np.sign(diff[~nonzero & (np.abs(diff)>1e-12)])
    return out


def matched_pairs(exposure,controls,strata,*,caliper=1.,max_pairs_matrix=4_000_000) -> dict:
    """Maximum-cardinality within-stratum matching using pre-outcome covariates.

    Standardization uses eligible pooled controls, NOT outcomes. A large dummy
    assignment penalty prioritizes match cardinality over distance. Unsupported
    strata are explicitly excluded; never extrapolate across no-overlap regions.
    """
    z=np.asarray(exposure); c=np.asarray(controls,dtype=float); groups=np.asarray(strata)
    if z.ndim!=1 or not np.isin(z,[0,1]).all() or c.ndim!=2 or len(c)!=len(z) or c.shape[1]<1 or not np.isfinite(c).all():
        raise ValueError("invalid binary exposure or controls")
    if groups.shape!=z.shape or not np.isfinite(caliper) or caliper<=0: raise ValueError("invalid strata/caliper")
    if min(np.sum(z==0),np.sum(z==1))<2: raise ValueError("both exposure classes need >=2 starts")
    mean=c.mean(axis=0); scale=c.std(axis=0,ddof=1); scale[scale<1e-12]=1
    cc=(c-mean)/scale; pairs=[]; omitted=[]
    for group in np.unique(groups):
        hi=np.flatnonzero((groups==group)&(z==1)); lo=np.flatnonzero((groups==group)&(z==0))
        if not len(hi) or not len(lo): omitted.append(str(group)); continue
        if len(hi)*(len(lo)+len(hi))>max_pairs_matrix: raise ValueError("matching memory budget exceeded")
        distance=np.linalg.norm(cc[hi,None,:]-cc[None,lo,:],axis=2)
        penalty=(len(hi)+1)*(caliper+1)
        cost=np.full((len(hi),len(lo)+len(hi)),penalty)
        cost[:,:len(lo)]=np.where(distance<=caliper,distance,2*penalty)
        rows,cols=linear_sum_assignment(cost)
        for row,col in zip(rows,cols):
            if col<len(lo) and distance[row,col]<=caliper:
                pairs.append((int(hi[row]),int(lo[col]),float(distance[row,col])))
    before=standardized_difference(c[z==1],c[z==0]).tolist()
    if len(pairs)>=2:
        after=standardized_difference(c[[p[0] for p in pairs]],c[[p[1] for p in pairs]]).tolist()
    else: after=None
    return dict(pairs=pairs,n_pairs=len(pairs),unmatched=int(len(z)-2*len(pairs)),
                standardized_difference_before=before,standardized_difference_after=after,
                unsupported_strata=omitted,caliper=caliper,
                status='overlap_present' if len(pairs)>=2 else 'insufficient_overlap',
                balance_pass=bool(after is not None and np.all(np.abs(after)<=.1)),
                causal_claim=False)


def chain_bootstrap_curves(values,chains,*,repetitions=499,seed=0) -> dict:
    """Equal-chain mean bootstrap; all correlated configurations remain together.

    Inputs are per-configuration curves, not individual starting-point outcomes.
    This does not replace MCMC equilibration and autocorrelation diagnostics.
    """
    y=np.asarray(values,dtype=float); ids=np.asarray(chains)
    if y.ndim!=2 or ids.shape!=(len(y),) or not np.isfinite(y).all(): raise ValueError("invalid curves/chains")
    unique=np.unique(ids)
    if len(unique)<2: raise ValueError("need >=2 independent chains")
    if not isinstance(repetitions,int) or repetitions<99: raise ValueError("need >=99 bootstrap draws")
    means=np.asarray([y[ids==g].mean(axis=0) for g in unique]); rng=np.random.default_rng(seed)
    draws=means[rng.integers(len(means),size=(repetitions,len(means)))].mean(axis=1)
    return dict(mean=means.mean(axis=0),lower=np.quantile(draws,.025,axis=0),
                upper=np.quantile(draws,.975,axis=0),independent_chains=len(unique),
                status='exploratory_few_clusters' if len(unique)<8 else 'cluster_bootstrap',
                repetitions=repetitions)


def coupling_decomposition(x,y,couplings) -> dict:
    """Descriptive within/between coupling slopes, with NO natural-experiment claim."""
    x=_finite_vector(x,'x'); y=_finite_vector(y,'y',len(x)); group=np.asarray(couplings)
    if group.shape!=x.shape or len(np.unique(group))<2: raise ValueError("need >=2 coupling levels")
    levels=np.unique(group); xm=np.asarray([x[group==g].mean() for g in levels]); ym=np.asarray([y[group==g].mean() for g in levels])
    dx=demean(x,group); dy=demean(y,group)
    def slope(a,b):
        a=a-a.mean(); b=b-b.mean(); ss=float(a@a)
        return float(a@b/ss) if ss>1e-12 else None
    return dict(levels=levels.tolist(),mean_exposure=xm.tolist(),mean_outcome=ym.tolist(),
                between_coupling_slope=slope(xm,ym),within_coupling_slope=slope(dx,dy),
                descriptive_only=True,causal_claim=False)
