"""Incremental baseline measurement: skip valid curves, process validated snapshots.

Can run while a chain is being extended; aggregate only after all requested
snapshots are available. No topology-conditioned analysis is performed here.
"""
from pathlib import Path
import argparse,sys,json,hashlib,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from spectral import operator,exact_returns,dimension
from condensate import fit_profile,tetra_mask
ap=argparse.ArgumentParser();ap.add_argument('job');ap.add_argument('--total',type=int,required=True);ap.add_argument('--stride',type=int,default=5);ap.add_argument('--starts',type=int,default=512);ap.add_argument('--steps',type=int,default=256);a=ap.parse_args()
codehash=hashlib.sha256(b''.join((ROOT/'src'/p).read_bytes() for p in ['spectral/__init__.py','condensate.py'])).hexdigest()
curves=[];checks=[];pending=[];computed=0;skipped=0
for ix in range(0,a.total,a.stride):
    source=ROOT/'data/geometry'/f'{a.job}_{ix}.npz'
    if not source.exists():pending.append(ix);continue
    inp=hashlib.sha256(source.read_bytes()).hexdigest()
    out=ROOT/'results/tables'/f'{a.job}_{ix}_condensate_exact_n{a.starts}_s{a.steps}.npz'
    if out.exists():
        r=np.load(out);assert str(r['source_sha256'])==codehash and str(r['input_sha256'])==inp
        values=r['returns'];check=json.loads(str(r['metadata']));skipped+=1
    else:
        g=np.load(source);meta=json.loads(str(g['metadata']));fit=fit_profile(meta['validation']['spatial_volume'])
        if not fit['resolved_stalk']:raise RuntimeError(f'unresolved condensate {ix}')
        mask=tetra_mask(g['time'],g['tetra'],fit);ids=np.flatnonzero(mask)
        starts=np.random.default_rng(55000+ix).permutation(ids)[:a.starts]
        begin=time.perf_counter();M=operator(g['neighbors']);reused=0
        pilot=ROOT/'results/tables'/f'{a.job}_{ix}_precision_pilot.npz'
        old=None
        if pilot.exists():
            old=np.load(pilot);n=len(old['starts'])
            if old['returns'].shape[1]==a.steps+1 and np.array_equal(starts[:n],old['starts']) and str(old['input_sha256'])==inp:reused=n
        new=exact_returns(M,a.steps,starts[reused:]) if reused<len(starts) else np.empty((0,a.steps+1))
        values=np.concatenate((old['returns'],new)) if reused else new
        N=len(ids);n=len(starts);mean=values.mean(axis=0)
        se=values.std(axis=0,ddof=1)/np.sqrt(n)*np.sqrt((N-n)/(N-1))
        check={'configuration':f'{a.job}_{ix}','starts':n,'steps':a.steps,'rho':.8,'operator':'full microscopic graph','conditioning':'cos2/constant fitted condensate starts','fit_relative_rmse':fit['relative_rmse'],'fraction_condensate':float(mask.mean()),'maximum_relative_se_9_64':float(np.max(se[9:65]/mean[9:65])),'seconds':time.perf_counter()-begin,'reused_pilot_starts':reused}
        with open(out,'xb') as f:np.savez_compressed(f,returns=values,starts=starts,mask=mask,metadata=json.dumps(check),source_sha256=codehash,input_sha256=inp)
        computed+=1
    curves.append(values.mean(axis=0));checks.append(check)
report={'job':a.job,'total_requested_snapshots':a.total,'measurement_stride':a.stride,'computed':computed,'skipped':skipped,'pending':pending,'checks':checks}
label=f'{a.job}_n{a.starts}_s{a.steps}_stride{a.stride}'
(ROOT/'results/tables'/f'{label}_measurement.json').write_text(json.dumps(report,indent=2)+'\n')
if not pending:
    P=np.array(curves);mean=P.mean(axis=0);rng=np.random.default_rng(81003)
    # Circular moving-block bootstrap of chronologically spaced configurations.
    # Block length 4 is a declared baseline sensitivity choice, not a proof of independence.
    draws=[];n=len(P);block=4
    for b in range(1000):
        ix=(rng.integers(n,size=(n+block-1)//block)[:,None]+np.arange(block)).ravel()[:n]%n
        draws.append(dimension(P[ix].mean(axis=0)))
    draws=np.array(draws);lo=np.full(a.steps+1,np.nan);hi=lo.copy();lo[1:-1],hi[1:-1]=np.quantile(draws[:,1:-1],[.025,.975],axis=0)
    table=np.column_stack((np.arange(a.steps+1),mean,dimension(mean),dimension(P).mean(axis=0),lo,hi))
    np.savetxt(ROOT/'results/tables'/f'{label}_aggregate.csv',table,delimiter=',',comments='',header='sigma,P_mean,Ds_of_mean_P,mean_Ds,Ds_block4_ci_low,Ds_block4_ci_high')
    print(json.dumps({'complete_measurement_set':len(P),'peak_Ds_sigma_ge_10':float(np.nanmax(table[10:,2])),'max_relative_se':max(c['maximum_relative_se_9_64'] for c in checks)}))
else:print(json.dumps({'computed':computed,'skipped':skipped,'pending':len(pending)}))
