#!/usr/bin/env python3
from pathlib import Path
import sys,json,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from cdt_confirmation.physical import diagnostic_screen
from cdt_confirmation.provenance import identity,stage,write_json

def produce(out):
    rng=np.random.default_rng(862341);iid=rng.normal(size=(4,4000));shifted=iid+np.arange(4)[:,None]*2
    ar=rng.normal(size=(4,4000))
    for j in range(1,4000):ar[:,j]+=.995*ar[:,j-1]
    cases=dict(iid=iid,shifted=shifted,strong_autocorrelation=ar,identical=np.tile(iid[0],(4,1)),constant=np.ones((4,4000)))
    np.savez_compressed(out/'synthetic_diagnostic_traces.npz',**cases)
    results={name:diagnostic_screen(data) for name,data in cases.items()}
    assert results['iid']['pass_screen'] and all(not results[k]['pass_screen'] for k in cases if k!='iid')
    write_json(out/'calibration.json',dict(source='SYNTHETIC_DIAGNOSTIC_CALIBRATION_NOT_CDT',cases=results,physical_CDT=False))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results/confirmation/diagnostic_calibration');args=ap.parse_args()
    p,reused=stage(args.output,identity(dict(seed=862341,chains=4,draws=4000)),produce)
    print(json.dumps(dict(path=str(p),reused=reused)))
