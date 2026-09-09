"""Read-only audit of the ORIGINAL run_chain.py manifests and diagnostics.csv.

No synthetic trajectory is substituted for absent physical data. Diagnostic
screens are necessary checks, not proof of thermalization or a reproduction PASS.
Checkpoint-inherited RNG streams do not become independent because a seed field differs.
"""
from __future__ import annotations
from pathlib import Path
import csv,json,hashlib,subprocess
from collections import Counter,defaultdict
import numpy as np
from cdt_mechanisms.evidence import sha256,jsonable


def safe_path(root,relative):
    root=Path(root).resolve();raw=Path(relative)
    if raw.is_absolute() or '..' in raw.parts:raise ValueError('native path must stay inside repository')
    p=root/raw
    if p.is_symlink() or any(x.is_symlink() for x in p.parents if x!=root.parent):raise ValueError('symlink input forbidden')
    if not p.resolve().is_relative_to(root) or not p.is_file():raise ValueError(f'missing native file: {relative}')
    return p


def diagnostic_screen(chains,*,rhat_limit=1.01,minimum_ess=400.,minimum_chains=4):
    """Rank/folded split Rhat plus bulk/tail ESS, using ArviZ's tested backend."""
    import arviz as az
    x=np.asarray(chains,dtype=float)
    if x.ndim!=2 or x.shape[0]<2 or x.shape[1]<8 or not np.isfinite(x).all():
        raise ValueError('need >=2 finite chains with >=8 draws each')
    if any(np.ptp(row)==0 for row in x):
        return dict(status='UNDEFINED_CONSTANT_CHAIN',pass_screen=False,shape=list(x.shape))
    duplicate=any(np.array_equal(x[i],x[j]) for i in range(len(x)) for j in range(i))
    r=float(np.asarray(az.rhat(x,method='rank')));bulk=float(np.asarray(az.ess(x,method='bulk')))
    tail=float(np.asarray(az.ess(x,method='tail',prob=(.05,.95))));mean_ess=float(np.asarray(az.ess(x,method='mean')))
    finite=np.isfinite([r,bulk,tail,mean_ess]).all()
    passed=finite and not duplicate and len(x)>=minimum_chains and r<=rhat_limit and min(bulk,tail)>=minimum_ess
    lag1=[float(np.corrcoef(row[:-1],row[1:])[0,1]) for row in x]
    return dict(status='PASS_SCREEN' if passed else 'FAIL_SCREEN',pass_screen=bool(passed),
        rank_folded_split_rhat=r,bulk_ess=bulk,tail_ess=tail,mean_ess=mean_ess,
        ess_implied_tau=float(x.size/mean_ess),lag1_autocorrelation=lag1,
        identical_chain_trajectories=duplicate,chains=len(x),draws_per_chain=x.shape[1],
        arviz_version=az.__version__,limits=dict(rhat=rhat_limit,ess=minimum_ess,chains=minimum_chains),
        reproduction_pass=False)


def read_native_trace(path,*,max_rows=2_000_000):
    values=[];sweeps=[];couplings=[];proposed=np.zeros(5);accepted=np.zeros(5)
    keys=['N0','N3','N31','peak_slice']
    with Path(path).open() as handle:
        reader=csv.DictReader(handle)
        required={'sweep','phase','k3',*keys,*[f'attempt_{j}' for j in range(1,6)],*[f'accept_{j}' for j in range(1,6)]}
        if not reader.fieldnames or not required<=set(reader.fieldnames):raise ValueError('wrong native diagnostics schema')
        for row in reader:
            if row['phase']!='measure':continue
            sweep=int(row['sweep'])
            if sweeps and sweep!=sweeps[-1]+1:raise ValueError('measurement sweep sequence is incomplete or duplicated')
            sweeps.append(sweep);values.append([float(row[k]) for k in keys]);couplings.append(float(row['k3']))
            p=np.array([int(row[f'attempt_{j}']) for j in range(1,6)])
            a=np.array([int(row[f'accept_{j}']) for j in range(1,6)])
            if np.any(a<0) or np.any(p<a):raise ValueError('invalid move acceptance counters')
            proposed+=p;accepted+=a
            if len(values)>max_rows:raise ValueError('trace row budget exceeded; raise it explicitly')
    if len(values)<8:raise ValueError('too few physical measurement sweeps')
    data=np.asarray(values)
    if not np.isfinite(data).all() or not np.isfinite(couplings).all() or np.any(data<=0):raise ValueError('invalid physical observable')
    if np.ptp(couplings)>1e-10:raise ValueError('k3 tuning continued during measurement')
    if accepted.sum()==0:raise ValueError('chain has no accepted measurement moves')
    return dict(values=data,columns=keys,sweeps=np.asarray(sweeps),k3=couplings[0],
        acceptance=np.divide(accepted,proposed,out=np.zeros(5),where=proposed>0),proposed=proposed,accepted=accepted)


