"""Read-only checks of native, measurement and analysis evidence and lineage."""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import numpy as np
from .chain import checkpoint_header,read_trace
from .design import validate_design,stage_seed
from .io import digest,inside,load_json,sha256,verify_inventory
from .statistics import dimension


def verify_study(root,study):
    root=Path(root).resolve();study=Path(study).resolve();cfg=validate_design(load_json(study/'requested_schedule.json'))
    if load_json(study/'protocol.json')['design']!={k:v for k,v in cfg.items() if k!='samples'}:raise ValueError('protocol mismatch')
    ci=load_json(study/'chain_index.json');mi=load_json(study/'measurement_index.json');ai=load_json(study/'analysis_index.json')
    if len(ci)!=len(cfg['volumes'])*len(cfg['couplings'])*cfg['chains']:raise ValueError('missing/extra native chains')
    all_jobs={};artifacts=0;raw_bytes=0
    # Includes excluded tuning and dispersal jobs, not only successful production.
    for mp in sorted((study/'raw').glob('*/manifest.json')):
        record=load_json(mp)
        if record['status']!='complete' or record['job_id']!=mp.parent.name or digest(record['contract'])[:20]!=record['job_id']:
            raise ValueError('incomplete/invalid native job')
        verify_inventory(mp.parent,record['outputs']);artifacts+=len(record['outputs']);raw_bytes+=sum((mp.parent/p).stat().st_size for p in record['outputs'])
        params=record['parameters'];expected=params['tune']+params['burn']+params['samples']*params['sample_stride']
        if checkpoint_header(mp.parent/'checkpoint.bin')['completed_sweeps']!=expected:raise ValueError('checkpoint duration mismatch')
        if read_trace(mp.parent/'diagnostics.csv',params,collect=False)['row_count']!=expected:raise ValueError('trace duration mismatch')
        geos={p.name for p in mp.parent.glob('geometry_*.dat')}
        if geos!={f'geometry_{i}.dat' for i in range(params['samples'])}:raise ValueError('snapshot set mismatch')
        if sha256(mp.parent/'input.dat')!=record['contract']['input_sha256']:raise ValueError('initial-state hash mismatch')
        all_jobs[record['job_id']]=record
    frozen={(e['volume'],e['k0']):e for e in load_json(study/'frozen_couplings.json')}
    identities=set();prod={};seed_set=set()
    for row in ci:
        identity=(row['volume'],row['k0'],row['chain'])
        if identity in identities:raise ValueError('duplicate chain identity')
        identities.add(identity);record=all_jobs[row['job']];mp=study/'raw'/row['job']/'manifest.json';p=record['parameters']
        if sha256(mp)!=row['manifest_sha256'] or record['stage']!='production' or row['status']!='complete':raise ValueError('invalid indexed production job')
        seed=stage_seed(cfg,'production',*identity)
        if p['seed']!=seed or seed in seed_set or record['initial_checkpoint_inherited'] or p['tune']!=0:raise ValueError('independent-seed/production contract failed')
        seed_set.add(seed)
        if p['target']!=row['volume'] or p['k0']!=row['k0'] or p['k3']!=frozen[identity[:2]]['k3']:raise ValueError('couplings/volume differ from frozen ensemble')
        line=record['contract']['lineage'];start=all_jobs[line['dispersal_job']]
        if start['stage']!='dispersal' or start['contract']['lineage']['chain']!=row['chain']:raise ValueError('wrong dispersal lineage')
        if sha256(study/'raw'/start['job_id']/'geometry_0.dat')!=record['contract']['input_sha256']:raise ValueError('dispersal initial-state mismatch')
        prod[row['job']]=row
    for ensemble,f in frozen.items():
        tuner=all_jobs[f['tuning_job']]
        if tuner['stage']!='tuning' or sha256(study/'raw'/f['tuning_job']/'manifest.json')!=f['tuning_manifest_sha256']:
            raise ValueError('tuning provenance mismatch')
        if checkpoint_header(study/'raw'/f['tuning_job']/'checkpoint.bin')['k3']!=f['k3']:raise ValueError('frozen k3 differs from actual tuning result')
    if len(mi)!=len(ci)*cfg['samples']:raise ValueError('measurement census mismatch')
    seen=set();primary=defaultdict(dict);native_hashes=set()
    for row in mi:
        identity=(row['job'],row['snapshot'])
        if identity in seen or row['job'] not in prod or not 0<=row['snapshot']<cfg['samples']:raise ValueError('duplicate/missing measurement identity')
        seen.add(identity)
        expected=f'raw/{row["job"]}/geometry_{row["snapshot"]}.dat'
        if row['raw']!=expected:raise ValueError('measurement points to wrong snapshot')
        raw=inside(study,expected);mp=inside(study,f'measurements/{row["measurement"]}/manifest.json');m=load_json(mp)
        if sha256(mp)!=row['manifest_sha256'] or digest(m['contract'])[:20]!=row['measurement']:raise ValueError('measurement manifest identity mismatch')
        if m['contract']['input_sha256']!=sha256(raw):raise ValueError('geometry content mismatch')
        native_hashes.add(sha256(raw));verify_inventory(mp.parent,m['outputs']);artifacts+=len(m['outputs'])
        for name,h in m['contract']['sources'].items():
            if sha256(inside(root,name))!=h:raise ValueError('measurement source snapshot mismatch')
        g=load_json(mp.parent/'geometry.json')
        if not all(g[k] for k in ('all_edge_links_circles','all_vertex_links_S2','all_spatial_slices_S2')):raise ValueError('unvalidated geometry')
        with np.load(mp.parent/'returns.npz',allow_pickle=False) as arrays:
            for curve in m['curves']:
                key=curve['key'];P=arrays[key];roots=arrays[key+'_roots']
                if P.shape!=(curve['roots'],cfg['max_steps']+1) or not np.isfinite(P).all() or np.any(P<0) or np.any(P>1+1e-12):raise ValueError('invalid probability array')
                if not np.all(P[:,0]==1) or len(set(roots.tolist()))!=len(roots):raise ValueError('invalid root sample')
                if roots.min()<0 or roots.max()>=g['N3'] or curve['mass_error']>1e-10:raise ValueError('invalid root/mass metadata')
            key=f'full_uniform_rho_{cfg["rho"]:g}'
            e=prod[row['job']];primary[e['volume'],e['k0']][e['chain'],row['snapshot']]=arrays[key].mean(axis=0)
    if len(seen)!=len(ci)*cfg['samples']:raise ValueError('measurement census incomplete')
    # Exact repeated states can occur in Markov chains; repeated whole trajectories
    # are rejected in diagnostics, not by assuming every configuration is distinct.
    ap=inside(study,f'analyses/{ai["analysis"]}/manifest.json');a=load_json(ap)
    if sha256(ap)!=ai['manifest_sha256']:raise ValueError('selected analysis changed')
    if a['contract']['measurement_index_sha256']!=sha256(study/'measurement_index.json') or a['contract']['chain_index_sha256']!=sha256(study/'chain_index.json'):
        raise ValueError('analysis references stale indices')
    for name,h in a['contract']['sources'].items():
        if sha256(inside(root,name))!=h:raise ValueError('analysis source snapshot mismatch')
    verify_inventory(ap.parent,a['outputs']);artifacts+=len(a['outputs']);summary=load_json(ap.parent/'summary.json')
    for group in summary['groups']:
        values=primary[group['volume_target'],group['k0']]
        cube=np.array([[values[c,s] for s in range(cfg['samples'])] for c in range(cfg['chains'])])
        saved=group['curves'][f'full_uniform_rho_{cfg["rho"]:g}']
        for key,actual in [('mean_geometry_ds',dimension(cube).mean(axis=(0,1))),('annealed_ds',dimension(cube.mean(axis=(0,1))))]:
            reference=np.array([np.nan if x is None else x for x in saved[key]])
            if not np.allclose(reference,actual,rtol=1e-12,atol=1e-12,equal_nan=True):raise ArithmeticError('primary spectral statistic recomputation disagrees')
    if summary['decision']['reproduction_pass'] is not False or summary['decision']['production_gates_changed'] is not False:
        raise ValueError('this pipeline cannot certify externally reviewed reproduction or change existing gates')
    return dict(verified=True,native_jobs=len(all_jobs),independent_production_chains=len(ci),geometries=len(mi),
                unique_geometry_hashes=len(native_hashes),artifacts_verified=artifacts,native_artifact_bytes=raw_bytes,
                primary_estimands_recomputed=True,source_snapshots_match=True,
                physical_monte_carlo_executed=True,diagnostic_screens_pass=summary['decision']['diagnostic_screens_pass'],
                REPRODUCTION_PASS=False,production_gates_changed=False)
