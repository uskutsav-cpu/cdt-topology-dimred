"""Full microscopic diffusion; masks restrict starts only."""
import numpy as np
from scipy.sparse import csr_matrix,eye

def operator(neighbors,rho=.8):
    neighbors=np.asarray(neighbors); n,d=neighbors.shape
    if not 0<rho<=1 or neighbors.min()<0 or neighbors.max()>=n: raise ValueError('invalid graph/rho')
    A=csr_matrix((np.ones(n*d),(np.repeat(np.arange(n),d),neighbors.ravel())),shape=(n,n))
    if (A!=A.T).nnz: raise ValueError('expected undirected regular graph')
    return (1-rho)*eye(n,format='csr')+rho/d*A

def exact_returns(M,steps,starts=None):
    n=M.shape[0]; starts=np.arange(n) if starts is None else np.asarray(starts)
    if len(starts)==0: raise ValueError('empty starts')
    x=np.zeros((n,len(starts))); x[starts,np.arange(len(starts))]=1
    result=np.empty((len(starts),steps+1)); result[:,0]=1
    for s in range(1,steps+1):
        x=M@x; result[:,s]=x[starts,np.arange(len(starts))]
    return result

def hutchinson(M,steps,probes,seed,mask=None):
    n=M.shape[0]; mask=np.ones(n,bool) if mask is None else np.asarray(mask,bool)
    if mask.shape!=(n,) or not mask.any() or probes<2: raise ValueError('mask/probes')
    z=np.random.default_rng(seed).choice([-1.,1.],size=(n,probes)); z[~mask]=0; x=z.copy()
    out=np.ones((probes,steps+1))
    for s in range(1,steps+1):
        x=M@x; out[:,s]=np.sum(z*x,axis=0)/mask.sum()
    return out

def walkers(neighbors,steps,walks,seed,rho=.8,starts=None):
    n,d=neighbors.shape; rng=np.random.default_rng(seed)
    if walks<1 or not 0<rho<=1: raise ValueError('walks/rho')
    starts=np.arange(n) if starts is None else np.asarray(starts)
    if not len(starts): raise ValueError('empty starts')
    origin=rng.choice(starts,size=walks); x=origin.copy(); out=np.ones(steps+1)
    for s in range(1,steps+1):
        move=rng.random(walks)<rho
        x[move]=neighbors[x[move],rng.integers(d,size=move.sum())]
        out[s]=np.mean(x==origin)
    return out

def dimension(P):
    P=np.asarray(P,float); out=np.full_like(P,np.nan); sig=np.arange(1,P.shape[-1]-1)
    valid=(P[...,1:-1]>0)&(P[...,2:]>0)&(P[...,:-2]>0)
    np.divide(-sig*(P[...,2:]-P[...,:-2]),P[...,1:-1],out=out[...,1:-1],where=valid)
    return out

def logpoly_dimension(P,halfwidth=3,degree=2):
    P=np.asarray(P,float); out=np.full_like(P,np.nan)
    if P.ndim!=1: raise ValueError('one curve required')
    for s in range(1+halfwidth,len(P)-halfwidth):
        sl=np.arange(s-halfwidth,s+halfwidth+1)
        if np.all(P[sl]>0):
            fit=np.polynomial.polynomial.polyfit(np.log(sl/s),np.log(P[sl]),degree)
            out[s]=-2*fit[1]
    return out
