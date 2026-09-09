"""Outcome-blind categorical overlap matching and assumption-explicit nulls.

These routines cannot justify exchangeability, choose covariates, certify
thermalization, or establish causality. Freeze strata before inspecting returns.
Permutation p-values are conditional on the supplied exchangeability assumption;
spatially correlated topology labels generally need a stronger null design.
"""
from __future__ import annotations

import numpy as np
from conditioned import _positive_int
from spectral import dimension


def _labels_strata(regular,strata):
    regular=np.asarray(regular);strata=np.asarray(strata)
    if regular.ndim!=1 or regular.dtype!=np.bool_ or not regular.any() or regular.all():
        raise ValueError('nonempty boolean regular labels with both classes required')
    if strata.shape!=regular.shape or strata.dtype.kind not in 'iu':
        raise ValueError('integer predeclared matching-stratum IDs required')
    return regular,strata


def overlap_weights(regular,strata):
    """Equalize both classes to stratum masses min(n_Rh,n_Qh).

    Each class sums to one. Nonoverlapping strata receive zero weight, and
    excluded counts are returned. This changes the estimand to overlap support.
    Labels/strata only: outcomes never influence matching.
    """
    regular,strata=_labels_strata(regular,strata)
    weights=np.zeros((2,len(regular)))
    table=[];mass=0
    for h in np.unique(strata):
        inside=strata==h
        r=np.flatnonzero(inside&regular);q=np.flatnonzero(inside&~regular)
        matched=min(len(r),len(q))
        table.append({'stratum':int(h),'regular':len(r),'singular':len(q),'overlap_mass':matched})
        if matched:
            weights[0,r]=matched/len(r);weights[1,q]=matched/len(q)
            mass+=matched
    if not mass:
        raise ValueError('no shared covariate support; matched estimand undefined')
    weights/=mass
    effective=1/np.sum(weights**2,axis=1)
    return {'weights':weights,'strata':table,'overlap_mass_per_class':mass,
            'excluded_sites':int(np.count_nonzero(weights.sum(axis=0)==0)),
            'effective_weighted_sites':effective,
            'estimand':'equal class covariate distribution on overlap support; not all-site mean'}


def weighted_effect(site_returns,weights,window):
    returns=np.asarray(site_returns,float);weights=np.asarray(weights,float);w=np.asarray(window)
    if returns.ndim!=2 or not np.isfinite(returns).all() or np.any(returns<0):
        raise ValueError('finite nonnegative site x diffusion-time returns required')
    if (weights.shape!=(2,len(returns)) or not np.isfinite(weights).all() or np.any(weights<0)
            or not np.allclose(weights.sum(axis=1),1,atol=1e-12,rtol=0)):
        raise ValueError('two nonnegative normalized weight rows required')
    if (w.ndim!=1 or not len(w) or w.dtype.kind not in 'iu' or len(set(w))!=len(w)
            or w.min()<1 or w.max()>=returns.shape[1]-1):
        raise ValueError('unique interior integer diffusion times required')
    curves=weights@returns;ds=dimension(curves)
    effect=float(np.mean(ds[0,w]-ds[1,w]))
    if not np.isfinite(effect):
        raise ValueError('nonpositive matched return in the declared diffusion window')
    return {'A':effect,'P_class':curves,'Ds_class':ds,'window':w}


def stratified_permutation_test(site_returns,regular,strata,window,*,
                                exchangeability_assumption,replicates=999,seed=0):
    """Preserve within-stratum class counts; require an explicit assumption.

    A nonempty string records a scientific assumption, not its validation.
    Never use the p-value as evidence unless that assumption is justified.
    """
    regular,strata=_labels_strata(regular,strata)
    if not isinstance(exchangeability_assumption,str) or not exchangeability_assumption.strip():
        raise ValueError('explicit within-stratum exchangeability assumption required')
    replicates=_positive_int(replicates,'replicates',20);seed=_positive_int(seed,'seed',0)
    matched=overlap_weights(regular,strata)
    observed=weighted_effect(site_returns,matched['weights'],window)['A']
    groups=[np.flatnonzero(strata==h) for h in np.unique(strata)]
    rng=np.random.default_rng(seed);null=np.empty(replicates)
    for b in range(replicates):
        permuted=regular.copy()
        for indices in groups:
            permuted[indices]=rng.permutation(regular[indices])
        weight=overlap_weights(permuted,strata)['weights']
        null[b]=weighted_effect(site_returns,weight,window)['A']
    return {'A_observed':observed,'null_A':null,
            'p_one_sided':float((1+np.count_nonzero(null>=observed))/(replicates+1)),
            'seed':seed,'replicates':replicates,'exchangeability_assumption':exchangeability_assumption,
            'assumption_validated_by_code':False,'causal_interpretation':False,
            'excluded_sites':matched['excluded_sites']}


def configuration_group_folds(configuration_ids,*,folds=5,seed=0):
    """Return a fold per row; all rows from a configuration stay together."""
    ids=np.asarray(configuration_ids)
    if ids.ndim!=1 or not len(ids) or ids.dtype.kind not in 'iuUS':
        raise ValueError('integer or string configuration IDs required')
    folds=_positive_int(folds,'folds',2);seed=_positive_int(seed,'seed',0)
    groups=np.unique(ids)
    if len(groups)<folds:
        raise ValueError('more folds than independent configuration groups')
    shuffled=np.random.default_rng(seed).permutation(groups)
    assignments={group:i%folds for i,group in enumerate(shuffled)}
    return np.array([assignments[x] for x in ids],dtype=np.int64)
