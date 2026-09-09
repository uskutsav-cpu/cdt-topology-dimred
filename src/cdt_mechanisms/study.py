"""Executable synthetic mechanism study and explicit saved-ensemble analysis."""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
from dataclasses import asdict
import json
import time
import numpy as np
import networkx as nx
from scipy import sparse
from .graph import from_neighbors, degrees, distances
from .bottlenecks import local_features, fiedler_sweep, wired_annulus_separator
from .diffusion import exact_diffusion, spectral_dimension, fit_walk_dimension, heat_trace_dimension, log_slope
from .persistence import independent_betti, geodesic_ball_persistence
from .triangulations import (bipyramid, stacked_sphere, product_cdt, random_flips, necks,
                            audit_cdt, geometry_digest, write_geometry, read_geometry)
from .fem import metric_mesh, assemble, full_spectrum, midpoint_refinement, refinement_audit
from .inference import within_effect, matched_pairs, coupling_decomposition, chain_bootstrap_curves
from .scales import max_statistic_scan, held_out_ridge, residual_correlations
from .evidence import write_json, sha256, jsonable, require_ensemble_manifest


def geometry_controls(g, a, roots, radii) -> dict:
    """Declared proxies, not continuum curvature or proof of confounder sufficiency."""
    edge_incidence=defaultdict(int)
    for cell in g.tetra:
        from itertools import combinations
        for e in combinations(sorted(map(int,cell)),2): edge_incidence[e]+=1
    # Equilateral Regge deficit at each edge (3D); valid only for this unit-edge metric.
    theta=np.arccos(1/3)
    deficit={e:2*np.pi-count*theta for e,count in edge_incidence.items()}
    root_deficit=[]
    for root in roots:
        es=list(combinations(sorted(map(int,g.tetra[root])),2))
        root_deficit.append(float(np.mean([deficit[e] for e in es])))
    T=int(np.max(g.time))+1
    lower=[]; types=[]
    for root in roots:
        times,counts=np.unique(g.time[g.tetra[root]],return_counts=True); ct=dict(zip(times,counts))
        t=next(int(t) for t in times if (int(t)+1)%T in ct)
        lower.append(t); types.append(int(ct[t]))
    return dict(root_equilateral_deficit=np.asarray(root_deficit),lower_time=np.asarray(lower),
                lower_vertex_count=np.asarray(types),time_extent=T,
                interpretation='equilateral edge-deficit proxy; not valid for unspecified nonunit metrics')


def measure_geometry(g, *, n_roots=16, max_steps=96, radii=(1,2,3,4,6,8),
                     seed=0, topology_roots=3, topology_horizon=8, do_fem=True) -> dict:
    if n_roots<4 or topology_roots<0: raise ValueError("need >=4 roots and nonnegative topology roots")
    audit=audit_cdt(g); a=from_neighbors(g.neighbors); rng=np.random.default_rng(seed)
    roots=np.sort(rng.choice(len(g.tetra),size=min(n_roots,len(g.tetra)),replace=False))
    diffusion=exact_diffusion(a,roots,int(max_steps)); ds=spectral_dimension(diffusion)
    features=local_features(a,roots,list(radii)); sweep=fiedler_sweep(a)
    topology=[]
    if topology_roots:
        dd=distances(a,roots[:topology_roots])
        for root,d in zip(roots[:topology_roots],dd):
            top=geodesic_ball_persistence(g.tetra,d,int(topology_horizon))
            topology.append(dict(root=int(root),**top))
    operators=None
    if do_fem:
        fem=assemble(metric_mesh(g.tetra)); spec=full_spectrum(fem)
        times=np.geomspace(.005,8,96); heat=heat_trace_dimension(spec['eigenvalues'],times)
        # A second mass choice is a sensitivity check, not a second continuum operator.
        lump=full_spectrum(assemble(metric_mesh(g.tetra),lumped=True))
        lump_heat=heat_trace_dimension(lump['eigenvalues'],times)
        d=degrees(a); q=sparse.diags(1/np.sqrt(d))
        dual_lap=sparse.eye(a.shape[0])-q@a@q
        # Complete spectrum for these modest synthetic meshes only.
        dual_eigs=np.linalg.eigvalsh(dual_lap.toarray())
        dual_heat=heat_trace_dimension(dual_eigs,np.geomspace(.1,256,96))
        # Full uniform-start trace: eliminates intervention start-location mismatch.
        sigma=np.arange(max_steps+1)
        eigen_p=np.clip(1-.5*dual_eigs,0,1)
        full_return=np.mean(eigen_p[:,None]**sigma[None,:],axis=0)
        full_ds=-2*log_slope(sigma,full_return)
        operators=dict(fem=spec,fem_heat=heat,lumped_heat=lump_heat,
                       full_discrete_trace=dict(sigma=sigma,returns=full_return,ds=full_ds,
                                                stationary_floor=1/len(g.tetra)),
                       dual_eigenvalues=dual_eigs,dual_heat=dual_heat,
                       diffusion_constants_aligned=False,continuum_limit_established=False)
    return dict(geometry_hash=geometry_digest(g),audit=audit,roots=roots,
                diffusion=diffusion,ds=ds,features=features,sweep=sweep,
                walk_fit=fit_walk_dimension(diffusion,4,min(24,max_steps-2)),
                topology=topology,operators=operators,
                controls=geometry_controls(g,a,roots,radii),global_betti=independent_betti(g.tetra))


