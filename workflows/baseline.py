#!/usr/bin/env python3
"""Native CDT baseline CLI. Run --help; no branch/gate is modified."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

def main():
    import multiprocessing as mp
    if mp.get_start_method(allow_none=True) is None:mp.set_start_method('spawn')
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['plan','status','extend','build','simulate','measure','analyze','verify','all'])
    ap.add_argument('--config',type=Path,default=ROOT/'configs/baseline/native_pilot.json')
    ap.add_argument('--output',type=Path,default=ROOT/'results/baseline/native_pilot')
    ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--capacity',type=int,default=200000)
    ap.add_argument('--timeout-seconds',type=float,default=1800)
    ap.add_argument('--samples',type=int,help='new total snapshots per chain for explicit extension')
    args=ap.parse_args()
    from cdt_baseline.io import load_json
    from cdt_baseline.design import validate_design
    if args.action=='status':
        from cdt_baseline.operations import status
        print(json.dumps(status(args.output),indent=2));return 0
    if args.action=='extend':
        from cdt_baseline.operations import extension_design
        cfg=extension_design(args.output,args.samples);args.action='all'
    else:cfg=validate_design(load_json(args.config))
    result={}
    if args.action=='plan':
        from cdt_baseline.operations import budget
        print(json.dumps(budget(cfg),indent=2));return 0
    if args.action=='build':
        from cdt_baseline.native import build_native
        m=build_native(ROOT,capacity=args.capacity)
        print(json.dumps({k:m[k] for k in ('build_id','binary','binary_sha256','patches')}));return 0
    if args.action in ('simulate','all'):
        from cdt_baseline.pipeline import simulate
        result['simulation']=simulate(ROOT,cfg,args.output,workers=args.workers,capacity=args.capacity,timeout_seconds=args.timeout_seconds)
        print(json.dumps(result['simulation']),flush=True)
        if result['simulation']['status']!='NATIVE_RUNS_COMPLETE':return 75
    if args.action in ('measure','all'):
        from cdt_baseline.measure import measure_study
        result['measurement']=measure_study(ROOT,cfg,args.output,workers=args.workers)
        print(json.dumps(result['measurement']),flush=True)
    if args.action in ('analyze','all'):
        from cdt_baseline.analysis import analyze_study
        result['analysis']=analyze_study(ROOT,cfg,args.output)
        print(json.dumps(result['analysis']['decision']),flush=True)
    if args.action in ('verify','all'):
        from cdt_baseline.verify import verify_study
        print(json.dumps(verify_study(ROOT,args.output)),flush=True)
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:raise SystemExit(130)
