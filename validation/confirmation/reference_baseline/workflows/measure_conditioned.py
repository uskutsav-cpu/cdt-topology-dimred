"""Gated, budget-limited exact reference measurement on validated mapped data.

Not run on CDT data by this update: all production gates remain closed.
Labels NPZ needs boolean regular/singular masks, optional boolean start_mask,
scalar geometry_sha256, and a nonempty scalar mapping_definition. Geometry NPZ
is the existing exporter format, with integer tetrahedron neighbors (N x 4).
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT/'src'))
from research_gates import require_production_gates
from conditioned import partition_returns, decompose_dimension, _positive_int
from runtime_safety import job_lock, atomic_json
from spectral import operator


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('geometry',type=Path)
    ap.add_argument('labels',type=Path)
    ap.add_argument('--root',type=Path,default=CODE_ROOT)
    ap.add_argument('--gates',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--rho',type=float,default=.8)
    ap.add_argument('--steps',type=int,default=256)
    ap.add_argument('--block-size',type=int,default=32)
    ap.add_argument('--max-scalar-updates',type=int,default=500000000)
    args = ap.parse_args(argv)
    gate_file = args.gates or args.root/'configs/methods/production_gates.json'
    gates = require_production_gates(args.root,gate_file)  # before any numerical work
    _positive_int(args.steps,'steps',2)
    _positive_int(args.block_size,'block size')
    _positive_int(args.max_scalar_updates,'work budget')
    geometry_hash, label_hash = sha(args.geometry), sha(args.labels)
    with np.load(args.geometry,allow_pickle=False) as g:
        neighbors = g['neighbors'].copy()
    if neighbors.ndim != 2 or neighbors.shape[1] != 4 or neighbors.dtype.kind not in 'iu':
        raise ValueError('integer N x 4 microscopic tetrahedron neighbor array required')
    with np.load(args.labels,allow_pickle=False) as labels:
        if str(labels['geometry_sha256'].item()) != geometry_hash:
            raise ValueError('label artifact belongs to a different geometry')
        definition = str(labels['mapping_definition'].item()).strip()
        if not definition:
            raise ValueError('explicit mapping definition required')
        masks = {name:labels[name].copy() for name in ('regular','singular')}
        start = labels['start_mask'].copy() if 'start_mask' in labels else None
    m = operator(neighbors,args.rho)
    n_starts = m.shape[0] if start is None else int(np.count_nonzero(start))
    updates = int(m.nnz) * n_starts * args.steps
    if updates > args.max_scalar_updates:
        raise RuntimeError(f'exact reference work estimate {updates} exceeds budget {args.max_scalar_updates}; '
                           'benchmark a scalable estimator instead of launching an unbounded job')
    sources = [Path(__file__),CODE_ROOT/'src/conditioned.py',CODE_ROOT/'src/spectral/__init__.py',
               CODE_ROOT/'src/research_gates.py',CODE_ROOT/'src/runtime_safety.py']
    contract = {'geometry_sha256':geometry_hash,'labels_sha256':label_hash,'gates_sha256':sha(gate_file),
                'rho':args.rho,'steps':args.steps,'block_size':args.block_size,
                'mapping_definition':definition,'source_sha256':{str(p.relative_to(CODE_ROOT)):sha(p) for p in sources}}
    manifest = args.output.with_suffix(args.output.suffix+'.manifest.json')
    with job_lock(args.output.with_suffix(args.output.suffix+'.lock')):
        if args.output.exists() or manifest.exists():
            if not (args.output.exists() and manifest.exists()):
                raise RuntimeError('partial existing output; inspect rather than overwrite')
            old = json.loads(manifest.read_text())
            if old['contract'] != contract or old['output_sha256'] != sha(args.output):
                raise RuntimeError('existing measurement failed provenance validation')
            print(json.dumps({'status':'SKIP_VERIFIED','output':str(args.output)}))
            return
        result = partition_returns(m,masks,args.steps,block_size=args.block_size,start_mask=start)
        decomposition = decompose_dimension(result['P_class'],result['counts'])
        if decomposition['maximum_identity_error'] > 1e-10:
            raise RuntimeError('mixture identity failed')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('xb') as handle:
            np.savez_compressed(handle,names=result['names'],counts=result['counts'],
                                P_class=result['P_class'],P_all=result['P_all'],Ds_class=result['Ds_class'],
                                weights=decomposition['weights'],Ds_all=decomposition['Ds_all'])
        atomic_json(manifest,{'contract':contract,'output_sha256':sha(args.output),
                             'production_gate_evidence':gates,'estimated_scalar_updates':updates,
                             'dimension_mixture_error':decomposition['maximum_identity_error'],
                             'scope':'single-geometry measurement; no ensemble or causal conclusion'})
        print(json.dumps({'status':'MEASUREMENT_COMPLETE','output':str(args.output)}))


if __name__ == '__main__':
    main()