def save_measurement(root: Path, name: str, result: dict):
    target=root/name; target.mkdir(parents=True,exist_ok=False)
    diff=result['diffusion']
    np.savez_compressed(target/'diffusion.npz',sigma=diff.sigma,roots=diff.roots,
                        returns=diff.returns,msd=diff.mean_square_distance,
                        stationary_return=diff.stationary_return,ds=result['ds']['ds'],
                        pre_mix=result['ds']['pre_mix'])
    basic={k:v for k,v in result.items() if k not in ('diffusion','ds','topology','operators')}
    basic['probability_mass_error']=diff.mass_error
    write_json(target/'measurement.json',basic)
    write_json(target/'persistence.json',result['topology'])
    if result['operators'] is not None: write_json(target/'operators.json',result['operators'])


def _finite_average(y):
    raw=np.asarray(y,dtype=float); valid=np.isfinite(raw)
    return float(raw[valid].mean()) if np.any(valid) else None


def _features_matrix(result,key,radii):
    lookup={(f['root'],f['radius']):f[key] for f in result['features']}
    return np.asarray([[lookup[(int(root),int(r))] for r in radii] for root in result['roots']])


def synthetic_statistics(seed=73) -> dict:
    """Known-coefficient and null controls; these observations are NOT CDT data."""
    rng=np.random.default_rng(seed); chains=24; configs_per_chain=3; roots=12
    n=chains*configs_per_chain*roots
    chain=np.repeat(np.arange(chains),configs_per_chain*roots)
    cfg=np.repeat(np.arange(chains*configs_per_chain),roots)
    control=rng.normal(size=(n,2)); exposure=.8*control[:,0]+rng.normal(size=n)
    offsets=rng.normal(size=chains*configs_per_chain)[cfg]
    outcome=-.7*exposure+.9*control[:,0]-.3*control[:,1]+offsets+rng.normal(scale=.15,size=n)
    fitted=within_effect(exposure,outcome,control,cfg,chain)
    null_outcome=.9*control[:,0]+offsets+rng.normal(scale=.5,size=n)
    null=within_effect(exposure,null_outcome,control,cfg,chain)
    # All starts in a pair share the same declared controls: exact overlap fixture.
    c0=rng.normal(size=(80,3)); z=np.repeat([0,1],80); cc=np.vstack((c0,c0))
    match=matched_pairs(z,cc,np.zeros(160,dtype=int),caliper=.01)
    x=rng.normal(size=(64,6)); y=rng.normal(size=(64,8))
    null_scan=max_statistic_scan(x,y,np.arange(64),permutations=199,seed=seed)
    signal=y.copy(); signal[:,3]=x[:,2]+rng.normal(scale=.1,size=64)
    positive=max_statistic_scan(x,signal,np.arange(64),permutations=199,seed=seed)
    levels=np.repeat([.5,1.5,2.],30); xx=levels+rng.normal(scale=.2,size=90)
    yy=-.6*xx+.8*levels+rng.normal(scale=.05,size=90)
    decomposition=coupling_decomposition(xx,yy,levels)
    return dict(known_effect=-.7,fitted=fitted,null=null,matching=match,
                null_scan=null_scan,positive_scan=positive,
                toy_coupling_decomposition=decomposition,
                provenance='synthetic calibration, not physical coupling observations')


