"""Conservative chain diagnostics; diagnostics are not proof of equilibrium."""
import numpy as np

def autocorrelation(x):
    x=np.asarray(x,float); x=x-x.mean(); n=len(x)
    if n<4 or np.dot(x,x)==0: return np.array([1.]),float('nan')
    f=np.fft.rfft(x,n=2*n)
    ac=np.fft.irfft(f*f.conj())[:n]; ac=ac/ac[0]
    # Initial positive paired sequence; tau convention: ESS=n/(2*tau).
    s=0.; previous=np.inf
    for i in range(1,n-1,2):
        pair=ac[i]+ac[i+1]
        if pair<=0: break
        pair=min(pair,previous); previous=pair; s+=pair
    return ac,max(.5,.5+s)

def summary(x):
    x=np.asarray(x,float); _,tau=autocorrelation(x); n=len(x)
    ess=n/(2*tau) if np.isfinite(tau) else 0.
    split=n//2; a,b=x[:split],x[split:]
    va=a.var(ddof=1); vb=b.var(ddof=1)
    denom=np.sqrt((va/len(a)+vb/len(b))*2*tau)
    z=float(abs(a.mean()-b.mean())/denom) if denom>0 else float('inf')
    return dict(mean=float(x.mean()),sd=float(x.std(ddof=1)),tau_int=float(tau),effective_samples=float(ess),half_mean_difference=float(b.mean()-a.mean()),split_z=z,screen_pass=bool(ess>=50 and z<2 and n>=50*tau))

def bootstrap_return(P,reps,seed):
    """Independent configurations only; dependent chains need blocks/thinning."""
    P=np.asarray(P)
    if P.ndim!=2 or len(P)<2: raise ValueError('configuration x sigma required')
    rng=np.random.default_rng(seed)
    for _ in range(reps): yield P[rng.integers(len(P),size=len(P))].mean(axis=0)

def rank_split_rhat(chains):
    """Max rank/folded split Rhat, Vehtari et al. (2021), equations 4 and 14.

    Input shape is chains x draws. Equal-length independent chains are required;
    an odd middle draw is omitted. This is a diagnostic, not convergence proof.
    """
    from scipy.stats import rankdata
    from scipy.special import ndtri
    x=np.asarray(chains,float)
    if x.ndim!=2 or x.shape[0]<2 or x.shape[1]<4:
        raise ValueError('at least two chains with four draws required')
    if not np.isfinite(x).all() or np.any(np.ptp(x,axis=1)==0):return float('nan')
    n=x.shape[1]//2
    def evaluate(y):
        y=np.concatenate((y[:,:n],y[:,-n:]),axis=0)
        z=ndtri((rankdata(y,method='average').reshape(y.shape)-.375)/(y.size+.25))
        within=z.var(axis=1,ddof=1).mean()
        if within==0:return float('nan')
        between=n*z.mean(axis=1).var(ddof=1)
        return float(np.sqrt(((n-1)*within/n+between/n)/within))
    bulk=evaluate(x);folded=evaluate(abs(x-np.median(x)))
    return float(np.maximum(bulk,folded))
