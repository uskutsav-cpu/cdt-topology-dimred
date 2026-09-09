"""Fixed-operator diffusion, measured exploration scales, finite-size flags."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy import sparse
from .graph import adjacency, checked_roots, degrees, distances


@dataclass
class Diffusion:
    sigma: np.ndarray
    roots: np.ndarray
    returns: np.ndarray              # roots x steps; column zero is sigma=0
    mean_square_distance: np.ndarray
    stationary_return: np.ndarray
    moving_probability: float
    mass_error: float

    @property
    def rms_distance(self):
        return np.sqrt(np.maximum(self.mean_square_distance,0))


def transition(value, moving_probability: float=0.5) -> sparse.csr_matrix:
    a=adjacency(value)
    if not np.isfinite(moving_probability) or not 0 < moving_probability <= 1:
        raise ValueError("moving probability must be in (0,1]")
    return (sparse.eye(a.shape[0],format='csr')*(1-moving_probability)
            +moving_probability*sparse.diags(1/degrees(a))@a).tocsr()


def exact_diffusion(value, roots, max_steps: int, *, moving_probability: float=0.5,
                    batch_size: int=32, max_work: int=500_000_000) -> Diffusion:
    """Deterministic probability propagation (no Monte Carlo sampling error).

    Memory O(N*batch_size + starts*steps), no dense N-by-N matrix power.
    Full shortest-path distances are computed one batch at a time.
    """
    a=adjacency(value); roots=checked_roots(roots,a.shape[0])
    if not isinstance(max_steps,int) or max_steps<2 or not isinstance(batch_size,int) or batch_size<1:
        raise ValueError("max_steps >=2 and batch_size >=1 must be integers")
    if a.nnz*len(roots)*max_steps > max_work:
        raise ValueError("work budget exceeded; reduce roots/steps or explicitly raise max_work")
    p=transition(a,moving_probability); trans=p.T.tocsr(); n=a.shape[0]
    ret=np.empty((len(roots),max_steps+1)); msd=np.empty_like(ret); err=0.
    for lo in range(0,len(roots),batch_size):
        rr=roots[lo:lo+batch_size]; b=len(rr); ix=np.arange(b)
        state=np.zeros((n,b)); state[rr,ix]=1
        d2=distances(a,rr).T**2
        for step in range(max_steps+1):
            ret[lo:lo+b,step]=state[rr,ix]
            msd[lo:lo+b,step]=np.sum(state*d2,axis=0)
            err=max(err,float(np.max(np.abs(state.sum(axis=0)-1))))
            if step<max_steps: state=trans@state
    if err>1e-9 or np.min(ret)<-1e-12:
        raise ArithmeticError("probability conservation failed")
    d=degrees(a)
    return Diffusion(np.arange(max_steps+1),roots,ret,msd,d[roots]/d.sum(),moving_probability,err)


def log_slope(x, y, *, half_window: int=2) -> np.ndarray:
    """Centered local log-linear slope on the ACTUAL x grid; endpoints undefined.

    A window touching zero/nonfinite y is invalid instead of epsilon-clipped.
    """
    x=np.asarray(x,dtype=float); raw=np.asarray(y,dtype=float)
    if x.ndim!=1 or len(x)<3 or np.any(np.diff(x)<=0) or np.any(x<0) or not np.isfinite(x).all():
        raise ValueError("x must be a finite nonnegative strictly increasing vector")
    if not isinstance(half_window,int) or half_window<1:
        raise ValueError("half_window must be >=1")
    if raw.ndim<1 or raw.shape[-1]!=len(x):
        raise ValueError("last y dimension must match x")
    out=np.full(raw.shape,np.nan); flat=raw.reshape(-1,len(x)); of=out.reshape(flat.shape)
    for j in range(half_window,len(x)-half_window):
        sl=slice(j-half_window,j+half_window+1)
        if np.any(x[sl]<=0): continue
        lx=np.log(x[sl]); centered=lx-lx.mean(); denom=centered@centered
        window=flat[:,sl]; valid=np.all((window>0)&np.isfinite(window),axis=1)
        of[valid,j]=(np.log(window[valid])@centered)/denom
    return out


def spectral_dimension(result: Diffusion, *, half_window=2, floor_factor=2.) -> dict:
    if not np.isfinite(floor_factor) or floor_factor<=1:
        raise ValueError("floor_factor must exceed 1")
    ds=-2*log_slope(result.sigma,result.returns,half_window=half_window)
    # Require every point in the slope window to be above the stationary floor.
    raw=result.returns>floor_factor*result.stationary_return[:,None]
    valid=np.zeros_like(raw)
    for j in range(half_window,len(result.sigma)-half_window):
        valid[:,j]=np.all(raw[:,j-half_window:j+half_window+1],axis=1)
    valid &= np.isfinite(ds)
    return dict(ds=ds,pre_mix=valid,finite_size_warning=~valid)


def fit_walk_dimension(result: Diffusion, lower: int, upper: int) -> dict:
    """Fit r_rms ~ sigma**(1/d_w); window must be chosen BEFORE looking at a ridge."""
    mask=(result.sigma>=lower)&(result.sigma<=upper)
    if lower<1 or mask.sum()<4:
        raise ValueError("need >=4 positive diffusion times in the declared window")
    radius=np.sqrt(result.mean_square_distance.mean(axis=0))
    if np.any(radius[mask]<=0): raise ValueError("zero exploration radius")
    x=np.log(result.sigma[mask]); y=np.log(radius[mask]); c=np.polyfit(x,y,1)
    fit=np.polyval(c,x); total=np.sum((y-y.mean())**2)
    return dict(exponent=float(c[0]),walk_dimension=float(1/c[0]) if c[0]>0 else None,
                r_squared=float(1-np.sum((y-fit)**2)/total) if total>0 else None,
                lower=int(lower),upper=int(upper),finite_window_only=True)


def heat_trace_dimension(eigenvalues, times) -> dict:
    """Exact finite-matrix heat trace derivative. Requires a COMPLETE spectrum."""
    w=np.asarray(eigenvalues,dtype=float); t=np.asarray(times,dtype=float)
    if w.ndim!=1 or len(w)<2 or np.any(w < -1e-8) or not np.isfinite(w).all():
        raise ValueError("invalid spectrum")
    if t.ndim!=1 or len(t)==0 or np.any(t<=0) or not np.isfinite(t).all():
        raise ValueError("times must be positive and finite")
    w=np.maximum(w,0); exp=np.exp(-np.outer(w,t)); z=exp.sum(axis=0)
    return dict(times=t,return_trace=z/len(w),ds=2*t*(w@exp)/z,
                zero_mode_fraction=exp[w<1e-10].sum(axis=0)/z)
