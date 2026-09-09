"""Tuning pilot -> dispersed independent starts -> frozen-coupling native chains."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading
from .chain import native_environment, run_native_job, checkpoint_header
from .design import validate_design, native_parameters, stage_seed
from .initial import write_seed
from .io import atomic_json, digest, immutable_json, load_json, now, sha256
from .native import build_native


def _parallel(tasks,workers):
    cancel=threading.Event();results=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(fn,cancel) for fn in tasks]
        try:
            for future in as_completed(futures):results.append(future.result())
        except BaseException:
            cancel.set()
            for future in futures:future.cancel()
            raise
    return results


def simulate(root: Path, cfg: dict, study: Path, *, workers=2, capacity=200000, timeout_seconds=1800.):
    root=Path(root).resolve();study=Path(study).resolve();cfg=validate_design(cfg)
    if type(workers) is not int or not 1<=workers<=4:raise ValueError('workers must be in [1,4]')
    if capacity is not None and capacity<2*max(cfg['volumes']):
        raise ValueError('choose pool capacity at least twice maximum requested volume')
    study.mkdir(parents=True,exist_ok=True)
    # Extensions preserve the experiment identity, changing only requested length.
    stable={k:v for k,v in cfg.items() if k!='samples'}
    record={'design':stable,'sampled_distribution':'pinned patched native CDT, S=-k0*N0+k3*N3 + 4e-5*(N3-target)^2',
            'adaptation':'one separate tuning job per volume/coupling, then a common fixed k3 for every independent chain',
            'initialization':'native-compatible minimal S2 x S1; independently seeded native dispersal at declared volumes',
            'reproduction_pass':False}
    immutable_json(study/'protocol.json',record)
    if (study/'requested_schedule.json').exists():
        old=load_json(study/'requested_schedule.json')
        if cfg['samples']<old['samples']:raise ValueError('cannot reduce requested study length')
        immutable_json(study/'schedule_history'/f"samples_{old['samples']}.json",old)
    atomic_json(study/'requested_schedule.json',cfg)
    build=build_native(root,capacity=capacity)
    immutable_json(study/'build_reference.json',{'build_id':build['build_id'],'binary_sha256':build['binary_sha256'],
                   'source_lock_sha256':sha256(root/'configs/baseline/source_lock.json'),'source_checkout':build['source_checkout'],
                   'patches':build['patches'],'capacity':capacity})
    initial=study/'initial'/f"T{cfg['time_extent']}.dat"
    validation=write_seed(cfg['time_extent'],initial)
    immutable_json(study/'initial/validation.json',validation)
    calibrations={};tune_tasks=[]
    for volume in cfg['volumes']:
        for k0 in cfg['couplings']:
            p=native_parameters(cfg,volume,k0,1.17778+.155*(k0-1),stage_seed(cfg,'tuning',volume,k0,0),stage='tuning')
            label=f'V{volume}_k0_{k0}_tuning'
            tune_tasks.append(lambda cancel,v=volume,k=k0,p=p,l=label: (v,k,run_native_job(root,build,study,l,initial,p,
                              stage='tuning',lineage={'purpose':'excluded adaptation pilot'},timeout_seconds=timeout_seconds,cancel_event=cancel)))
    for volume,k0,job in _parallel(tune_tasks,workers):
        if job['status']!='complete':
            atomic_json(study/'simulation_status.json',{'status':'PAUSED_TUNING','job':job['job_id'],'reproduction_pass':False})
            return load_json(study/'simulation_status.json')
        header=checkpoint_header(study/'raw'/job['job_id']/'checkpoint.bin')
        calibrations[volume,k0]=(job,header['k3'])
    # Frozen coupling values are fixed before any production outcome is seen.
    freeze=[{'volume':v,'k0':k,'k3':value,'tuning_job':job['job_id'],'tuning_manifest_sha256':sha256(study/'raw'/job['job_id']/'manifest.json')}
            for (v,k),(job,value) in sorted(calibrations.items())]
    immutable_json(study/'frozen_couplings.json',freeze)
    tasks=[]
    for (volume,k0),(tuner,k3) in sorted(calibrations.items()):
        for c in range(cfg['chains']):
            def chain_task(cancel,v=volume,k=k0,k3=k3,c=c,tuner=tuner):
                prep=native_parameters(cfg,v,k,k3,stage_seed(cfg,'dispersal',v,k,c),stage='dispersal',chain=c)
                start=run_native_job(root,build,study,f'V{v}_k0_{k}_chain{c}_dispersal',initial,prep,stage='dispersal',
                                    lineage={'chain':c,'volume':v,'k0':k,'tuning_job':tuner['job_id']},
                                    timeout_seconds=timeout_seconds,cancel_event=cancel)
                if start['status']!='complete':return {'volume':v,'k0':k,'chain':c,'status':'PAUSED_DISPERSAL','job':start['job_id']}
                inp=study/'raw'/start['job_id']/'geometry_0.dat'
                p=native_parameters(cfg,v,k,k3,stage_seed(cfg,'production',v,k,c))
                job=run_native_job(root,build,study,f'V{v}_k0_{k}_chain{c}_production',inp,p,stage='production',
                    lineage={'chain':c,'volume':v,'k0':k,'dispersal_job':start['job_id'],'dispersal_input_sha256':sha256(inp),
                             'production_rng_reseeded':True},timeout_seconds=timeout_seconds,cancel_event=cancel)
                return {'volume':v,'k0':k,'chain':c,'status':job['status'],'job':job['job_id'],'k3':k3,
                        'seed':p['seed'],'manifest_sha256':sha256(study/'raw'/job['job_id']/'manifest.json')}
            tasks.append(chain_task)
    entries=_parallel(tasks,workers)
    entries.sort(key=lambda x:(x['volume'],x['k0'],x['chain']))
    atomic_json(study/'chain_index.json',entries)
    result=dict(status='NATIVE_RUNS_COMPLETE' if all(x['status']=='complete' for x in entries) else 'PAUSED_NATIVE_CHAINS',
                native_production_chains=len(entries),requested_snapshots=len(entries)*cfg['samples'],
                kind=cfg['kind'],finished_at=now(),equilibrium_established=False,reproduction_pass=False,
                production_gates_changed=False)
    atomic_json(study/'simulation_status.json',result)
    return result
