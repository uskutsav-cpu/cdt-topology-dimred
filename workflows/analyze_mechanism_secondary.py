#!/usr/bin/env python3
"""Exploratory persistence/branching analysis of a hash-verified synthetic study.

The joint scan uses one final geometry per independent construction seed.
The selected persistence locations are not a uniform all-start sample: the
primary workflow used the first three sorted sampled root labels.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from cdt_mechanisms.evidence import verify_run, create_run, sha256, write_json
from cdt_mechanisms.bottlenecks import wired_annulus_separator
from cdt_mechanisms.graph import from_neighbors
from cdt_mechanisms.triangulations import read_geometry
from cdt_mechanisms.inference import within_effect
from cdt_mechanisms.scales import max_statistic_scan


def doses(topology: dict) -> dict:
    """Censored H1/H2 lifetimes stay separate from completed finite lifetimes."""
    output={}
    for dimension in (1,2):
        matches=[row for row in topology['summary'] if row['dimension']==dimension]
        if len(matches)!=1: raise ValueError('expected exactly one summary per dimension')
        row=matches[0]
        for metric in ('observed_persistence','finite_total_persistence','censored_intervals'):
            value=float(row[metric])
            if not np.isfinite(value) or value<0: raise ValueError('invalid persistence summary')
            output[f'H{dimension}_{metric}']=value
    return output


def joined_rows(measurement: dict, persistence: list, diffusion: dict, radius: int, sigma: int) -> list:
    roots=np.asarray(diffusion['roots']); rows=[]
    if len(set(map(int,roots)))!=len(roots): raise ValueError('duplicate diffusion roots')
    index={int(root):i for i,root in enumerate(roots)}
    features={(r['root'],r['radius']):r for r in measurement['features']}
    controls=measurement['controls']; T=controls['time_extent']
    for top in persistence:
        root=int(top['root'])
        if root not in index or (root,radius) not in features:
            raise ValueError('topology root has no paired diffusion/features')
        j=index[root]
        if not diffusion['pre_mix'][j,sigma] or not np.isfinite(diffusion['ds'][j,sigma]): continue
        feature=features[(root,radius)]; t=controls['lower_time'][j]; typ=controls['lower_vertex_count'][j]
        rows.append(dict(root=root,outcome=float(diffusion['ds'][j,sigma]),**doses(top),
             conductance=feature['conductance'],annular_components=feature['annular_components'],
             spanning_annular_branches=feature['spanning_annular_branches'],
             graph_cycle_fraction=feature['graph_cycle_fraction'],
             controls=[float(np.log(feature['ball_vertices'])),controls['root_equilateral_deficit'][j],
                       float(np.sin(2*np.pi*t/T)),float(np.cos(2*np.pi*t/T)),int(typ==1),int(typ==2)]))
    return rows


def produce(output: Path, source: Path) -> None:
    verify_run(source)
    summary=json.loads((source/'summary.json').read_text()); config=summary['config']
    radius=int(config['primary_radius']); sigma=int(config['primary_sigma'])
    local=[]; aggregate=[]; separator_rows=[]
    for record in summary['geometries']:
        name=record['name']; folder=source/name
        measurement=json.loads((folder/'measurement.json').read_text())
        persistence=json.loads((folder/'persistence.json').read_text())
        with np.load(folder/'diffusion.npz',allow_pickle=False) as arrays:
            diffusion={key:arrays[key].copy() for key in arrays.files}
        for row in joined_rows(measurement,persistence,diffusion,radius,sigma):
            local.append(dict(**row,configuration=name,seed=record['seed']))
        g=read_geometry(folder/'geometry.dat'); a=from_neighbors(g.neighbors)
        separators=[]
        for top in persistence:
            root=int(top['root'])
            try:
                sep=wired_annulus_separator(a,root,1,radius)
                separator_rows.append(dict(configuration=name,**sep)); separators.append(sep['cut_weight'])
            except ValueError as exc:
                separator_rows.append(dict(configuration=name,root=root,status='undefined',reason=str(exc)))
        if record['flip_count']!=config['flip_counts'][-1]: continue
        features={}
        for metric in ('conductance','annular_components','spanning_annular_branches','graph_cycle_fraction'):
            for scale in config['radii']:
                values=[row[metric] for row in measurement['features'] if row['radius']==scale]
                features[f'{metric}_radius_{scale}']=float(np.mean(values))
        pp=[doses(top) for top in persistence]
        for key in pp[0]: features[key]=float(np.mean([p[key] for p in pp]))
        features['mean_wired_edge_cut']=float(np.mean(separators)) if separators else None
        operators=json.loads((folder/'operators.json').read_text())
        outcomes=[operators['full_discrete_trace']['ds'][time] for time in config['analysis_sigmas']]
        aggregate.append(dict(seed=record['seed'],features=features,outcomes=outcomes))
    estimates={}
    exposures=['H1_observed_persistence','H2_observed_persistence','H1_finite_total_persistence',
               'H2_finite_total_persistence','annular_components','spanning_annular_branches','graph_cycle_fraction']
    for exposure in exposures:
        try:
            result=within_effect([r[exposure] for r in local],[r['outcome'] for r in local],
                    [r['controls'] for r in local],[r['configuration'] for r in local],[r['seed'] for r in local])
            estimates[exposure]=dict(**result,unadjusted_secondary_p_value=True)
        except ValueError as exc: estimates[exposure]=dict(status='not_identifiable',reason=str(exc))
    names=sorted(aggregate[0]['features']); excluded=[]; kept=[]
    for name in names:
        values=[r['features'][name] for r in aggregate]
        if any(v is None or not np.isfinite(v) for v in values) or np.ptp(values)<1e-12:
            excluded.append(name)
        else: kept.append(name)
    if kept and len(aggregate)>=8:
        scan=max_statistic_scan([[r['features'][name] for name in kept] for r in aggregate],
               [r['outcomes'] for r in aggregate],[r['seed'] for r in aggregate],permutations=499,seed=211)
    else: scan=dict(status='not_identifiable')
    write_json(output/'secondary_analysis.json',dict(
        scientific_status='EXPLORATORY_SYNTHETIC_ONLY',post_primary_analysis=True,
        source_run=source.name,selected_local_rows=len(local),local_sigma=sigma,local_radius=radius,
        persistence_sampling='first three sorted sampled root labels; not uniform all-start persistence',
        observed_horizon=config['topology_horizon'],selected_local_estimates=estimates,
        jointly_scanned_features=kept,excluded_constant_or_missing_features=excluded,
        diffusion_times=config['analysis_sigmas'],independent_final_geometry_aggregates=aggregate,
        joint_max_statistic_scan=scan,
        important_limitations=['Only eight independent construction seeds; not CDT chains.',
        'Lifetime is a nested-ball filtration lifetime, not the paper effective-topology scale.',
        'Finite and censored intervals are separate; ball boundaries can create homology.',
        'Secondary local p-values are unadjusted and exploratory; not confirmatory findings.',
        'Volume, curvature, branching, and necks can change together under the intervention.'],
        production_gates_changed=False,topology_causal_mechanism_established=False))
    write_json(output/'wired_separators.json',separator_rows)
    write_json(output/'selected_local_rows.json',local)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'results/mechanisms_secondary')
    args=parser.parse_args(); source=args.source.resolve(); verify_run(source)
    path,reused=create_run(args.output,{'analysis':'secondary-persistence-branching-v1'},
                  lambda root:produce(root,source),external_inputs={
                  'source_manifest_sha256':sha256(source/'manifest.json'),'workflow_sha256':sha256(__file__)})
    print(json.dumps(dict(result=str(path),hash_verified_reuse=reused,scientific_status='EXPLORATORY_SYNTHETIC_ONLY')))

if __name__=='__main__': main()