def load_native_job(root,path,*,require_current_binary=True):
    root=Path(root).resolve();path=Path(path).resolve();m=json.loads(path.read_text());cfg=m.get('parameters',{})
    if m.get('stage')!='simulation' or m.get('status')!='complete':raise ValueError('native simulation is not complete')
    if cfg.get('initial_checkpoint') or m.get('initial_checkpoint_sha256') or 'inherited' in str(m.get('rng_origin','')).lower():
        raise ValueError('checkpoint-inherited RNG: must be grouped by original chain lineage, not declared independent')
    job=m.get('configuration_id','')
    if len(job)!=20 or any(c not in '0123456789abcdef' for c in job):raise ValueError('invalid native job id')
    outputs=m.get('output_hashes')
    if not isinstance(outputs,dict) or not outputs:raise ValueError('native output hash inventory absent')
    for rel,digest in outputs.items():
        p=safe_path(root,rel)
        if sha256(p)!=digest:raise ValueError(f'corrupt native output: {rel}')
    if require_current_binary:
        binary=safe_path(root,'build/simulator/cdt-run')
        if sha256(binary)!=m.get('binary_sha256'):raise ValueError('native job used a different binary; archive and review its provenance')
    trace_rel=f'data/raw/{job}/diagnostics.csv'
    if trace_rel not in outputs:raise ValueError('diagnostics trace not bound to native output hashes')
    trace=read_native_trace(root/trace_rel)
    expected=int(cfg['samples'])*int(cfg.get('sample_stride',1))
    if len(trace['sweeps'])!=expected:raise ValueError('measurement trace length disagrees with declared schedule')
    if trace['sweeps'][0]!=int(cfg['tune'])+int(cfg['burn'])+1:raise ValueError('measurement started at wrong sweep')
    geometries=[]
    for index in range(int(cfg['samples'])):
        rel=f'data/raw/{job}/geometry_{index}.dat'
        if rel not in outputs:raise ValueError('missing hash-bound physical geometry snapshot')
        geometries.append(dict(path=rel,sha256=outputs[rel],index=index,
            sweep=int(cfg['tune'])+int(cfg['burn'])+(index+1)*int(cfg.get('sample_stride',1))))
    validation=m.get('geometry_validation',[])
    if len(validation)!=len(geometries) or not all(v.get('all_vertex_links_S2') for v in validation):
        raise ValueError('full native geometry link validation absent')
    widths=[];max_fractions=[]
    for v in validation:
        a=np.asarray(v['spatial_volume'],dtype=float);T=len(a)
        if T<3 or np.any(a<=0):raise ValueError('invalid spatial volume profile')
        d=np.minimum((np.arange(T)-int(a.argmax()))%T,(int(a.argmax())-np.arange(T))%T)
        widths.append(float(np.sqrt(np.sum(a*d*d)/a.sum())));max_fractions.append(float(a.max()/a.sum()))
    return dict(job_id=job,seed=int(cfg['seed']),coupling=float(cfg['k0']),target=int(cfg['target']),
        binary=m['binary_sha256'],manifest_sha256=sha256(path),trace=trace,geometry=geometries,
        profile_width=np.asarray(widths),profile_peak_fraction=np.asarray(max_fractions),native_manifest=m)


