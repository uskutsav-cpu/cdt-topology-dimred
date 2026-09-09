"""Paired block / coarse-seed / probe bootstrap with explicit sampling units.

Input is chains -> chronological configurations -> seed realizations ->
(probe, class=2, diffusion_time) arrays. Unequal numbers of configurations,
coarse seeds, and probes are allowed. Configurations have equal weight; seed
realizations have equal weight within their configuration. Probe estimates may
be negative, but invalid nonlinear mean/replicate curves are not hidden.
"""
from __future__ import annotations

import numpy as np
from conditioned import _positive_int
from spectral import dimension
from uncertainty import circular_block_indices


def hierarchical_block_effect(chains,window,*,block_length,replicates=500,seed=0,
                              max_resampled_values=500_000_000):
    block_length=_positive_int(block_length,'block_length')
    replicates=_positive_int(replicates,'replicates',20)
    seed=_positive_int(seed,'seed',0)
    max_resampled_values=_positive_int(max_resampled_values,'max_resampled_values')
    arrays=[];times=None
    for chain in chains:
        if len(chain)<2*block_length:
            raise ValueError('each chronological chain needs at least two blocks')
        configs=[]
        for config in chain:
            if not len(config):raise ValueError('configuration has no coarse seeds')
            seeds=[]
            for value in config:
                a=np.asarray(value,float)
                if a.ndim!=3 or a.shape[1]!=2 or a.shape[0]<2 or not np.isfinite(a).all():
                    raise ValueError('finite probe x two classes x diffusion-time arrays required')
                if times is None:times=a.shape[-1]
                if a.shape[-1]!=times:raise ValueError('diffusion-time lengths differ')
                seeds.append(a)
            configs.append(seeds)
        arrays.append(configs)
    if not arrays:raise ValueError('at least one independent chain required')
    w=np.asarray(window)
    if (w.ndim!=1 or not len(w) or w.dtype.kind not in 'iu' or len(np.unique(w))!=len(w)
            or w.min()<1 or w.max()>=times-1):
        raise ValueError('unique interior integer diffusion times required')
    n=sum(len(c) for c in arrays)
    # Bound the worst realization chosen for every seed slot/configuration slot.
    max_seeds=max(len(c) for chain in arrays for c in chain)
    max_probes=max(len(a) for chain in arrays for c in chain for a in c)
    work=replicates*n*max_seeds*max_probes*2*times
    if work>max_resampled_values:
        raise RuntimeError('hierarchical bootstrap work budget exceeded')
    config_means=[np.mean([a.mean(axis=0) for a in config],axis=0)
                  for chain in arrays for config in chain]
    pooled=np.mean(config_means,axis=0);ds=dimension(pooled)
    observed=float(np.mean(ds[0,w]-ds[1,w]))
    if not np.isfinite(observed):
        raise ValueError('observed mean returns invalid in declared window')
    rng=np.random.default_rng(seed);effects=np.empty(replicates)
    for b in range(replicates):
        total=np.zeros((2,times))
        for chain in arrays:
            for index in circular_block_indices(len(chain),block_length,rng):
                config=chain[index];mean=np.zeros((2,times))
                for j in rng.integers(len(config),size=len(config)):
                    probes=config[j]
                    mean+=probes[rng.integers(len(probes),size=len(probes))].mean(axis=0)
                total+=mean/len(config)
        d=dimension(total/n)
        effects[b]=np.mean(d[0,w]-d[1,w])
    invalid=int(np.count_nonzero(~np.isfinite(effects)))
    return {'A':observed,'A_CI95':None if invalid else np.quantile(effects,[.025,.975]),
            'bootstrap_A':effects,'invalid_bootstrap_replicates':invalid,
            'Ds_of_mean_return':ds,'mean_of_configuration_Ds':np.mean(dimension(np.stack(config_means)),axis=0),
            'configuration_count':n,'chain_count':len(arrays),'block_length_configurations':block_length,
            'replicates':replicates,'seed':seed,'window':w,'estimated_resampled_values':work,
            'estimand':'dimension of equal-configuration, within-configuration equal-seed mean return',
            'inference_status':'ASSUMPTION_DEPENDENT_NOT_EQUILIBRIUM_OR_CAUSAL_CERTIFICATION'}
