"""Paired, memory-bounded diagonal-return estimation on the unchanged graph.

Shared full-graph Rademacher probes estimate all origin classes at once.
For symmetric M and y=M^k z, E[y_i^2]=(M^(2k))_ii and
E[y_i (My)_i]=(M^(2k+1))_ii. The half_power method needs ceil(steps/2)
operator applications per probe. A conventional diagonal Hutchinson backend
provides an independent implementation. Probe noise is NOT ensemble noise.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from numbers import Integral

import numpy as np
from scipy.sparse import csr_matrix

from conditioned import checked_operator, _positive_int
from spectral import dimension


def _partition(masks, n, start_mask=None):
    if not masks or any(not isinstance(name,str) or not name for name in masks):
        raise ValueError('nonempty named masks required')
    names = tuple(masks)
    arrays = []
    for name in names:
        a=np.asarray(masks[name])
        if a.dtype != np.bool_ or a.shape!=(n,) or not a.any():
            raise ValueError('every mask must be nonempty boolean shape (n,)')
        arrays.append(a)
    starts=np.ones(n,dtype=bool) if start_mask is None else np.asarray(start_mask)
    if starts.dtype!=np.bool_ or starts.shape!=(n,) or not starts.any():
        raise ValueError('start_mask must be nonempty boolean shape (n,)')
    cover=np.zeros(n,dtype=np.int64)
    for a in arrays:
        cover+=a
    if not np.array_equal(cover,starts.astype(np.int64)):
        raise ValueError('classes must disjointly partition the start population')
    counts=np.array([a.sum() for a in arrays],dtype=np.int64)
    rows=np.concatenate([np.full(int(c),i) for i,c in enumerate(counts)])
    cols=np.concatenate([np.flatnonzero(a) for a in arrays])
    weights=np.concatenate([np.full(int(c),1.0/c) for c in counts])
    reduction=csr_matrix((weights,(rows,cols)),shape=(len(names),n))
    return names,counts,reduction


def propagate_probe_block(matrix, probes, reduction, steps, *, method='half_power'):
    """Low-level deterministic propagation; arbitrary designs are not iid probes.

    Output: probe x class x time. Caller validates M and the class reducer.
    Exposed for exhaustive-sign/Hadamard oracle tests, not random-error claims.
    """
    steps=_positive_int(steps,'steps',0)
    if method not in ('half_power','hutchinson'):
        raise ValueError('method must be half_power or hutchinson')
    z=np.asarray(probes,dtype=float)
    if z.ndim!=2 or z.shape[0]!=matrix.shape[0] or not z.shape[1] or not np.isfinite(z).all():
        raise ValueError('finite n x number_of_probes design required')
    if not np.all((z==1)|(z==-1)):
        raise ValueError('Rademacher entries must be -1 or +1')
    output=np.empty((z.shape[1],reduction.shape[0],steps+1))
    output[:,:,0]=np.asarray(reduction@(z*z)).T
    x=z.copy()
    if method=='half_power':
        for k in range(1,ceil(steps/2)+1):
            nxt=matrix@x
            output[:,:,2*k-1]=np.asarray(reduction@(x*nxt)).T
            if 2*k<=steps:
                output[:,:,2*k]=np.asarray(reduction@(nxt*nxt)).T
            x=nxt
    else:
        for s in range(1,steps+1):
            x=matrix@x
            output[:,:,s]=np.asarray(reduction@(z*x)).T
    return output


@dataclass
class ReturnEstimate:
    names: tuple
    counts: np.ndarray
    samples: np.ndarray
    seed: int
    first_probe: int
    method: str
    operator_applications: int
    estimated_peak_bytes: int

    @property
    def mean(self):
        return self.samples.mean(axis=0)

    @property
    def standard_error(self):
        return self.samples.std(axis=0,ddof=1)/np.sqrt(len(self.samples))

    @property
    def overall_samples(self):
        return np.einsum('pct,c->pt',self.samples,self.counts/self.counts.sum())

    def summary(self):
        mean=self.mean
        se=self.standard_error
        ds=dimension(mean)
        valid=np.isfinite(ds)
        return {'names':list(self.names),'counts':self.counts.tolist(),
                'probe_count':len(self.samples),'seed':self.seed,'first_probe':self.first_probe,
                'method':self.method,'operator_applications':self.operator_applications,
                'estimated_peak_array_bytes':self.estimated_peak_bytes,
                'nonpositive_mean_returns':int(np.count_nonzero(mean<=0)),
                'valid_interior_dimensions':int(valid[:,1:-1].sum()),
                'max_absolute_return_standard_error':float(se.max()),
                'operator_unchanged':True,'uncertainty_scope':'iid probe noise only; not ensemble uncertainty',
                'physics_validation':'NOT_ESTABLISHED'}


def estimate_conditioned(matrix,masks,steps,*,probes=256,seed=0,batch_size=16,
                         start_mask=None,method='half_power',first_probe=0,
                         max_bytes=512*1024**2,max_scalar_updates=5_000_000_000):
    steps=_positive_int(steps,'steps',0)
    probes=_positive_int(probes,'probes',2)
    batch_size=_positive_int(batch_size,'batch_size')
    max_bytes=_positive_int(max_bytes,'max_bytes')
    max_scalar_updates=_positive_int(max_scalar_updates,'max_scalar_updates')
    first_probe=_positive_int(first_probe,'first_probe',0)
    seed=_positive_int(seed,'seed',0)
    if method not in ('half_power','hutchinson'):
        raise ValueError('unknown estimator method')
    matrix=checked_operator(matrix)
    n=matrix.shape[0]
    names,counts,reduction=_partition(masks,n,start_mask)
    batch=min(batch_size,probes)
    multiplications=ceil(steps/2) if method=='half_power' else steps
    updates=int(matrix.nnz)*multiplications*probes
    # Conservative simultaneous numeric-array estimate, excluding Python/BLAS
    # overhead and the caller's preexisting inputs. It is not an RSS hard limit.
    matrix_bytes=sum(a.nbytes for a in (matrix.data,matrix.indices,matrix.indptr,
                                       reduction.data,reduction.indices,reduction.indptr))
    output_bytes=8*probes*len(names)*(steps+1)
    peak=matrix_bytes+output_bytes+8*5*n*batch+8*batch*len(names)*(steps+1)
    if peak>max_bytes:
        raise MemoryError(f'estimated array budget exceeded: {peak} > {max_bytes} bytes')
    if updates>max_scalar_updates:
        raise RuntimeError(f'estimated work budget exceeded: {updates} scalar updates')
    samples=np.empty((probes,len(names),steps+1))
    for first in range(0,probes,batch):
        width=min(batch,probes-first)
        z=np.empty((n,width))
        for j in range(width):
            # Per-probe streams make chunk size and continuation irrelevant.
            rng=np.random.default_rng(np.random.SeedSequence([seed,first_probe+first+j]))
            z[:,j]=2*rng.integers(0,2,n,dtype=np.int8)-1
        samples[first:first+width]=propagate_probe_block(matrix,z,reduction,steps,method=method)
    if not np.isfinite(samples).all():
        raise FloatingPointError('nonfinite diffusion estimates')
    return ReturnEstimate(names,counts,samples,seed,first_probe,method,
                          multiplications*probes,peak)


def probe_effect(estimate:ReturnEstimate,window,*,regular='regular',singular='singular',
                 replicates=500,seed=1):
    """Paired probe bootstrap for one geometry, never a physics p-value.

    Failed nonlinear replicates are reported; they are not silently removed.
    Any invalid replicate prevents issuing a percentile interval.
    """
    w=np.asarray(window)
    t=estimate.samples.shape[-1]
    if (w.ndim!=1 or not len(w) or w.dtype.kind not in 'iu' or len(np.unique(w))!=len(w)
            or w.min()<1 or w.max()>=t-1):
        raise ValueError('unique interior integer diffusion times required')
    replicates=_positive_int(replicates,'replicates',20)
    seed=_positive_int(seed,'bootstrap seed',0)
    if regular==singular or regular not in estimate.names or singular not in estimate.names:
        raise ValueError('two distinct existing class names required')
    indices=[estimate.names.index(regular),estimate.names.index(singular)]
    draws=estimate.samples[:,indices,:]
    mean=draws.mean(axis=0)
    ds=dimension(mean)
    observed=float(np.mean(ds[0,w]-ds[1,w]))
    if not np.isfinite(observed):
        return {'A':None,'CI95_probe_only':None,'status':'INVALID_NONPOSITIVE_RETURN',
                'invalid_bootstrap_replicates':None,'uncertainty_scope':'probe noise only'}
    rng=np.random.default_rng(seed)
    effects=np.empty(replicates)
    for i in range(replicates):
        pooled=draws[rng.integers(len(draws),size=len(draws))].mean(axis=0)
        d=dimension(pooled)
        effects[i]=np.mean(d[0,w]-d[1,w])
    invalid=int(np.count_nonzero(~np.isfinite(effects)))
    return {'A':observed,'CI95_probe_only':None if invalid else np.quantile(effects,[.025,.975]).tolist(),
            'invalid_bootstrap_replicates':invalid,'replicates':replicates,'seed':seed,
            'window':w.tolist(),'status':'INVALID_BOOTSTRAP_RETURNS' if invalid else 'PROBE_NOISE_INTERVAL_ONLY',
            'uncertainty_scope':'one geometry; excludes MCMC, coarse seed and ensemble uncertainty'}
