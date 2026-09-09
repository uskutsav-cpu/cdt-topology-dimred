"""Independent geometry validation and exact batched microscopic diffusion.

Root sampling is uniform without replacement. Propagation is deterministic,
not a random-walker count. Failed stalk fits are retained, never silently dropped.
"""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import io
import json
import math
import os
import platform
import shutil
import subprocess
import time
import numpy as np
from scipy.sparse import csr_matrix, eye
from geometry import read_geometry
from condensate import fit_profile, tetra_mask, excised_operator
from .design import validate_design
from .io import atomic_bytes, atomic_json, digest, immutable_json, inventory, load_json, lock, now, sha256, verify_inventory


def compile_validator(root: Path) -> dict:
    source=root/'src/cdt_baseline/cpp/validate_geometry.cpp'
    compiler=shutil.which('c++')
    if compiler is None:raise RuntimeError('C++ compiler required for independent geometry checks')
    version=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]
    contract=dict(source_sha256=sha256(source),compiler=compiler,version=version,platform=platform.platform())
    out=root/'build/baseline-validator'/digest(contract)[:20];mp=out/'manifest.json'
    with lock(out.parent/(out.name+'.lock')):
        if mp.exists():
            m=load_json(mp);verify_inventory(out,m['outputs']);return m
        if out.exists():raise ValueError('incomplete validator build retained; inspect rather than overwrite')
        out.mkdir(parents=True)
        command=[compiler,'-std=c++14','-O3','-Wall','-Wextra',str(source),'-o',str(out/'validate-geometry')]
        with (out/'build.log').open('wb') as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True)
        result=dict(contract=contract,binary=str((out/'validate-geometry').relative_to(root)),binary_sha256=sha256(out/'validate-geometry'),outputs=inventory(out))
        atomic_json(mp,result);return result


def exact_returns(M, roots, steps: int, batch: int=8):
    M=csr_matrix(M,dtype=float);roots=np.asarray(roots)
    if M.shape[0]!=M.shape[1] or M.shape[0]<2 or not np.isfinite(M.data).all() or np.any(M.data<0):
        raise ValueError('invalid transition matrix')
    if not np.allclose(np.asarray(M.sum(axis=0)).ravel(),1,rtol=0,atol=1e-13):
        raise ValueError('transition matrix must be column stochastic')
    if roots.ndim!=1 or roots.dtype.kind not in 'iu' or len(roots)==0 or np.any(roots<0) or np.any(roots>=M.shape[0]):
        raise ValueError('invalid starting roots')
    if type(steps) is not int or steps<1 or type(batch) is not int or batch<1:raise ValueError('invalid propagation budget')
    answer=np.empty((len(roots),steps+1),dtype=float);mass_error=0.
    for start in range(0,len(roots),batch):
        ids=roots[start:start+batch];b=len(ids);q=np.zeros((M.shape[0],b));q[ids,np.arange(b)]=1
        answer[start:start+b,0]=1
        for s in range(1,steps+1):
            q=M@q
            answer[start:start+b,s]=q[ids,np.arange(b)]
            if s==steps or s%16==0:
                mass_error=max(mass_error,float(np.max(np.abs(q.sum(axis=0)-1))))
    if mass_error>1e-10 or not np.isfinite(answer).all() or np.any(answer<0) or np.any(answer>1+1e-12):
        raise ArithmeticError('diffusion mass/probability validation failed')
    return answer,mass_error


def full_operator(neighbors,rho):
    nb=np.asarray(neighbors)
    if nb.ndim!=2 or nb.shape[1]!=4 or nb.dtype.kind not in 'iu' or np.any(nb<0) or np.any(nb>=len(nb)):
        raise ValueError('expected four valid neighbors per tetrahedron')
    if type(rho) not in (int,float) or not 0<rho<1:raise ValueError('rho must lie in (0,1)')
    n=len(nb);A=csr_matrix((np.ones(n*4),(np.repeat(np.arange(n),4),nb.ravel())),shape=(n,n))
    if (A!=A.T).nnz:raise ValueError('dual adjacency is not symmetric')
    return ((1-rho)*eye(n,format='csr')+(rho/4)*A).tocsr()


def draw_roots(ids,count,seed):
    ids=np.asarray(ids,dtype=np.int64)
    if ids.ndim!=1 or len(ids)==0 or len(np.unique(ids))!=len(ids) or type(count) is not int or count<1:
        raise ValueError('invalid root population/budget')
    # Do not sort: the first half must itself remain a uniform sample.
    return np.random.default_rng(seed).choice(ids,size=min(count,len(ids)),replace=False)


