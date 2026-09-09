"""Sparse generalized FEM modes and honest finite-matrix heat-trace tail bounds.

A bound on omitted eigenmodes of a finite FEM matrix is NOT a continuum error bound.
Residuals check numerical eigenpairs, not a certified eigenvalue enclosure.
"""
from __future__ import annotations
import numpy as np
from scipy.sparse.linalg import eigsh
from cdt_mechanisms.fem import full_spectrum
from cdt_mechanisms.graph import from_neighbors,degrees
from scipy import sparse


def low_modes(fem,k=256,*,dense_limit=1000,tolerance=1e-10):
    n=fem.stiffness.shape[0]
    if not isinstance(k,int) or k<2:raise ValueError('at least two modes required')
    if n<=dense_limit or k>=n:
        result=full_spectrum(fem,dense_limit=max(dense_limit,n))
        result.update(n_total=n,method='complete dense generalized eigensolve')
        return result
    # Negative shift avoids inverting the singular stiffness matrix at its zero mode.
    values,vectors=eigsh(fem.stiffness,k=min(k,n-1),M=fem.mass,sigma=-1e-7,
        which='LM',tol=tolerance,v0=np.linspace(1.,2.,n),maxiter=max(1000,20*n))
    order=np.argsort(values);values=values[order];vectors=vectors[:,order]
    kv=fem.stiffness@vectors;mv=fem.mass@vectors
    residual=np.linalg.norm(kv-mv*values,axis=0)/np.maximum(1.,np.linalg.norm(kv,axis=0))
    orth=np.max(np.abs(vectors.T@mv-np.eye(len(values))))
    if values.min()<-1e-8 or residual.max()>1e-7 or orth>1e-7:
        raise ArithmeticError('generalized eigenpair validation failed')
    return dict(eigenvalues=np.maximum(values,0),residual=float(residual.max()),
        mass_orthogonality_error=float(orth),complete=False,n_modes=len(values),n_total=n,
        zero_modes=int(np.sum(values<1e-9)),volume=fem.volume,method='shift-invert generalized sparse modes')


def trace_bounds(spectrum,times):
    w=np.asarray(spectrum['eigenvalues'],dtype=float);t=np.asarray(times,dtype=float)
    n=int(spectrum.get('n_total',spectrum['n_modes']))
    if w.ndim!=1 or len(w)<2 or n<len(w) or not np.isfinite(w).all() or np.any(w<0) or np.any(np.diff(w)<-1e-10):
        raise ValueError('sorted nonnegative finite spectrum required')
    if t.ndim!=1 or np.any(t<=0) or not np.isfinite(t).all():raise ValueError('positive finite times required')
    e=np.exp(-np.outer(w,t));z=e.sum(axis=0);q=w@e;omitted=n-len(w)
    if spectrum['complete'] and omitted:raise ValueError('inconsistent complete spectrum')
    threshold=float(w[-1]);ztail=omitted*np.exp(-threshold*t)
    # sup_{lambda>=threshold} lambda exp(-lambda*t).
    maximizer=np.maximum(threshold,1/t);qtail=omitted*maximizer*np.exp(-maximizer*t)
    lower=2*t*q/(z+ztail);upper=2*t*(q+qtail)/z
    return dict(times=t,known_trace=z,trace_lower=z,trace_upper=z+ztail,
        ds_truncated=2*t*q/z,ds_lower=lower,ds_upper=upper,
        omitted_trace_upper=ztail,omitted_relative_upper=ztail/z,
        zero_mode_fraction_upper=float(spectrum['zero_modes'])/z,
        interpretation='finite-matrix tail bounds conditional on accurate ordered low eigenvalues; no continuum certification')


def dual_spectrum(g,moving_probability=.5):
    a=from_neighbors(g.neighbors);d=degrees(a);q=sparse.diags(1/np.sqrt(d))
    lap=moving_probability*(sparse.eye(len(d))-q@a@q)
    values=np.maximum(0,np.linalg.eigvalsh(lap.toarray()))
    return dict(eigenvalues=values,n_modes=len(values),n_total=len(values),complete=True,zero_modes=1,
                operator='continuous-time generator I-P of the same lazy microscopic walk')


def calibrate_clock(dual_values,fem_values,mode_start=1,mode_stop=13):
    a=np.asarray(dual_values);b=np.asarray(fem_values)
    if not 1<=mode_start<mode_stop<=min(len(a),len(b)):raise ValueError('invalid calibration mode range')
    aa=a[mode_start:mode_stop];bb=b[mode_start:mode_stop]
    if not np.isfinite(aa).all() or not np.isfinite(bb).all() or np.any(aa<=0) or np.any(bb<=0):
        raise ValueError('calibration requires strictly positive finite nonzero modes')
    ratios=bb/aa
    if np.any(ratios<=0) or not np.isfinite(ratios).all():raise ValueError('nonpositive mode ratio')
    return dict(fem_eigenvalue_to_dual_ratio=float(np.median(ratios)),ratios=ratios,
        ratio_quartiles=np.quantile(ratios,[.25,.75]),mode_start=mode_start,mode_stop=mode_stop,
        use='fem_time=dual_time/ratio; frozen on a separate reference geometry, never refitted per intervention',
        unique_physical_clock_established=False)
