#!/usr/bin/env python3
from pathlib import Path
import argparse,concurrent.futures,json,os,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(k,'1')
import numpy as np
from cdt_mechanisms.fem import metric_mesh,assemble,midpoint_refinement,refinement_audit
from cdt_mechanisms.triangulations import bipyramid,product_cdt,stacked_sphere,random_flips,undo_flips,write_geometry
from cdt_mechanisms.graph import from_neighbors,distances
from cdt_confirmation.operators import low_modes,trace_bounds,dual_spectrum,calibrate_clock
from cdt_confirmation.measurement import legacy_validate,neck_features
from cdt_confirmation.fields import rooted
from cdt_confirmation.walks import propagate
from cdt_confirmation.statistics import paired_effect
from cdt_confirmation.provenance import identity,stage,write_json,verify
from cdt_mechanisms.evidence import sha256


def job(payload):
    cfg,seed,count,clock,output=payload
    ident=identity(dict(stage='intervention and FEM refinement',config=cfg,seed=seed,flips=count,clock=clock))
    def produce(out):
        start=time.perf_counter();initial=stacked_sphere(cfg['spatial_vertices'],seed=seed)
        faces,ledger=random_flips(initial,count,seed=seed+10000)
        assert undo_flips(faces,ledger)==initial
        g=product_cdt(faces,cfg['time_slices']);validation=legacy_validate(g);write_geometry(g,out/'geometry.dat')
        walk=propagate(from_neighbors(g.neighbors),np.arange(len(g.tetra)),48,moving_probability=cfg['moving_probability'])
        np.savez_compressed(out/'diffusion.npz',**{k:v for k,v in walk.items() if isinstance(v,np.ndarray)})
        dd=distances(from_neighbors(g.neighbors),np.arange(len(g.tetra)))
        persistence=[rooted(g.tetra,d,cfg['horizon'])['fields'][2]['features'] for d in dd]
        write_json(out/'root_persistence.json',persistence)
        dual=dual_spectrum(g,cfg['moving_probability']);dual_heat=trace_bounds(dual,cfg['dual_times'])
        times=np.asarray(cfg['dual_times'])/clock['fem_eigenvalue_to_dual_ratio']
        mesh=metric_mesh(g.tetra);levels=[];previous=None
        for level in range(cfg['refinement_levels']):
            fem=assemble(mesh);spectrum=low_modes(fem,cfg['sparse_modes']);heat=trace_bounds(spectrum,times)
            entry=dict(level=level,n_vertices=mesh.n_vertices,n_tetrahedra=len(mesh.tetra),spectrum=spectrum,heat=heat)
            if previous is not None:
                entry['patch_test']=refinement_audit(previous[0],fem,previous[1])
                old=levels[-1]['spectrum']['eigenvalues'];nmode=min(16,len(old),len(spectrum['eigenvalues']))
                entry['maximum_low_mode_ritz_increase']=float(np.max(spectrum['eigenvalues'][:nmode]-old[:nmode]))
                entry['maximum_first_15_relative_change']=float(np.max(np.abs(spectrum['eigenvalues'][1:nmode]/old[1:nmode]-1)))
            levels.append(entry)
            if level<cfg['refinement_levels']-1:
                mesh,p=midpoint_refinement(mesh);previous=(fem,p)
        last=levels[-1]['heat'];penultimate=levels[-2]['heat']
        width=last['ds_upper']-last['ds_lower'];change=np.abs(last['ds_truncated']-penultimate['ds_truncated'])
        screen=(width<=cfg['maximum_ds_tail_width'])&(change<=cfg['maximum_refinement_ds_change'])
        write_json(out/'operators.json',dict(seed=seed,flips=count,validation=validation,clock=clock,
            levels=levels,dual_spectrum=dual,dual_heat=dual_heat,finite_refinement_screen=screen,
            refined_tail_width=width,last_refinement_ds_change=change,
            necks=neck_features(faces),mean_H1_total=float(np.mean([p['H1_finite_total_persistence'] for p in persistence])),
            exact_reversal=True,unchanged_N0=len(g.time),unchanged_N3=len(g.tetra),
            full_discrete_ds={str(t):float(walk['full_ds'][t]) for t in cfg['dual_times']},
            runtime_seconds=time.perf_counter()-start,physical_CDT=False,continuum_convergence_established=False))
        write_json(out/'surgery.json',dict(ledger=ledger,exact_reversal=True))
    path,reused=stage(output,ident,produce)
    return dict(seed=seed,flips=count,path=str(path),reused=reused)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results/confirmation/operators')
    ap.add_argument('--workers',type=int,default=2);ap.add_argument('--config',type=Path,default=ROOT/'configs/confirmation/operators.json')
    args=ap.parse_args();cfg=json.loads(args.config.read_text());args.output.mkdir(parents=True,exist_ok=True)
    if not 1<=args.workers<=4:raise ValueError('workers 1..4 required')
    def reference(out):
        g=product_cdt(bipyramid(cfg['spatial_vertices']),cfg['time_slices']);legacy_validate(g)
        mesh=metric_mesh(g.tetra);mesh,_=midpoint_refinement(mesh)
        fem=low_modes(assemble(mesh));dual=dual_spectrum(g,cfg['moving_probability'])
        clock=calibrate_clock(dual['eigenvalues'],fem['eigenvalues'],*cfg['clock_modes'])
        write_json(out/'clock.json',clock);write_json(out/'reference_spectra.json',dict(fem=fem,dual=dual))
    ref,reused=stage(args.output/'reference',identity(dict(stage='independent clock reference',config=cfg)),reference)
    clock=json.loads((ref/'clock.json').read_text());start=time.perf_counter()
    jobs=[(cfg,s,n,clock,str(args.output/'measurements')) for s in cfg['seeds'] for n in cfg['flip_counts']]
    records=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for rec in pool.map(job,jobs):
            rec['path']=str(Path(rec['path']).relative_to(args.output));records.append(rec);print(json.dumps(rec),flush=True)
    summaries={(r['seed'],r['flips']):json.loads((args.output/r['path']/'operators.json').read_text()) for r in records}
    paired=[];t=cfg['primary_comparison_time'];j=cfg['dual_times'].index(t)
    for s in cfg['seeds']:
        before=summaries[s,0];after=summaries[s,cfg['flip_counts'][-1]]
        paired.append(dict(seed=s,dual_discrete_change=after['full_discrete_ds'][str(t)]-before['full_discrete_ds'][str(t)],
            dual_continuous_change=after['dual_heat']['ds_truncated'][j]-before['dual_heat']['ds_truncated'][j],
            fem_refined_change=after['levels'][-1]['heat']['ds_truncated'][j]-before['levels'][-1]['heat']['ds_truncated'][j],
            fem_change_interval=[after['levels'][-1]['heat']['ds_lower'][j]-before['levels'][-1]['heat']['ds_upper'][j],
                                 after['levels'][-1]['heat']['ds_upper'][j]-before['levels'][-1]['heat']['ds_lower'][j]],
            finite_refinement_pass=before['finite_refinement_screen'][j] and after['finite_refinement_screen'][j],
            neck_change=after['necks']['neck_count']-before['necks']['neck_count'],
            H1_total_change=after['mean_H1_total']-before['mean_H1_total']))
    report=dict(records=records,clock=clock,paired=paired,wall_seconds=time.perf_counter()-start,workers=args.workers,
        effects={k:paired_effect([r[k] for r in paired],seed=72001+i) for i,k in enumerate(['dual_discrete_change','dual_continuous_change','fem_refined_change','neck_change','H1_total_change'])},
        physical_CDT=False,production_gates_changed=False,continuum_convergence_established=False)
    inputs={r['path']:sha256(args.output/r['path']/'manifest.json') for r in records}
    target,_=stage(args.output/'analysis',identity(dict(stage='paired operator analysis',config=cfg),inputs),lambda p:write_json(p/'summary.json',report))
    print(json.dumps(dict(summary=str(target/'summary.json'))),flush=True)

if __name__=='__main__':main()
