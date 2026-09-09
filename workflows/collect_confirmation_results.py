#!/usr/bin/env python3
"""Collect current-source verified studies, generate figures, and publish a report atomically."""
from pathlib import Path
import argparse,importlib.util,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from cdt_confirmation.provenance import verify,identity,stage,write_json
from cdt_mechanisms.evidence import sha256

def choose(folder,name):
    candidates=[]
    for p in Path(folder).glob('*/'+name):
        m=verify(p.parent)
        if all(sha256(ROOT/'src'/k)==v for k,v in m['identity']['source'].items()):candidates.append(p)
    if len(candidates)!=1:raise ValueError(f'need exactly one current-source {name} in {folder}; found {len(candidates)}')
    return candidates[0]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run-root',type=Path,default=ROOT/'results/confirmation')
    ap.add_argument('--output',type=Path);args=ap.parse_args();root=args.run_root.resolve();output=args.output or root/'reports'
    primary_file=choose(root/'census/analysis','analysis.json')
    size_file=choose(root/'finite_size/analysis','summary.json')
    operator_file=choose(root/'operators_final/analysis','summary.json')
    read=lambda p:json.loads(Path(p).read_text())
    primary=read(primary_file);sizes=read(size_file);operators=read(operator_file)
    protocol=read(root/'census/protocol.json');index=read(root/'census/index.json')
    rows=[];inputs={str(p.relative_to(root)):sha256(p) for p in [primary_file,size_file,operator_file,root/'census/index.json',root/'census/protocol.json']}
    for rec in index['records']:
        path=root/'census'/rec['path'];verify(path);inputs[str(path.relative_to(root))+'/manifest.json']=sha256(path/'manifest.json')
        s=read(path/'summary.json');d=dict(np.load(path/'diffusion.npz',allow_pickle=False))
        rows.append(dict(seed=rec['seed'],subset='training' if rec['seed'] in protocol['design']['training_seeds'] else 'confirmation',
            H1=s['aggregates']['H1_finite_total_persistence'],Ds32=s['full_ds']['32'],branch_entropy=s['necks']['branch_size_entropy'],
            neck_count=s['necks']['neck_count'],rms=d['rms_distance'].tolist(),
            full_ds=[float(x) if np.isfinite(x) else None for x in d['full_ds']]))
    levels=[]
    for rec in operators['records']:
        path=root/'operators_final'/rec['path'];verify(path)
        inputs[str(path.relative_to(root))+'/manifest.json']=sha256(path/'manifest.json')
        o=read(path/'operators.json')
        levels.append(dict(seed=rec['seed'],flips=rec['flips'],levels=[dict(vertices=l['n_vertices'],ds32=l['heat']['ds_truncated'][-1]) for l in o['levels']]))
    for rec in sizes['records']:
        p=root/'finite_size'/rec['path'];verify(p);inputs[str(p.relative_to(root))+'/manifest.json']=sha256(p/'manifest.json')
    nulls=np.load(primary_file.parent/'primary_nulls.npz',allow_pickle=False)
    data=dict(primary=primary,finite_size=sizes,operators=operators,scatter=rows,operator_levels=levels,
              primary_null=nulls['confirmation'].tolist(),scope='constructed evidence; physical CDT not established')
    plot_path=ROOT/'workflows/plot_confirmation.py';inputs['plot_script']=sha256(plot_path);inputs['collector_script']=sha256(__file__)
    def producer(path):
        write_json(path/'COMPUTED_RESULTS.json',data)
        spec=importlib.util.spec_from_file_location('confirmation_plot_script',plot_path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.make_figures(path/'COMPUTED_RESULTS.json',path/'figures')
        a=primary['primary_confirmation'];within=primary['within'];effects=operators['effects']
        operator_status='UNRESOLVED' if not operators.get('continuum_convergence_established',False) else 'REVIEW_REQUIRED'
        report=f'''# Automatically collected confirmation results

Scope: constructed triangulations only. No physical chain, coupling mediation,
or continuum-limit claim is made. Existing production gates are unchanged.

## Independent persistence test

Confirmation geometries: {a['n_independent_geometries']}.
Pearson r: {a['pearson_r']:.9f}; one-sided permutation p: {a['permutation_p']:.6g}.
95% geometry bootstrap interval: {a['correlation_ci95']}.

Within-configuration persistence coefficient:
{within['H1_finite_total_persistence']['estimate']['coefficient']:.9f};
95% cluster interval: {within['H1_finite_total_persistence']['estimate']['ci95']}.

Controlled conductance coefficient:
{within['conductance_r4']['estimate']['coefficient']:.9f};
95% cluster interval: {within['conductance_r4']['estimate']['ci95']}.

## Limits and controls

Matched overlap fraction: {primary['matching']['retained_fraction']:.6f};
balance pass: {primary['matching']['matching']['balance_pass']}.
Scale-matching evidence does not establish a moving scaling band.

Dual discrete paired change: {effects['dual_discrete_change']['mean_difference']:.9f}.
FEM paired change: {effects['fem_refined_change']['mean_difference']:.9f};
95% sampling interval: {effects['fem_refined_change']['ci95']}.
Operator classification: **{operator_status}**.

Finite-size replication remains exploratory and inconclusive.
Full coefficients, intervals, corrections, seeds, and caveats are in COMPUTED_RESULTS.json.
Eleven PNG/SVG figures are generated directly from those saved measurements.
'''
        (path/'SUMMARY.md').write_text(report)
    p,reused=stage(output,identity(dict(kind='verified_collected_confirmation_report'),inputs=inputs),producer)
    print(json.dumps(dict(report=str(p/'SUMMARY.md'),reused=reused)))
if __name__=='__main__':main()