def diffusion_calibration() -> list[dict]:
    output=[]
    for dimension,side in [(1,512),(2,64),(3,24)]:
        graph=nx.grid_graph(dim=[side]*dimension,periodic=True)
        graph=nx.convert_node_labels_to_integers(graph)
        a=nx.to_scipy_sparse_array(graph,format='csr',dtype=float)
        result=exact_diffusion(a,[0],128); ds=spectral_dimension(result)
        mask=(result.sigma>=32)&(result.sigma<=64)
        output.append(dict(lattice_dimension=dimension,side=side,
                           measured_ds=float(np.mean(ds['ds'][0,mask])),
                           walk_fit=fit_walk_dimension(result,16,64),mass_error=result.mass_error,
                           synthetic_graph_not_cdt=True))
    return output


def refinement_study() -> dict:
    g=product_cdt(bipyramid(6),3); mesh=metric_mesh(g.tetra); output=[]
    previous=None
    for level in range(3):
        fem=assemble(mesh); spec=full_spectrum(fem)
        entry=dict(level=level,vertices=mesh.n_vertices,tetrahedra=len(mesh.tetra),
                   volume=fem.volume,first_12_eigenvalues=spec['eigenvalues'][:12],
                   residual=spec['residual'])
        if previous is not None:
            entry['patch_test']=refinement_audit(previous[0],fem,previous[1])
            entry['ritz_monotonicity_max_increase']=float(np.max(spec['eigenvalues'][:12]-previous[2][:12]))
        output.append(entry)
        if level<2:
            fine,p=midpoint_refinement(mesh); previous=(fem,p,spec['eigenvalues']); mesh=fine
    return dict(levels=output,continuum_convergence_established=False,
                meaning='nested-space, metric-preserving refinement and low-mode sensitivity')


