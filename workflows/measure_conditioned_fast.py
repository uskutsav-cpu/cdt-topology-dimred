"""Gated stochastic conditioned measurement with immutable probe-level evidence.

No production runs are authorized by synthetic tests. Mapping NPZ must be
independently approved and carry scalar validation_status='VALIDATED'.
No flag in this command bypasses the four existing research gates.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import platform
import sys
import numpy as np
import scipy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from conditioned_stochastic import estimate_conditioned
from evidence_io import sha256,atomic_npz,source_hashes
from research_gates import require_production_gates
from runtime_safety import atomic_json,job_lock
from spectral import operator,dimension


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('geometry',type=Path);ap.add_argument('labels',type=Path)
    ap.add_argument('--root',type=Path,default=ROOT);ap.add_argument('--gates',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--steps',type=int,default=256);ap.add_argument('--probes',type=int,default=512)
    ap.add_argument('--batch-size',type=int,default=16);ap.add_argument('--seed',type=int,default=0)
    ap.add_argument('--rho',type=float,default=.8)
    ap.add_argument('--method',choices=['half_power','hutchinson'],default='half_power')
    ap.add_argument('--max-bytes',type=int,default=512*1024**2)
    ap.add_argument('--max-scalar-updates',type=int,default=5_000_000_000)
    args=ap.parse_args(argv)
    gate_file=args.gates or args.root/'configs/methods/production_gates.json'
    gates=require_production_gates(args.root,gate_file)  # intentionally first
    gh,lh=sha256(args.geometry),sha256(args.labels)
    with np.load(args.geometry,allow_pickle=False) as data:neighbors=data['neighbors'].copy()
    if neighbors.ndim!=2 or neighbors.shape[1]!=4 or neighbors.dtype.kind not in 'iu':
        raise ValueError('integer N x 4 tetrahedron-neighbor array required')
    with np.load(args.labels,allow_pickle=False) as labels:
        if str(labels['geometry_sha256'].item())!=gh:
            raise ValueError('labels belong to a different geometry')
        if ('validation_status' not in labels or str(labels['validation_status'].item())!='VALIDATED'):
            raise ValueError('independently VALIDATED mapping artifact required; experimental mapping rejected')
        definition=str(labels['mapping_definition'].item()).strip()
        if not definition:raise ValueError('mapping definition required')
        if definition.startswith('EXPERIMENTAL'):
            raise ValueError('experimental mapping cannot be promoted by relabeling its status')
        masks={n:labels[n].copy() for n in ('regular','singular')}
        start=labels['start_mask'].copy() if 'start_mask' in labels else None
    paths=[Path(__file__),*[ROOT/'src'/n for n in ('conditioned_stochastic.py','conditioned.py',
            'spectral/__init__.py','research_gates.py','runtime_safety.py','evidence_io.py')]]
    contract={'geometry_sha256':gh,'labels_sha256':lh,'gates_sha256':sha256(gate_file),
              'mapping_definition':definition,'steps':args.steps,'probes':args.probes,'seed':args.seed,
              'rho':args.rho,'method':args.method,'sources':source_hashes(ROOT,paths),
              'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__}
    manifest=args.output.with_suffix(args.output.suffix+'.manifest.json')
    with job_lock(args.output.with_suffix(args.output.suffix+'.lock')):
        if args.output.exists() or manifest.exists():
            if not args.output.is_file() or not manifest.is_file():
                raise RuntimeError('partial result exists; inspect instead of overwriting')
            old=json.loads(manifest.read_text())
            if old['contract']!=contract or old['output_sha256']!=sha256(args.output):
                raise RuntimeError('cached measurement failed provenance validation')
            print(json.dumps({'status':'SKIP_VERIFIED','output':str(args.output)}));return
        M=operator(neighbors,args.rho)
        estimate=estimate_conditioned(M,masks,args.steps,probes=args.probes,seed=args.seed,
            batch_size=args.batch_size,start_mask=start,method=args.method,
            max_bytes=args.max_bytes,max_scalar_updates=args.max_scalar_updates)
        atomic_npz(args.output,names=estimate.names,counts=estimate.counts,
            probe_returns=estimate.samples,P_class=estimate.mean,P_standard_error=estimate.standard_error,
            P_all=estimate.overall_samples.mean(axis=0),Ds_class=dimension(estimate.mean))
        summary=estimate.summary()
        atomic_json(manifest,{'contract':contract,'output_sha256':sha256(args.output),
            'execution_settings':{'batch_size':args.batch_size,'max_bytes':args.max_bytes,
                                  'max_scalar_updates':args.max_scalar_updates},
            'production_gate_evidence':gates,'measurement':summary,
            'scope':'single-geometry stochastic measurement, not a final ensemble result'})
        print(json.dumps({'status':'STOCHASTIC_MEASUREMENT_COMPLETE','output':str(args.output),
                          'nonpositive_mean_returns':summary['nonpositive_mean_returns']}))


if __name__=='__main__':main()
