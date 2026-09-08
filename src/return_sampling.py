"""Nested exact-start sampling for pilot precision assessment; no repeated starts."""
import numpy as np
from spectral import exact_returns

def precision_pilot(M,steps,starts,seed,window,batch=64,max_starts=1024,relative_se=.02):
    starts=np.asarray(starts);n=len(starts)
    if n<1 or batch<2 or max_starts<2 or not 1<=window[0]<=window[1]<steps:raise ValueError('sampling contract')
    order=np.random.default_rng(seed).permutation(starts);cap=min(n,max_starts)
    measured=[];history=[];count=0
    for end in range(min(batch,cap),cap+batch,batch):
        end=min(end,cap)
        if end==count:break
        measured.append(exact_returns(M,steps,order[count:end]));count=end
        values=np.concatenate(measured);mean=values.mean(axis=0)
        if count==n:se=np.zeros(steps+1)
        else:se=values.std(axis=0,ddof=1)/np.sqrt(count)*np.sqrt((n-count)/(n-1))
        sl=slice(window[0],window[1]+1);worst=float(np.max(se[sl]/mean[sl]))
        history.append({'starts':count,'maximum_relative_se':worst})
        if worst<=relative_se:break
    return {'starts':order[:count],'returns':values,'history':history,'precision_pass':worst<=relative_se}
