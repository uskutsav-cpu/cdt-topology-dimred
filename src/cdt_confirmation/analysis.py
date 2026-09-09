"""Locked primary replication plus explicitly secondary controlled analyses."""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
from cdt_mechanisms.scales import max_statistic_scan,residual_correlations,held_out_ridge
from cdt_mechanisms.inference import matched_pairs
from cdt_mechanisms.evidence import sha256
from .statistics import correlation_test,holm,within_with_null,paired_effect
from .provenance import stage,identity,write_json,verify


def load_run(root):
    root=Path(root);protocol=json.loads((root/'protocol.json').read_text());index=json.loads((root/'index.json').read_text())
    records={r['seed']:r for r in index['records']};out=[]
    for seed in protocol['design']['training_seeds']+protocol['design']['confirmation_seeds']:
        p=root/records[seed]['path'];manifest=verify(p)
        expected=protocol['design']
        config=manifest['identity']['config']
        if config.get('seed')!=seed or config.get('design')!=expected:
            raise ValueError('stage seed or design disagrees with locked protocol')
        if manifest['identity']['source']!=protocol['kernel_sources']:
            raise ValueError('stage measurement source disagrees with locked protocol')
        out.append(dict(summary=json.loads((p/'summary.json').read_text()),rows=json.loads((p/'root_measurements.json').read_text()),path=p,
                        diffusion=dict(np.load(p/'diffusion.npz',allow_pickle=False))))
    if len({x['summary']['geometry_digest'] for x in out})!=len(out):raise ValueError('duplicate geometry in independent units')
    return protocol,index,out


def _controls(rows):
    return np.asarray([[np.log(r['ball_vertices_r4']),np.log(r['ball_vertices_r8']),r['curvature_proxy'],
        float(r['tetra_type']==1),float(r['tetra_type']==2),np.sin(2*np.pi*r['time_slice']/4),np.cos(2*np.pi*r['time_slice']/4)] for r in rows])


def _within(items,key,sigma,seed):
    rows=[r for item in items for r in item['rows']]
    cfg=np.concatenate([np.repeat(item['summary']['seed'],len(item['rows'])) for item in items])
    x=np.asarray([r[key] for r in rows]);y=np.asarray([r[f'Ds_{sigma}'] for r in rows]);c=_controls(rows)
    return within_with_null(x,y,c,cfg,cfg,seed=seed)


def _matching(items):
    rows=[];z=[];strata=[];seeds=[]
    for item in items:
        rr=item['rows'];x=np.asarray([r['H1_finite_total_persistence'] for r in rr]);q1,q3=np.quantile(x,[.25,.75])
        if q1>=q3:continue
        for r in rr:
            value=r['H1_finite_total_persistence']
            if value<=q1 or value>=q3:
                rows.append(r);z.append(int(value>=q3));seeds.append(item['summary']['seed'])
                strata.append(f"{item['summary']['seed']}_{r['tetra_type']}")
    if len(rows)<4:return dict(status='NO_OVERLAP')
    match=matched_pairs(z,_controls(rows),np.asarray(strata),caliper=.5)
    # Existing matching reports (high exposure, low exposure, distance).
    pairs=np.asarray([(a,b) for a,b,_ in match['pairs']],dtype=int)
    if len(pairs)==0:return dict(status='NO_MATCHES',matching=match)
    y=np.asarray([r['Ds_32'] for r in rows]);seeds=np.asarray(seeds)
    dif=[]
    for seed in np.unique(seeds[pairs[:,0]]):
        pp=pairs[seeds[pairs[:,0]]==seed];dif.append(float(np.mean(y[pp[:,0]]-y[pp[:,1]])))
    return dict(matching=match,eligible_rows=len(rows),retained_fraction=2*len(pairs)/len(rows),
        paired_geometry_effect=paired_effect(dif,seed=6123) if len(dif)>=4 else None,
        causal_claim=False,interpretation='high-minus-low persistence matched association; not isolated topology intervention')


