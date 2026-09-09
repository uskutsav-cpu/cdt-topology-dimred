#!/usr/bin/env python3
"""Generate immutable independent-geometry measurements; --analyze consumes saved stages."""
from pathlib import Path
import argparse, concurrent.futures, json, os, sys, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(key,'1')
from cdt_confirmation.measurement import construct_job,kernel_sources
from cdt_confirmation.provenance import write_json,lock,verify
from cdt_mechanisms.evidence import canonical
import hashlib


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--design',type=Path,default=ROOT/'configs/confirmation/independent.json')
    ap.add_argument('--output',type=Path,default=ROOT/'results/confirmation/independent')
    ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--analyze',action='store_true')
    args=ap.parse_args();cfg=json.loads(args.design.read_text())
    if args.workers<1 or args.workers>8:raise ValueError('workers must be 1..8')
    train=cfg['training_seeds'];confirm=cfg['confirmation_seeds'];seeds=train+confirm
    if len(set(seeds))!=len(seeds) or min(len(train),len(confirm))<4:raise ValueError('independent nonoverlapping splits required')
    sources=kernel_sources();args.output.mkdir(parents=True,exist_ok=True)
    protocol=dict(design=cfg,kernel_sources=sources)
    with lock(args.output/'protocol.lock'):
        pp=args.output/'protocol.json'
        if pp.exists():
            if json.loads(pp.read_text())!=protocol:raise ValueError('protocol/source changed: use a new output directory')
        else:write_json(pp,protocol)
    if args.analyze:
        from cdt_confirmation.analysis import analyze_run
        analyze_run(args.output);return
    start=time.perf_counter();jobs=[(cfg,s,str(args.output/'measurements'),sources) for s in seeds];records=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for item in pool.map(construct_job,jobs):
            item['path']=str(Path(item['path']).relative_to(args.output));records.append(item)
            print(json.dumps(item),flush=True)
    index=dict(protocol_sha256=hashlib.sha256(canonical(protocol)).hexdigest(),records=records,
        wall_seconds=time.perf_counter()-start,workers=args.workers,physical_CDT=False)
    target=args.output/'index.json'
    if not target.exists():write_json(target,index)
    else:
        old=json.loads(target.read_text())
        if [(x['seed'],x['path']) for x in old['records']]!=[(x['seed'],x['path']) for x in records]:raise ValueError('index mismatch')
        print('Verified complete stage reuse',flush=True)

if __name__=='__main__':main()