def run_synthetic_study(root: Path, config: dict) -> None:
    n=int(config['spatial_vertices']); T=int(config['time_slices']); seeds=list(config['seeds'])
    levels=list(config['flip_counts']); radii=list(config['radii']); times=np.asarray(config['analysis_sigmas'])
    max_steps=int(config['max_steps']); n_roots=int(config['n_roots']); all_results=[]; summary=[]; refinement_comparisons=[]
    for seed in seeds:
        initial=stacked_sphere(n,seed=int(seed),mode='random')
        for count in levels:
            name=f'seed_{seed}_flips_{count}'
            faces,ledger=random_flips(initial,int(count),seed=int(seed)+10_000)
            g=product_cdt(faces,T)
            result=measure_geometry(g,n_roots=n_roots,max_steps=max_steps,radii=radii,
                      seed=int(seed)+900,topology_roots=int(config['topology_roots']),
                      topology_horizon=int(config['topology_horizon']),do_fem=True)
            save_measurement(root,name,result); write_geometry(g,root/name/'geometry.dat')
            if seed in config.get('refined_fem_seeds',[]) and count in (levels[0],levels[-1]):
                mesh=metric_mesh(g.tetra); coarse=assemble(mesh)
                refined,pro=midpoint_refinement(mesh); fine=assemble(refined)
                refined_spec=full_spectrum(fine)
                refined_heat=heat_trace_dimension(refined_spec['eigenvalues'],result['operators']['fem_heat']['times'])
                low,high=config['fem_window']; ft=refined_heat['times']
                refinement_comparisons.append(dict(seed=seed,flip_count=count,
                    vertices=refined.n_vertices,tetrahedra=len(refined.tetra),
                    patch_test=refinement_audit(coarse,fine,pro),
                    window_mean_ds=float(np.mean(refined_heat['ds'][(ft>=low)&(ft<=high)])),
                    eigen_residual=refined_spec['residual']))
                write_json(root/name/'refined_fem.json',dict(spectrum=refined_spec,heat=refined_heat,
                         metric_preserved=True,continuum_limit_established=False))
            write_json(root/name/'surgery.json',dict(ledger=ledger,reverse_verified=True,
                       initial_spatial_faces=initial,final_spatial_faces=faces,
                       necks=necks(faces),intervention='spatial flips followed by foliated product construction',
                       topology_changed=False,boltzmann_sample=False))
            ds=result['ds']['ds']; mask=result['ds']['pre_mix']
            selected=np.asarray(ds[:,times]); selected_valid=mask[:,times]
            avg=np.where(selected_valid,selected,np.nan)
            op=result['operators']; fem_time=op['fem_heat']['times']; dual_time=op['dual_heat']['times']
            fem_low,fem_high=config['fem_window']; diffusion_low,diffusion_high=config['discrete_window']
            trace=op['full_discrete_trace']; trace_window=(trace['sigma']>=diffusion_low)&(trace['sigma']<=diffusion_high)
            if np.any(trace['returns'][trace_window]<=2*trace['stationary_floor']):
                raise ValueError('declared full-trace intervention window hits finite-size floor')
            summary.append(dict(name=name,seed=int(seed),flip_count=int(count),
                N0=len(g.time),N3=len(g.tetra),spatial_necks=necks(faces)['separating_triangle_count'],
                sweep_conductance=result['sweep']['sweep_conductance'],
                spectral_gap=result['sweep']['normalized_gap'],
                ds_window_mean=_finite_average(avg),
                full_trace_ds_window_mean=float(np.mean(trace['ds'][trace_window])),n_premix_root_times=int(selected_valid.sum()),
                fem_ds_window_mean=float(np.mean(op['fem_heat']['ds'][(fem_time>=fem_low)&(fem_time<=fem_high)])),
                dual_heat_ds_window_mean=float(np.mean(op['dual_heat']['ds'][(dual_time>=diffusion_low)&(dual_time<=diffusion_high)])),
                walk_dimension=result['walk_fit']['walk_dimension'],global_betti=result['global_betti'],
                mass_error=result['diffusion'].mass_error))
            all_results.append((name,seed,count,result))
    # Additional same-volume sphere with no non-facial triangular necks, not a paired causal control.
    contrast=product_cdt(bipyramid(n),T)
    ref=measure_geometry(contrast,n_roots=n_roots,max_steps=max_steps,radii=radii,seed=55,
                         topology_roots=int(config['topology_roots']),topology_horizon=int(config['topology_horizon']))
    save_measurement(root,'bipyramid_reference',ref); write_geometry(contrast,root/'bipyramid_reference/geometry.dat')
    # Within-configuration controls; all interventions sharing an initial seed stay in ONE cluster.
    xx=[]; yy=[]; cc=[]; cfg=[]; chain=[]; binary=[]; strata=[]
    primary_radius=int(config['primary_radius']); primary_sigma=int(config['primary_sigma'])
    for name,seed,count,result in all_results:
        x=_features_matrix(result,'conductance',[primary_radius])[:,0]
        f=_features_matrix(result,'ball_vertices',[primary_radius])[:,0]
        controls=result['controls']; t=controls['lower_time']; typ=controls['lower_vertex_count']
        matrix=np.column_stack((np.log(f),controls['root_equilateral_deficit'],
                                np.sin(2*np.pi*t/T),np.cos(2*np.pi*t/T),typ==1,typ==2))
        y=result['ds']['ds'][:,primary_sigma]; valid=result['ds']['pre_mix'][:,primary_sigma]&np.isfinite(x)
        xx.extend(x[valid]); yy.extend(y[valid]); cc.extend(matrix[valid]); cfg.extend([name]*int(valid.sum())); chain.extend([seed]*int(valid.sum()))
        binary.extend((x[valid]>np.median(x[valid])).astype(int))
        strata.extend([f'{name}:time{int(t[j])}:type{int(typ[j])}' for j in np.flatnonzero(valid)])
    inference=None
    try: inference=within_effect(xx,yy,cc,cfg,chain)
    except ValueError as exc: inference=dict(status='not_identifiable',reason=str(exc))
    try:
        matching=matched_pairs(binary,cc,strata,caliper=float(config.get('matching_caliper',1.)))
        pairs=matching['pairs']; yy_array=np.asarray(yy)
        matching['descriptive_matched_ds_difference']=float(np.mean([yy_array[a]-yy_array[b] for a,b,_ in pairs])) if pairs else None
        matching['comparison']='higher vs lower within-configuration radial conductance; exact configuration/time/type strata'
        matching['adjusted_effect_claim_permitted']=False
    except ValueError as exc:
        matching=dict(status='not_identifiable',reason=str(exc),adjusted_effect_claim_permitted=False)
    # A scale scan uses ONE graph at the final intervention per independent seed.
    final=[r for _,_,count,r in all_results if count==levels[-1]]
    xf=np.asarray([_features_matrix(r,'conductance',radii).mean(axis=0) for r in final])
    yf=np.asarray([r['ds']['ds'][:,times].mean(axis=0) for r in final])
    scan=None; ridge=None
    if len(final)>=8 and np.isfinite(xf).all() and np.isfinite(yf).all():
        scan=max_statistic_scan(xf,yf,seeds,permutations=int(config['permutations']),seed=371)
        ntrain=len(final)//2
        mean_rms=np.asarray([r['diffusion'].rms_distance[:,times].mean(axis=0) for r in final[ntrain:]]).mean(axis=0)
        ridge=held_out_ridge(xf[:ntrain],yf[:ntrain],xf[ntrain:],yf[ntrain:],radii,mean_rms,times)
    # Paired intervention effect is descriptive; seed bootstrap respects paired initial geometries.
    contrasts=[]
    for seed in seeds:
        before=next(s for s in summary if s['seed']==seed and s['flip_count']==levels[0])
        after=next(s for s in summary if s['seed']==seed and s['flip_count']==levels[-1])
        contrasts.append(dict(seed=seed,delta_necks=after['spatial_necks']-before['spatial_necks'],
                         delta_ds=after['full_trace_ds_window_mean']-before['full_trace_ds_window_mean'],
                         delta_mean_local_ds=after['ds_window_mean']-before['ds_window_mean'],
                         delta_fem_ds=after['fem_ds_window_mean']-before['fem_ds_window_mean'],
                         delta_gap=after['spectral_gap']-before['spectral_gap']))
    effects=np.asarray([[c['delta_ds'],c['delta_fem_ds'],c['delta_gap'],c['delta_necks']] for c in contrasts])
    bootstrap=chain_bootstrap_curves(effects,seeds,repetitions=499,seed=713)
    refined_effects=[]
    for seed in config.get('refined_fem_seeds',[]):
        rows=[r for r in refinement_comparisons if r['seed']==seed]
        if len(rows)==2:
            before=next(r for r in rows if r['flip_count']==levels[0])
            after=next(r for r in rows if r['flip_count']==levels[-1])
            refined_effects.append(dict(seed=seed,delta_refined_fem_ds=after['window_mean_ds']-before['window_mean_ds']))
    write_json(root/'summary.json',dict(config=config,geometries=summary,
        bipyramid_reference=dict(N3=len(contrast.tetra),global_betti=ref['global_betti'],
           spatial_necks=necks(bipyramid(n))['separating_triangle_count'],sweep=ref['sweep']),
        within_configuration_inference=inference,matched_geometry_controls=matching,
        scale_scan=scan,held_out_ridge=ridge,refined_fem_comparisons=refinement_comparisons,
        refined_fem_effects=refined_effects,
        paired_intervention_contrasts=contrasts,paired_seed_bootstrap=bootstrap,
        effect_columns=['delta_full_trace_ds','delta_fem_ds','delta_gap','delta_spatial_necks'],
        scientific_status='SYNTHETIC_METHOD_VALIDATION_ONLY',
        topology_causal_mechanism_established=False,physical_coupling_result=False,
        original_simulator_rerun=False,legacy_full_test_suite_rerun=False))
    write_json(root/'statistics_calibration.json',synthetic_statistics())
    write_json(root/'diffusion_calibration.json',diffusion_calibration())
    write_json(root/'fem_refinement.json',refinement_study())