def analyze_run(root):
    root=Path(root);protocol,index,items=load_run(root);design=protocol['design'];ntrain=len(design['training_seeds'])
    train=items[:ntrain];test=items[ntrain:];plan_path=Path(__file__).resolve().parents[2]/'configs/confirmation/analysis_plan.json'
    inputs={'protocol':sha256(root/'protocol.json'),'index':sha256(root/'index.json'),'analysis_plan':sha256(plan_path)}
    inputs.update({str(x['summary']['seed']):sha256(x['path']/'manifest.json') for x in items})
    ident=identity(dict(stage='independent confirmation analysis',plan=json.loads(plan_path.read_text())),inputs)
    def producer(out):
        feature=design['primary_feature'];sigma=design['primary_sigma']
        def primary(subset,seed):
            x=[i['summary']['aggregates'][feature] for i in subset];y=[i['summary']['full_ds'][str(sigma)] for i in subset]
            return correlation_test(x,y,direction='negative',permutations=design['primary_permutations'],
                bootstraps=design['bootstrap_repetitions'],seed=seed)
        main=primary(test,design['primary_analysis_seed']);training=primary(train,design['primary_analysis_seed']+1)
        np.savez_compressed(out/'primary_nulls.npz',confirmation=main.pop('null_distribution'),training=training.pop('null_distribution'))
        within={feature:_within(test,feature,32,33001),'conductance_r4':_within(test,'conductance_r4',16,33002)}
        adjusted=holm([v['estimate']['p_value'] for v in within.values()])
        for value,p in zip(within.values(),adjusted):value['holm_adjusted_p']=float(p)
        radii=design['radii'];sigmas=design['sigmas']
        def matrices(subset):
            x=np.asarray([[i['summary']['aggregates'][f'conductance_r{r}'] for r in radii] for i in subset])
            y=np.asarray([[i['summary']['full_ds'][str(s)] for s in sigmas] for i in subset])
            return x,y
        xt,yt=matrices(train);xv,yv=matrices(test)
        scan=max_statistic_scan(xv,yv,[i['summary']['seed'] for i in test],permutations=1999,seed=44001)
        np.savez_compressed(out/'scale_nulls.npz',maxima=scan.pop('null_maxima'))
        rms_train=np.mean([i['diffusion']['rms_distance'][sigmas] for i in train],axis=0)
        rms_test=np.mean([i['diffusion']['rms_distance'][sigmas] for i in test],axis=0)
        ridge=held_out_ridge(xt,yt,xv,yv,radii,rms_test,sigmas)
        ridge.pop('measured_radius_alignment',None);ridge.pop('sqrt_sigma_alignment',None)
        # Test train-selected cells jointly with a fixed signed-mean statistic.
        rt=residual_correlations(xt,yt);rv=residual_correlations(xv,yv);selected=np.nanargmax(np.abs(rt),axis=0)
        signs=np.sign(rt[selected,np.arange(len(sigmas))]);score=float(np.mean(signs*rv[selected,np.arange(len(sigmas))]))
        rng=np.random.default_rng(44002);null=[]
        for _ in range(1999):
            rr=residual_correlations(xv,yv[rng.permutation(len(yv))]);null.append(float(np.mean(signs*rr[selected,np.arange(len(sigmas))])))
        ridge['held_out_signed_mean_correlation']=score;ridge['held_out_permutation_p']=float((1+np.sum(np.asarray(null)>=score-1e-15))/2000)
        delta=np.asarray(radii)[selected];align={}
        for name,dt,dv in [('empirical',rms_train,rms_test),('sqrt',np.sqrt(sigmas),np.sqrt(sigmas))]:
            c=float(np.exp(np.mean(np.log(delta/dt))))
            align[name]=dict(training_fitted_c=c,confirmation_log_rmse=float(np.sqrt(np.mean(np.log(delta/(c*dv))**2))))
        branch={}
        for j,key in enumerate(['neck_count','mean_separated_vertices','largest_separated_vertices','summed_separated_vertices','branch_size_entropy']):
            try:
                res=correlation_test([i['summary']['necks'][key] for i in test],[i['summary']['full_ds']['32'] for i in test],
                    direction='two-sided',permutations=1999,bootstraps=1999,seed=55000+j)
                res.pop('null_distribution');branch[key]=res
            except ValueError as exc:branch[key]=dict(status='UNDEFINED',reason=str(exc))
        valid=[v for v in branch.values() if 'permutation_p' in v]
        for v,p in zip(valid,holm([v['permutation_p'] for v in valid])):v['holm_adjusted_p']=float(p)
        checks=[c for i in items for c in i['summary']['field_checks']]
        write_json(out/'analysis.json',dict(primary_confirmation=main,training_replication=training,within=within,
            matching=_matching(test),scale_scan=scan,training_selected_ridge=ridge,scale_alignment=align,branch_descriptors=branch,
            n_geometries=len(items),training_geometries=ntrain,confirmation_geometries=len(test),
            total_roots=sum(i['summary']['n_roots'] for i in items),
            finite_field_comparisons=len(checks),finite_field_disagreements=sum(not c['same_barcode_as_F2'] for c in checks),
            root_census_all=all(i['summary']['root_census'] for i in items),
            minimum_pre_mix_fraction=min(i['summary']['mean_pre_mix']['32'] for i in items),
            independent_rank_checks=sum(len(i['summary']['independent_rank_checks']) for i in items),
            physical_CDT=False,production_gates_changed=False,
            scope='constructed product triangulations; new seeds and all roots; no physical coupling or equilibrium claim'))
    path,reused=stage(root/'analysis',ident,producer);print(json.dumps(dict(analysis_path=str(path),reused=reused)),flush=True)
    return path