def audit_repository(root,*,minimum_chains=4,minimum_ess=400.,rhat_limit=1.01):
    root=Path(root).resolve();required=['.git','workflows/run_chain.py','workflows/run_chain_safe.py',
        'external/3d-cdt/simulation.cpp','build/simulator/cdt-run','configs/methods/production_gates.json']
    missing=[rel for rel in required if not (root/rel).exists()]
    candidates=sorted((root/'results/manifests').glob('*.json'));jobs=[];failures=[];statuses=Counter()
    for path in candidates:
        try:m=json.loads(path.read_text())
        except Exception as exc:failures.append(dict(path=str(path.relative_to(root)),error=str(exc)));continue
        if m.get('stage')!='simulation' or '.through_' in path.name:continue
        statuses[str(m.get('status'))]+=1
        if m.get('status')!='complete':continue
        try:jobs.append(load_native_job(root,path))
        except Exception as exc:failures.append(dict(path=str(path.relative_to(root)),error=str(exc)))
    grouped=defaultdict(list)
    for job in jobs:grouped[job['coupling'],job['target']].append(job)
    screens=[]
    for (coupling,target),group in sorted(grouped.items()):
        result=dict(coupling=coupling,target=target,jobs=[g['job_id'] for g in group],screens={})
        if len({g['seed'] for g in group})!=len(group) or len({g['binary'] for g in group})!=1:
            result.update(status='FAIL_PROVENANCE',pass_screen=False)
        elif len(group)<minimum_chains:
            result.update(status='INSUFFICIENT_INDEPENDENT_CHAINS',pass_screen=False)
        elif len({len(g['trace']['values']) for g in group})!=1 or len({len(g['profile_width']) for g in group})!=1:
            result.update(status='UNEQUAL_SCHEDULES_REQUIRES_EXPLICIT_ALIGNMENT',pass_screen=False)
        else:
            kw=dict(minimum_chains=minimum_chains,minimum_ess=minimum_ess,rhat_limit=rhat_limit)
            for j,key in enumerate(group[0]['trace']['columns']):
                result['screens'][key]=diagnostic_screen([g['trace']['values'][:,j] for g in group],**kw)
            for key in ['profile_width','profile_peak_fraction']:
                result['screens'][key]=diagnostic_screen([g[key] for g in group],**kw)
            result['acceptance_by_chain']=[g['trace']['acceptance'] for g in group]
            result['mean_N3']=[float(g['trace']['values'][:,1].mean()) for g in group]
            result['pass_screen']=all(v['pass_screen'] for v in result['screens'].values())
            result['status']='PASS_SCREEN' if result['pass_screen'] else 'FAIL_SCREEN'
        screens.append(result)
    gates={};gatepath=root/'configs/methods/production_gates.json'
    if gatepath.exists():gates=json.loads(gatepath.read_text())
    all_gates_open=all(gates.get(k,{}).get('status')=='PASS' and gates[k].get('evidence') for k in [
        'baseline_reproduction','effective_topology_2d_reproduction','coarsegrain_3d_validation','microscopic_mapping_validation'])
    passed=bool(screens) and all(s['pass_screen'] for s in screens) and not failures and not missing
    return jsonable(dict(status='READY_FOR_BASELINE_REVIEW' if passed else 'BLOCKED',repository=str(root),
        missing_requirements=missing,native_manifest_status_counts=dict(statuses),valid_native_jobs=len(jobs),
        failures=failures,ensemble_screens=screens,production_gate_records=gates,all_production_gate_statuses_open=all_gates_open,
        no_process_liveness_inferred=True,physical_measurements_run=False,reproduction_pass=False,
        production_gates_changed=False,note='Diagnostic thresholds introduced by this continuation; not a historical preregistration.'))
