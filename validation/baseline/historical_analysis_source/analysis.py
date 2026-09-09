"""Fail-closed baseline assessment with explicit estimands and finite-size limits."""
from __future__ import annotations
from pathlib import Path
import csv
import io
import platform
import warnings
import numpy as np
import arviz as az
from .chain import read_trace, checkpoint_header
from .design import validate_design
from .io import atomic_bytes,atomic_json,digest,immutable_json,load_json,now,sha256,verify_inventory,lock
from .statistics import diagnostic,dimension,log_dimension,root_jackknife,block_curves


def clean(value):
    if isinstance(value,np.ndarray):return clean(value.tolist())
    if isinstance(value,np.generic):return clean(value.item())
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,float) and not np.isfinite(value):return None
    return value


def _summarize_curves(cube,pop,floors,cfg,key):
    C,S,R,L=cube.shape;p=cube.mean(axis=2);ds=dimension(p)
    mean_ds=ds.mean(axis=(0,1));annealed=dimension(p.mean(axis=(0,1)))
    root_se=root_jackknife(cube,pop)
    half=dimension(cube[:,:,:max(2,R//2),:].mean(axis=2)).mean(axis=(0,1))
    low,high=cfg['analysis_window'];window=np.arange(low,high+1)
    floor=np.mean(floors);valid=np.isfinite(mean_ds)&(p.mean(axis=(0,1))>cfg['limits']['stationary_multiple']*floor)
    valid[:low]=False;valid[high+1:]=False
    records=[];boot={}
    for block in cfg['limits']['block_lengths']:
        b,a=block_curves(p,block,cfg['bootstrap_replicates'],int(digest({'seed':cfg['bootstrap_seed'],'key':key,'block':block})[:16],16))
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            q=np.nanquantile(b,[.025,.975],axis=0);aq=np.nanquantile(a,[.025,.975],axis=0)
        conservative=np.array([q[0]-1.96*root_se,q[1]+1.96*root_se])
        boot[f'block_{block}_mean_ds']=b;boot[f'block_{block}_annealed']=a
        records.append(dict(block_length=block,blocks_per_chain=S//block,pointwise_95=q,
                            conservative_pointwise_95=conservative,annealed_pointwise_95=aq,
                            max_conservative_halfwidth=float(np.max((conservative[1]-conservative[0])[valid]/2)) if valid.any() else None))
    primary=records[-1];ci=np.asarray(primary['conservative_pointwise_95'])
    ds_diagnostics={str(s):diagnostic(ds[:,:,s],cfg['limits']) for s in cfg['diagnostic_sigmas']}
    p_diagnostics={str(s):diagnostic(p[:,:,s],cfg['limits']) for s in cfg['diagnostic_sigmas']}
    taus=[r.get('tau_proxy',float('inf')) for r in ds_diagnostics.values()]
    times=np.flatnonzero(valid);peak=int(times[np.argmax(mean_ds[times])]) if len(times) else None
    first=ds[:,:S//2].mean(axis=(0,1));second=ds[:,S//2:].mean(axis=(0,1))
    max_drift=float(np.max(np.abs(first[valid]-second[valid]))) if valid.any() else None
    max_root=float(np.max(np.abs(half[valid]-mean_ds[valid]))) if valid.any() else None
    checks=dict(valid_window=bool(valid.any()),
                enough_blocks=primary['blocks_per_chain']>=cfg['limits']['minimum_blocks'],
                block_exceeds_twice_tau=bool(np.isfinite(max(taus)) and primary['block_length']>=2*max(taus)),
                pointwise_precision=bool(valid.any() and primary['max_conservative_halfwidth']<=cfg['limits']['ds_halfwidth']),
                root_refinement=bool(max_root is not None and max_root<=cfg['limits']['root_refinement_ds']),
                drift=bool(max_drift is not None and max_drift<=cfg['limits']['drift_ds']),
                ds_diagnostics=all(x['pass_screen'] for x in ds_diagnostics.values()),
                return_diagnostics=all(x['pass_screen'] for x in p_diagnostics.values()))
    result=dict(estimands={'mean_geometry_ds':'differentiate root-mean P on each geometry, then equally average geometries/chains',
                          'annealed_ds':'differentiate the ensemble-averaged P; not interchangeable with mean_geometry_ds'},
                return_mean=p.mean(axis=(0,1)),mean_geometry_ds=mean_ds,annealed_ds=annealed,
                secondary_log_derivative=log_dimension(p.mean(axis=(0,1))),
                chain_mean_ds=ds.mean(axis=1),root_jackknife_standard_error=root_se,
                nested_half_root_ds=half,max_nested_half_root_difference=max_root,
                first_half_ds=first,second_half_ds=second,max_half_chain_drift=max_drift,
                valid_time_mask=valid,stationary_return_mean=floor,valid_times=int(valid.sum()),
                uncertainty='hierarchical circular block bootstrap plus separately reported root jackknife; conservative additive pointwise margin, not simultaneous coverage',
                block_sensitivity=records,Ds_diagnostics=ds_diagnostics,P_diagnostics=p_diagnostics,
                diagnostic_screens=checks,pass_screens=all(checks.values()),
                peak_time_in_valid_window=peak,peak_ds=float(mean_ds[peak]) if peak is not None else None,
                peak_is_window_boundary=bool(peak in (low,high)) if peak is not None else None)
    return result,boot


def analyze_study(root,cfg,study):
    root=Path(root).resolve();study=Path(study).resolve();cfg=validate_design(cfg)
    if load_json(study/'requested_schedule.json')!=cfg:raise ValueError('analysis configuration differs from executed schedule')
    if load_json(study/'measurement_status.json')['status']!='MEASUREMENTS_COMPLETE':raise ValueError('measurement incomplete')
    mi=load_json(study/'measurement_index.json');ci=load_json(study/'chain_index.json')
    if len(mi)!=len(ci)*cfg['samples']:raise ValueError('missing/extra measured snapshots')
    source_files=['src/cdt_baseline/analysis.py','src/cdt_baseline/statistics.py','src/cdt_baseline/design.py','src/cdt_baseline/io.py','src/cdt_baseline/chain.py']
    source_hashes={p:sha256(root/p) for p in source_files}
    # A code change gives a new immutable analysis directory, not a overwritten result.
    contract=dict(design=cfg,sources=source_hashes,measurement_index_sha256=sha256(study/'measurement_index.json'),chain_index_sha256=sha256(study/'chain_index.json'))
    key=digest(contract)[:20];out=study/'analyses'/key;out.mkdir(parents=True,exist_ok=True)
    with lock(out.parent/(key+'.lock')):
        mp=out/'manifest.json'
        if mp.exists():
            m=load_json(mp);verify_inventory(out,m['outputs'])
            atomic_json(study/'analysis_index.json',{'analysis':key,'manifest_sha256':sha256(mp)})
            return load_json(out/'summary.json')
        groups={};boot_arrays={};total_attempts=0;total_time=0.;all_seeds=[];rng_pairs=[]
        for e in ci:
            mp0=study/'raw'/e['job']/'manifest.json';m=load_json(mp0)
            if sha256(mp0)!=e['manifest_sha256'] or m['status']!='complete' or m['stage']!='production':raise ValueError('native chain changed/not production')
            verify_inventory(mp0.parent,m['outputs']);p=m['parameters'];all_seeds.append(p['seed'])
            cp=checkpoint_header(mp0.parent/'checkpoint.bin');rng_pairs.append((cp['simulation_rng_state'],cp['universe_rng_state']))
            total_attempts+=(p['burn']+p['samples']*p['sample_stride'])*p['attempts'];total_time+=m['total_elapsed_seconds']
            trace=read_trace(mp0.parent/'diagnostics.csv',p)['rows'];data=[r for r in trace if r['phase']=='measure']
            if len(data)!=p['samples']*p['sample_stride'] or p['tune']!=0 or m['initial_checkpoint_inherited']:
                raise ValueError('invalid production sampling/lineage')
            sub=groups.setdefault((e['volume'],e['k0']),[]);sub.append((e,m,data))
        if len(set(all_seeds))!=len(all_seeds) or len(set(rng_pairs))!=len(rng_pairs):raise ValueError('duplicate production RNG provenance')
        results=[]
        for (volume,k0),entries in sorted(groups.items()):
            entries.sort(key=lambda x:x[0]['chain']);C=len(entries);S=cfg['samples']
            if C!=cfg['chains'] or [e[0]['chain'] for e in entries]!=list(range(C)):raise ValueError('missing/duplicate chain identities')
            if len({e[1]['parameters']['k3'] for e in entries})!=1:raise ValueError('independent chains do not share frozen k3')
            native={name:diagnostic(np.array([[float(r[name]) for r in e[2]] for e in entries]),cfg['limits'])
                    for name in ('N0','N3','N31','peak_slice')}
            acceptance={str(j):{'proposed':sum(int(r[f'attempt_{j}']) for e in entries for r in e[2]),
                                 'accepted':sum(int(r[f'accept_{j}']) for e in entries for r in e[2])} for j in range(1,6)}
            for x in acceptance.values():x['fraction']=x['accepted']/x['proposed'] if x['proposed'] else None
            by_job={e[0]['job']:e[0]['chain'] for e in entries}
            rows=[r for r in mi if r['job'] in by_job];geoms={};curve_metadata={};data={};fits=[]
            for row in rows:
                mpath=study/'measurements'/row['measurement']/'manifest.json';m=load_json(mpath)
                if sha256(mpath)!=row['manifest_sha256']:raise ValueError('measurement manifest changed')
                verify_inventory(mpath.parent,m['outputs']);c=by_job[row['job']];s=row['snapshot']
                if (c,s) in geoms:raise ValueError('duplicate geometry entry')
                if sha256(study/row['raw'])!=m['contract']['input_sha256']:raise ValueError('raw geometry changed')
                geoms[c,s]=load_json(mpath.parent/'geometry.json');fits.append(load_json(mpath.parent/'profile_fit.json'))
                with np.load(mpath.parent/'returns.npz',allow_pickle=False) as z:
                    for curve in m['curves']:
                        label=curve['key'];data.setdefault(label,{})[c,s]=z[label].copy();curve_metadata.setdefault(label,{})[c,s]=curve
            if len(geoms)!=C*S:raise ValueError('unequal geometry census')
            shape={name:diagnostic(np.array([[geoms[c,s][name] for s in range(S)] for c in range(C)]),cfg['limits'])
                   for name in ('profile_width','profile_participation','profile_peak_fraction','peak_volume')}
            curves={};missing={}
            for label,values in sorted(data.items()):
                if len(values)!=C*S or len({v.shape for v in values.values()})!=1:
                    missing[label]={'available':len(values),'required':C*S,'reason':'no ensemble estimate from a selected successful subset'};continue
                cube=np.array([[values[c,s] for s in range(S)] for c in range(C)])
                pop=np.array([[curve_metadata[label][c,s]['population'] for s in range(S)] for c in range(C)])
                floor=np.array([[curve_metadata[label][c,s]['stationary_return'] for s in range(S)] for c in range(C)])
                summary,boot=_summarize_curves(cube,pop,floor,cfg,f'V{volume}_k{k0}_{label}')
                summary['policy']=curve_metadata[label][0,0]['policy'];summary['rho']=curve_metadata[label][0,0]['rho'];curves[label]=summary
                for name,value in boot.items():boot_arrays[f'V{volume}_k{k0}_{label}_{name}']=value
            for policy in ('full_uniform','full_peak31','excised_uniform_hold','excised_uniform_renormalize'):
                for rho in [cfg['rho'],*cfg['rho_sensitivity']]:
                    label=f'{policy}_rho_{rho:g}'
                    if label not in curves and label not in missing:
                        missing[label]={'available':0,'required':C*S,'reason':'no valid ensemble of this requested representation'}
            primary=curves[f'full_uniform_rho_{cfg["rho"]:g}'];rho_checks={}
            for rho in cfg['rho_sensitivity']:
                other=curves[f'full_uniform_rho_{rho:g}'];times=np.arange(cfg['max_steps']+1);at=times*cfg['rho']/rho
                overlap=np.asarray(primary['valid_time_mask'])&(at>=cfg['analysis_window'][0])&(at<=cfg['analysis_window'][1])
                overlap&=np.interp(at,times,np.asarray(other['valid_time_mask'],float))>.999
                delta=np.asarray(primary['mean_geometry_ds'])-np.interp(at,times,other['mean_geometry_ds'])
                difference=float(np.max(np.abs(delta[overlap]))) if overlap.any() else None
                rho_checks[str(rho)]=dict(compared_at='equal rho*sigma',overlap_times=int(overlap.sum()),max_absolute_Ds_difference=difference,
                                          pass_screen=bool(difference is not None and difference<=cfg['limits']['drift_ds']))
            checks=dict(native_diagnostics=all(x['pass_screen'] for x in native.values()),
                        profile_diagnostics=all(x['pass_screen'] for x in shape.values()),
                        volume_center=abs(native['N3']['mean']/volume-1)<=cfg['limits']['volume_relative_offset'],
                        acceptance=all(x['accepted']>0 for x in acceptance.values()),
                        spectral=primary['pass_screens'],rho_sensitivity=all(x['pass_screen'] for x in rho_checks.values()))
            result=dict(volume_target=volume,k0=k0,k3=entries[0][1]['parameters']['k3'],chains=C,snapshots_per_chain=S,
                        native_diagnostics=native,geometry_diagnostics=shape,acceptance=acceptance,curves=curves,
                        unresolved_curve_ensembles=missing,rho_comparison=rho_checks,
                        stalk_resolved_configurations=sum(f.get('excision_status')=='resolved_adaptation' for f in fits),
                        checks=checks,pass_screens=all(checks.values()))
            results.append(result)
        curve_peaks=[dict(volume=r['volume_target'],k0=r['k0'],mean_N3=r['native_diagnostics']['N3']['mean'],
                         Ds_peak=r['curves'][f'full_uniform_rho_{cfg["rho"]:g}']['peak_ds'],
                         sigma_peak=r['curves'][f'full_uniform_rho_{cfg["rho"]:g}']['peak_time_in_valid_window']) for r in results]
        all_pass=all(r['pass_screens'] for r in results)
        reasons=[]
        for r in results:
            reasons += [f'V={r["volume_target"]},k0={r["k0"]}: {name} failed' for name,ok in r['checks'].items() if not ok]
        reasons+=['Finite-volume and condensate/reference agreement is not established by these screens.',
                  'No reviewed paper-level numerical reference/matched-boundary calibration has been supplied.',
                  'A clean complete Git checkout/full legacy stack must be recorded separately from the pinned-source export used here.']
        decision=dict(status='DIAGNOSTIC_SCREENS_PASS_REFERENCE_PENDING' if all_pass else 'NOT_ESTABLISHED',
                      reproduction_pass=False,diagnostic_screens_pass=all_pass,physical_monte_carlo_executed=True,
                      equilibrium_proved=False,production_gates_changed=False,reasons=reasons)
        output=dict(schema=1,study_kind=cfg['kind'],analysis_id=key,created_at=now(),design=cfg,groups=results,
                    finite_size_summary=curve_peaks,production_proposals=total_attempts,native_production_process_seconds=total_time,
                    independent_production_chains=len(ci),native_snapshots=len(mi),decision=decision,
                    environment=dict(python=platform.python_version(),numpy=np.__version__,arviz=az.__version__),
                    limitations=['128 or more saved configurations are not automatically independent.',
                                 'Peak-start/full-graph curves are not substitutes for the historical stalk-excised observable.',
                                 'Confidence intervals conditional on finite trajectories are not trustworthy equilibrium intervals when diagnostics fail.',
                                 'No fit is constrained to yield Ds=2 or Ds=3. No configurations were discarded to manufacture agreement.'])
        atomic_json(out/'summary.json',clean(output));buf=io.BytesIO();np.savez_compressed(buf,**boot_arrays);atomic_bytes(out/'bootstrap.npz',buf.getvalue())
        text='# Native CDT baseline assessment\n\nStatus: **'+decision['status']+'**. Native Monte Carlo ran; REPRODUCTION_PASS is false.\n\n'
        text+='| Target N3 | Chains | Snapshots/chain | N3 Rhat | Peak-slice Rhat | Peak-slice bulk ESS | Stalk-resolved snapshots |\n|---|---|---|---|---|---|---|\n'
        for r in results:
            a=r['native_diagnostics'];text+=f'| {r["volume_target"]} | {r["chains"]} | {r["snapshots_per_chain"]} | {a["N3"].get("rank_folded_rhat",float("nan")):.6g} | {a["peak_slice"].get("rank_folded_rhat",float("nan")):.6g} | {a["peak_slice"].get("bulk_ess",float("nan")):.6g} | {r["stalk_resolved_configurations"]} |\n'
        text+='\n## Unresolved requirements\n\n'+'\n'.join('- '+s for s in reasons)+'\n'
        atomic_bytes(out/'REPORT.md',text.encode());atomic_json(out/'manifest.json',dict(contract=contract,outputs={'summary.json':sha256(out/'summary.json'),'bootstrap.npz':sha256(out/'bootstrap.npz'),'REPORT.md':sha256(out/'REPORT.md')}))
        atomic_json(study/'analysis_index.json',{'analysis':key,'manifest_sha256':sha256(out/'manifest.json')})
        return clean(output)