def analyze_saved_ensemble(root: Path, manifest: dict, base: Path, config: dict) -> None:
    audit=require_ensemble_manifest(manifest,root=base); records=[]; all_rows=[]
    for index,record in enumerate(manifest['configurations']):
        geometry_path=(base/record['geometry']).resolve(); g=read_geometry(geometry_path)
        # The file is re-hashed immediately before use to narrow the TOCTOU window.
        if sha256(geometry_path)!=record['geometry_sha256']: raise ValueError("input changed after manifest validation")
        result=measure_geometry(g,n_roots=int(config['n_roots']),max_steps=int(config['max_steps']),
                    radii=config['radii'],seed=int(config['seed'])+index,
                    topology_roots=int(config.get('topology_roots',0)),
                    topology_horizon=int(config.get('topology_horizon',8)),do_fem=False)
        name=f'configuration_{index:06d}'; save_measurement(root,name,result)
        radius=int(config['primary_radius']); sigma=int(config['primary_sigma'])
        feat=_features_matrix(result,'conductance',[radius])[:,0]
        vol=_features_matrix(result,'ball_vertices',[radius])[:,0]
        ds=result['ds']['ds'][:,sigma]; valid=result['ds']['pre_mix'][:,sigma]&np.isfinite(feat)
        control=result['controls']; T=control['time_extent']; tt=control['lower_time']
        for j in np.flatnonzero(valid):
            all_rows.append(dict(x=float(feat[j]),y=float(ds[j]),
              controls=[float(np.log(vol[j])),float(control['root_equilateral_deficit'][j]),
                        float(np.sin(2*np.pi*tt[j]/T)),float(np.cos(2*np.pi*tt[j]/T))],
              config=record['configuration_id'],chain=record['chain_id'],coupling=record['coupling']))
        records.append(dict(**record,artifact_directory=name,N3=len(g.tetra),valid_starts=int(valid.sum()),
                            mean_conductance=_finite_average(feat[valid]),mean_ds=_finite_average(ds[valid])))
    try:
        within=within_effect([r['x'] for r in all_rows],[r['y'] for r in all_rows],
          [r['controls'] for r in all_rows],[r['config'] for r in all_rows],[r['chain'] for r in all_rows])
    except ValueError as exc: within=dict(status='not_identifiable',reason=str(exc))
    valid=[r for r in records if r['mean_ds'] is not None and r['mean_conductance'] is not None]
    try:
        between=coupling_decomposition([r['mean_conductance'] for r in valid],[r['mean_ds'] for r in valid],[r['coupling'] for r in valid])
    except ValueError as exc: between=dict(status='not_identifiable',reason=str(exc))
    write_json(root/'ensemble_analysis.json',dict(audit=audit,configurations=records,within_effect=within,
               descriptive_coupling_decomposition=between,scientific_status='EXPLORATORY_ONLY',
               no_thermalization_or_baseline_gate_inferred=True,production_gates_changed=False))
