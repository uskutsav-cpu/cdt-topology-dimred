"""Explicit cos²/constant stalk fit; boundary conventions kept separate."""
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import csr_matrix,diags,eye

def fit_profile(profile):
    """C.19–20 functional form, using current N31 as the normalization.

    Individual-configuration fitting is an explicit adaptation of the paper's
    coherently averaged profile fit, not a claimed exact historical cutoff.
    """
    profile=np.asarray(profile,float); T=len(profile); t=np.arange(T); volume=profile.sum()
    if T<8 or np.any(profile<=0): raise ValueError('invalid profile')
    center0=float(np.argmax(profile))
    def model(p):
        A,w,center=p; d=(t-center+T/2)%T-T/2
        height=2*volume/(np.pi*w)
        bump=np.where(abs(d)<np.pi*w/2,height*np.cos(d/w)**2,0.)
        return np.maximum(A,bump)
    best=None
    for w in [T/10,T/5,T/3]:
        res=least_squares(lambda p:(model(p)-profile)/np.sqrt(np.maximum(profile,4)),[max(4,float(np.quantile(profile,.15))),w,center0],bounds=([.1,.5,center0-T/2],[profile.max(),T,center0+T/2]))
        if best is None or np.dot(res.fun,res.fun)<np.dot(best.fun,best.fun): best=res
    A,w,center=best.x; height=2*volume/(np.pi*w)
    radius=w*np.arccos(np.sqrt(min(1,A/height)))
    d=(t-center+T/2)%T-T/2; slices=abs(d)<=radius
    fitted=model(best.x)
    relrmse=float(np.sqrt(np.mean((profile-fitted)**2))/profile.max())
    return {'stalk_level':float(A),'width':float(w),'center':float(center%T),'radius':float(radius),'relative_rmse':relrmse,'resolved_stalk':bool(slices.any() and (~slices).sum()>=4 and relrmse<.3),'slice_mask':slices,'fitted_profile':fitted}

def tetra_mask(time,tetra,fit,radius_shift=0):
    T=len(fit['slice_mask']); d=(np.arange(T)-fit['center']+T/2)%T-T/2
    slices=abs(d)<=fit['radius']+radius_shift
    return np.all(slices[time[tetra]],axis=1)

def excised_operator(neighbors,mask,rho=.8,boundary='renormalize'):
    """Column stochastic operator on retained sites, for baseline sensitivity.

    This changes the operator and must never be the topology-conditioned test.
    """
    from scipy.sparse.csgraph import connected_components
    ids=np.flatnonzero(mask)
    if len(ids)<2: raise ValueError('empty/too small excision')
    inv=np.full(len(mask),-1,int); inv[ids]=np.arange(len(ids)); mapped=inv[neighbors[ids]]
    rows=np.repeat(np.arange(len(ids)),neighbors.shape[1]); cols=mapped.ravel(); ok=cols>=0
    A=csr_matrix((np.ones(ok.sum()),(rows[ok],cols[ok])),shape=(len(ids),len(ids)))
    degree=np.asarray(A.sum(axis=0)).ravel()
    if np.any(degree==0) or connected_components(A)[0]!=1: raise ValueError('excision disconnected')
    if boundary=='renormalize': M=(1-rho)*eye(len(ids),format='csr')+rho*A@diags(1/degree)
    elif boundary=='hold': M=rho/neighbors.shape[1]*A+diags(1-rho*degree/neighbors.shape[1])
    else: raise ValueError('unknown boundary')
    return M.tocsr(),ids
