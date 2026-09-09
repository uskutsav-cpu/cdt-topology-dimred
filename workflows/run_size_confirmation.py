#!/usr/bin/env python3
from pathlib import Path
import argparse,concurrent.futures,json,os,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(k,'1')
import numpy as np
from cdt_confirmation.measurement import construct_job,kernel_sources
from cdt_confirmation.provenance import stage,identity,write_json,verify
from cdt_confirmation.statistics import correlation_test
from cdt_mechanisms.evidence import sha256


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--output',type=Path,default=ROOT/'results/confirmation/finite_size')
    args=ap.parse_args();cfg=json.loads((ROOT/'configs/confirmation/finite_size.json').read_text());sources=kernel_sources()
    if not 1<=args.workers<=4:raise ValueError('workers 1..4 required')
    args.output.mkdir(parents=True,exist_ok=True);jobs=[];labels=[]
    for size in cfg['spatial_vertices']:
        design={**cfg,'spatial_vertices':size,'flips':size*cfg['flips_per_spatial_vertex']}
        for seed in cfg['seeds']:
            jobs.append((design,seed,str(args.output/'measurements'),sources));labels.append(size)
    start=time.perf_counter();records=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for size,rec in zip(labels,pool.map(construct_job,jobs)):
            rec.update(spatial_vertices=size);rec['path']=str(Path(rec['path']).relative_to(args.output))
            records.append(rec);print(json.dumps(rec),flush=True)
    summaries=[]
    for size in cfg['spatial_vertices']:
        rows=[json.loads((args.output/r['path']/'summary.json').read_text()) for r in records if r['spatial_vertices']==size]
        test=correlation_test([r['aggregates']['H1_finite_total_persistence'] for r in rows],[r['full_ds']['32'] for r in rows],
                              permutations=1999,bootstraps=1999,seed=81345+size);test.pop('null_distribution')
        summaries.append(dict(spatial_vertices=size,tetrahedra=rows[0]['audit']['N3'],n_seeds=len(rows),
            H1_vs_Ds32=test,mean_H1=float(np.mean([r['aggregates']['H1_finite_total_persistence'] for r in rows])),
            mean_Ds32=float(np.mean([r['full_ds']['32'] for r in rows])),
            minimum_pre_mix_fraction=min(r['mean_pre_mix']['32'] for r in rows),
            mean_fraction_whole_geometry_balls=float(np.mean([r['aggregates']['whole_geometry'] for r in rows])),
            finite_field_comparisons=sum(len(r['field_checks']) for r in rows),
            finite_field_disagreements=sum(not c['same_barcode_as_F2'] for r in rows for c in r['field_checks'])))
    report=dict(config=cfg,records=records,sizes=summaries,wall_seconds=time.perf_counter()-start,workers=args.workers,
                total_roots=sum(r['spatial_vertices']*24-48 for r in records),physical_CDT=False,
                inference='secondary per-size descriptive tests, not three independent confirmations; seeds paired across sizes')
    inp={r['path']:sha256(args.output/r['path']/'manifest.json') for r in records}
    target,_=stage(args.output/'analysis',identity(dict(stage='finite-size sensitivity',config=cfg),inputs=inp),lambda p:write_json(p/'summary.json',report))
    print(json.dumps(dict(summary=str(target/'summary.json'))),flush=True)
if __name__=='__main__':main()
