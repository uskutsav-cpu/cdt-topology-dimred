"""Cached all-site UV returns; no changed graph or topology-conditioned labels."""
from pathlib import Path
import argparse,sys,json,hashlib,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from spectral import operator,dimension
from spectral_exact_short import diagonal_returns,batched_diagonal_returns
from condensate import fit_profile,tetra_mask
ap=argparse.ArgumentParser();ap.add_argument('job');ap.add_argument('--total',required=True,type=int);ap.add_argument('--stride',type=int,default=4);ap.add_argument('--steps',type=int,default=26);a=ap.parse_args()
if min(a.total,a.stride,a.steps)<1:raise ValueError('positive sizes required')
code=hashlib.sha256(b''.join((ROOT/'src'/p).read_bytes() for p in ['spectral_exact_short.py','spectral/__init__.py','condensate.py'])).hexdigest()
means=[];noise=[];records=[]
for ix in range(0,a.total,a.stride):
    src=ROOT/'data/geometry'/f'{a.job}_{ix}.npz';inp=hashlib.sha256(src.read_bytes()).hexdigest()
    dest=ROOT/'results/tables'/f'{a.job}_{ix}_exact_uv_s{a.steps}.npz'
    if dest.exists():
        old=np.load(dest)
        assert str(old['input_sha256'])==inp and str(old['source_sha256'])==code,'stale cache'
        P=old['returns'];mask=old['mask'];record=json.loads(str(old['metadata']))
    else:
        g=np.load(src);fit=fit_profile(json.loads(str(g['metadata']))['validation']['spatial_volume'])
        if not fit['resolved_stalk']:raise RuntimeError(f'unresolved stalk {ix}')
        mask=tetra_mask(g['time'],g['tetra'],fit);M=operator(g['neighbors']);start=time.perf_counter()
        P,record=diagonal_returns(M,a.steps,32_000_000)
        if record['computed_steps']!=a.steps:P,record=batched_diagonal_returns(M,a.steps)
        record.update(configuration=ix,seconds=time.perf_counter()-start,rho=.8,operator='full microscopic graph',fit_relative_rmse=fit['relative_rmse'],fraction_condensate=float(mask.mean()))
        with dest.open('xb') as f:np.savez_compressed(f,returns=P,mask=mask,metadata=json.dumps(record),input_sha256=inp,source_sha256=code)
    sample=ROOT/'results/tables'/f'{a.job}_{ix}_condensate_exact_n512_s256.npz'
    if sample.exists() and a.steps<=256:
        old=np.load(sample);assert str(old['input_sha256'])==inp and np.array_equal(mask,old['mask'])
        values=old['returns'][:,:a.steps+1]
        assert np.allclose(P[old['starts']],values,rtol=1e-11,atol=1e-13)
        n=len(values);N=int(mask.sum());noise.append(values.var(axis=0,ddof=1)/n*(N-n)/N)
    means.append(P[mask].mean(axis=0));records.append(record)
means=np.array(means);mean=means.mean(axis=0)
label=f'{a.job}_exact_uv_s{a.steps}_total{a.total}_stride{a.stride}'
np.savetxt(ROOT/'results/tables'/f'{label}.csv',np.column_stack((np.arange(a.steps+1),mean,dimension(mean),dimension(means).mean(axis=0))),delimiter=',',header='sigma,P_mean,Ds_of_mean_P,mean_Ds',comments='')
comparison=[]
if len(noise)==len(means) and len(means)>1:
    variance=means.var(axis=0,ddof=1);noise=np.array(noise).mean(axis=0)
    for s in [9,15,17,20,25]:
        if s<=a.steps and variance[s]>0:comparison.append({'sigma':s,'sampling_variance_over_exact_geometry_variance':float(noise[s]/variance[s])})
report={'status':'baseline measurement; no equilibrium claim','job':a.job,'configurations':len(means),'steps':a.steps,'sampling_variance_comparison':comparison,'records':records,'source_sha256':code}
(ROOT/'results/tables'/f'{label}.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='records'}))