def profile_statistics(profile):
    profile=np.asarray(profile,float);T=len(profile)
    if T<3 or np.any(profile<=0) or not np.isfinite(profile).all():raise ValueError('invalid spatial profile')
    peaks=np.flatnonzero(profile==profile.max());variances=[]
    for peak in peaks:
        d=np.minimum((np.arange(T)-peak)%T,(peak-np.arange(T))%T)
        variances.append(float(np.dot(profile,d*d)/profile.sum()))
    return dict(peak_volume=int(profile.max()),peak_times=peaks.tolist(),
                profile_width=float(np.sqrt(np.mean(variances))),
                profile_participation=float(profile.sum()**2/np.dot(profile,profile)),
                profile_peak_fraction=float(profile.max()/profile.sum()))


def finite_json(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:finite_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [finite_json(v) for v in value]
    return value


def measurement_sources(root):
    paths=['src/cdt_baseline/measure.py','src/cdt_baseline/io.py','src/cdt_baseline/cpp/validate_geometry.cpp','src/geometry.py','src/condensate.py']
    return {p:sha256(root/p) for p in paths}


def _measure_one(task):
    root=Path(task['root']);study=Path(task['study']);raw=study/task['raw'];cfg=task['cfg']
    before=sha256(raw)
    contract=dict(input_sha256=before,sources=task['sources'],validator_sha256=task['validator']['binary_sha256'],
                  rho=cfg['rho'],rho_sensitivity=cfg['rho_sensitivity'],max_steps=cfg['max_steps'],roots=cfg['roots'],
                  policies=['full_uniform','full_peak31','excised_uniform_hold','excised_uniform_renormalize'],
                  sampling='uniform_without_replacement_unsorted',root_seed='SHA256 of geometry and population label',
                  excision='existing individual-profile cos2/constant fit; not claimed historical prescription')
    key=digest(contract)[:20];out=study/'measurements'/key;mp=out/'manifest.json'
    with lock(out.parent/(key+'.lock')):
        if mp.exists():
            old=load_json(mp)
            if old['contract']!=contract:raise ValueError('measurement hash collision')
            verify_inventory(out,old['outputs']);return dict(raw=task['raw'],measurement=key,manifest_sha256=sha256(mp),cached=True)
        if out.exists():raise ValueError('incomplete measurement retained; inspect before retrying')
        out.mkdir(parents=True);start=time.perf_counter()
        validator=root/task['validator']['binary']
        if sha256(validator)!=task['validator']['binary_sha256']:raise ValueError('validator changed')
        proc=subprocess.run([str(validator),str(raw)],capture_output=True,text=True,timeout=120)
        if proc.returncode:raise ValueError(f'geometry rejected: {task["raw"]}: {proc.stderr[-1000:]}')
        report=json.loads(proc.stdout);g=read_geometry(raw)
        if len(g.tetra)!=report['N3'] or len(g.time)!=report['N0']:raise ValueError('independent parsers disagree')
        report.update(profile_statistics(report['spatial_volume']))
        n=len(g.tetra);all_ids=np.arange(n);times=g.time[g.tetra]
        peak31=np.flatnonzero((times[:,0]==times[:,1])&(times[:,1]==times[:,2])&np.isin(times[:,0],report['peak_times']))
        if not len(peak31):raise ValueError('no native-oriented 31 tetrahedra at profile maximum')
        seeds={label:int(digest({'geometry':before,'population':label})[:16],16) for label in ('full','peak31','excised')}
        roots={'full_uniform':draw_roots(all_ids,cfg['roots'],seeds['full']),
               'full_peak31':draw_roots(peak31,cfg['roots'],seeds['peak31'])}
        arrays={};curves=[];fits={};excisions={}
        try:
            fit=fit_profile(report['spatial_volume']);fits=finite_json(fit)
            if fit['resolved_stalk']:
                mask=tetra_mask(g.time,g.tetra,fit)
                # The exact boundary treatment is a declared sensitivity analysis.
                for boundary in ('hold','renormalize'):
                    excisions[boundary]=excised_operator(g.neighbors,mask,cfg['rho'],boundary)
                retained=excisions['hold'][1];local_roots=draw_roots(np.arange(len(retained)),cfg['roots'],seeds['excised'])
                fits['retained_N3']=len(retained);fits['retained_fraction']=len(retained)/n
                fits['excision_status']='resolved_adaptation'
            else:fits['excision_status']='unresolved_stalk'
        except (ValueError,RuntimeError) as e:
            fits.update(excision_status='failed_fit_or_disconnected_excision',error=str(e));excisions={}
        for rho in [cfg['rho'],*cfg['rho_sensitivity']]:
            M=full_operator(g.neighbors,rho)
            ids=np.concatenate([roots['full_uniform'],roots['full_peak31']]);unique,inverse=np.unique(ids,return_inverse=True)
            values,error=exact_returns(M,unique,cfg['max_steps'],cfg['root_batch']);v=values[inverse];offset=0
            for label in ('full_uniform','full_peak31'):
                count=len(roots[label]);name=f'{label}_rho_{rho:g}';data=v[offset:offset+count];offset+=count
                arrays[name]=data;arrays[name+'_roots']=roots[label]
                curves.append(dict(key=name,policy=label,rho=rho,roots=count,population=n if label=='full_uniform' else len(peak31),
                                   operator_size=n,stationary_return=1/n,mass_error=error,root_seed=seeds['full' if label=='full_uniform' else 'peak31']))
            if excisions:
                for boundary in ('hold','renormalize'):
                    EM,retained=excised_operator(g.neighbors,mask,rho,boundary)
                    data,error=exact_returns(EM,local_roots,cfg['max_steps'],cfg['root_batch'])
                    label=f'excised_uniform_{boundary}';name=f'{label}_rho_{rho:g}'
                    arrays[name]=data;arrays[name+'_roots']=retained[local_roots]
                    # Trace's all-root mean stationary return is 1/N also for a
                    # connected, nonregular induced graph. For sampled roots,
                    # use the actual stationary pi values instead of that mean.
                    if boundary=='hold':stationary=1/len(retained)
                    else:
                        retained_mask=np.zeros(n,bool);retained_mask[retained]=True
                        degree=np.sum(retained_mask[g.neighbors[retained]],axis=1)
                        stationary=float(np.mean(degree[local_roots]/degree.sum()))
                    curves.append(dict(key=name,policy=label,rho=rho,roots=len(local_roots),population=len(retained),
                                       operator_size=len(retained),stationary_return=stationary,mass_error=error,root_seed=seeds['excised']))
        if sha256(raw)!=before:raise ValueError('geometry changed during measurement')
        buffer=io.BytesIO();np.savez_compressed(buffer,**arrays);atomic_bytes(out/'returns.npz',buffer.getvalue())
        atomic_json(out/'geometry.json',report);atomic_json(out/'profile_fit.json',fits);atomic_json(out/'curves.json',curves)
        record=dict(schema=1,contract=contract,raw=task['raw'],curves=curves,elapsed_seconds=time.perf_counter()-start,
                    executed_at=now(),outputs=inventory(out),full_manifold_validation=True,exact_probability_propagation=True,
                    equilibrium_established=False,reproduction_pass=False)
        atomic_json(mp,record)
        return dict(raw=task['raw'],measurement=key,manifest_sha256=sha256(mp),cached=False)


def measure_study(root,cfg,study,*,workers=2):
    root=Path(root).resolve();study=Path(study).resolve();cfg=validate_design(cfg)
    if type(workers) is not int or not 1<=workers<=4:raise ValueError('workers must be in [1,4]')
    if load_json(study/'protocol.json')['design']!={k:v for k,v in cfg.items() if k!='samples'}:raise ValueError('measurement design mismatch')
    if load_json(study/'simulation_status.json')['status']!='NATIVE_RUNS_COMPLETE':raise ValueError('complete the native schedule before measurement')
    validator=compile_validator(root);sources=measurement_sources(root);index=load_json(study/'chain_index.json')
    plan=dict(sources=sources,validator=validator['contract'],primary='full_uniform: both mean-per-geometry Ds and derivative-of-ensemble-P explicitly distinguished',
              reference='Cooperman 1711.02685 Eq.3.10/3.12 and appendix A use per-geometry differentiation then ensemble mean; stalk is excised',
              comparison='excision here is an adaptation using the existing individual-profile fit; do not claim exact published reproduction',
              negative='unresolved excisions are not substituted with full graphs and not silently filtered into an ensemble estimate')
    immutable_json(study/'measurement_protocol.json',plan)
    tasks=[];chain_rows=[]
    for entry in index:
        mp=study/'raw'/entry['job']/'manifest.json';m=load_json(mp)
        if entry['status']!='complete' or m['status']!='complete' or sha256(mp)!=entry['manifest_sha256']:raise ValueError('chain manifest changed/incomplete')
        verify_inventory(mp.parent,m['outputs'])
        if m['parameters']['samples']!=cfg['samples']:raise ValueError('unequal requested chain lengths')
        for i in range(cfg['samples']):
            raw=str((mp.parent/f'geometry_{i}.dat').relative_to(study))
            tasks.append(dict(root=str(root),study=str(study),raw=raw,cfg=cfg,validator=validator,sources=sources))
            chain_rows.append(dict(**entry,snapshot=i,raw=raw))
    outputs=[]
    # Numerical sparse kernels do not need nested BLAS worker pools.
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(_measure_one,task) for task in tasks]
        for i,f in enumerate(as_completed(futures),1):
            outputs.append(f.result())
            if i%64==0:print(json.dumps({'measurements_completed':i,'total':len(tasks)}),flush=True)
    by_raw={x['raw']:x for x in outputs}
    rows=[dict(e,**{k:v for k,v in by_raw[e['raw']].items() if k!='raw'}) for e in chain_rows]
    atomic_json(study/'measurement_index.json',rows)
    result=dict(status='MEASUREMENTS_COMPLETE',geometries=len(rows),full_manifold_checks=len(rows),
                exact_propagation=True,kind='native Monte Carlo, equilibrium not inferred',reproduction_pass=False,finished_at=now())
    atomic_json(study/'measurement_status.json',result);return result
