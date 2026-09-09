#!/usr/bin/env python3
"""Descriptive before/after geometric confounder audit, no selected significance test."""
from pathlib import Path
from collections import Counter
from itertools import combinations
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from cdt_mechanisms.triangulations import read_geometry
from cdt_mechanisms.graph import from_neighbors,distances
from cdt_mechanisms.study import geometry_controls
from cdt_mechanisms.evidence import sha256
from cdt_confirmation.measurement import legacy_validate

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--selection',type=Path,default=ROOT/'docs/confirmation/FINAL_RUNS.json')
    ap.add_argument('--output',type=Path,default=ROOT/'validation/confirmation/intervention_geometry_controls.json')
    args=ap.parse_args();selection=json.loads(args.selection.read_text());root=ROOT/selection['operators_root']
    summary=json.loads((ROOT/selection['operators_analysis']).read_text());rows=[]
    for rec in summary['records']:
        path=root/rec['path']/'geometry.dat';g=read_geometry(path);valid=legacy_validate(g)['report']
        order=Counter(e for cell in g.tetra for e in combinations(sorted(map(int,cell)),2));values=np.array(list(order.values()))
        a=from_neighbors(g.neighbors);roots=np.arange(len(g.tetra));d=distances(a,roots)
        curvature=geometry_controls(g,a,roots,[4,8])['root_equilateral_deficit']
        rows.append(dict(seed=rec['seed'],flips=rec['flips'],geometry_sha256=sha256(path),
            N0=valid['N0'],N1=valid['N1'],N3=valid['N3'],edge_order_mean=float(values.mean()),
            edge_order_sd=float(values.std()),edge_order_max=int(values.max()),
            root_curvature_mean=float(curvature.mean()),root_curvature_sd=float(curvature.std()),
            mean_ball_volume_r4=float(np.sum(d<=4,axis=1).mean()),mean_ball_volume_r8=float(np.sum(d<=8,axis=1).mean()),
            mean_pairwise_dual_distance=float(d.mean()),dual_diameter=int(d.max())))
    pairs=[]
    for seed in sorted({r['seed'] for r in rows}):
        a=next(r for r in rows if r['seed']==seed and r['flips']==0)
        b=next(r for r in rows if r['seed']==seed and r['flips']!=0)
        pairs.append(dict(seed=seed,changes={k:b[k]-a[k] for k in a if k not in ['seed','flips','geometry_sha256']}))
    result=dict(records=rows,paired_changes=pairs,mean_changes={k:float(np.mean([p['changes'][k] for p in pairs])) for k in pairs[0]['changes']},
        script_sha256=sha256(__file__),status='descriptive geometric changes; interventions do not isolate topology',physical_CDT=False)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(args.output)
if __name__=='__main__':main()
