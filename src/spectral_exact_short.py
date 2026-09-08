"""Exact diagonal returns from sparse half-powers of a symmetric operator."""
import numpy as np
from scipy.sparse import eye

def diagonal_returns(M,steps,max_nnz=8_000_000,starts=None):
    if steps<0 or (M-M.T).nnz:raise ValueError('symmetric operator required')
    n=M.shape[0];starts=np.arange(n) if starts is None else np.asarray(starts)
    B=eye(n,format='csr')[starts];columns=[np.ones(len(starts))];history=[];stop=None
    for k in range(1,(steps+1)//2+1):
        # One sparse multiplication per two diffusion times. Nonnegative M
        # avoids cancellation; rows of B are columns by symmetry.
        C=(B@M).tocsr()
        if C.nnz>max_nnz:
            stop={'reason':'nnz_limit','attempted_power':k,'next_nnz':C.nnz};break
        odd=np.asarray(B.multiply(C).sum(axis=1)).ravel()
        columns.append(odd)
        if len(columns)<=steps:
            columns.append(np.asarray(C.multiply(C).sum(axis=1)).ravel())
        history.append({'power':k,'nnz':C.nnz,'storage_bytes':C.data.nbytes+C.indices.nbytes+C.indptr.nbytes})
        B=C
    return np.array(columns[:steps+1]).T,{'computed_steps':len(columns[:steps+1])-1,'requested_steps':steps,'powers':history,'stop':stop}

def batched_diagonal_returns(M,steps,max_nnz=8_000_000,batch=512):
    n=M.shape[0];batch=min(batch,max_nnz//n)
    if batch<1:raise ValueError('memory bound cannot hold one full row')
    result=np.empty((n,steps+1));reports=[]
    for start in range(0,n,batch):
        stop=min(start+batch,n);P,r=diagonal_returns(M,steps,max_nnz,np.arange(start,stop))
        if r['computed_steps']!=steps:raise RuntimeError('unexpected row-batch sparsity limit')
        result[start:stop]=P;reports.append({'start':start,'stop':stop,'max_nnz':max((x['nnz'] for x in r['powers']),default=0)})
    return result,{'computed_steps':steps,'batch_size':batch,'batches':reports}
