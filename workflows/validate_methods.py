"""Execute reproducible synthetic validations, not CDT ensemble measurements."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np
import scipy
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from topology.synthetic import sphere, ball, torus, pinched_spheres
from coarsegrain.voronoi import poisson_seeds, voronoi, validate_partition
from coarsegrain.dual2d import coarsegrain_surface
from coarsegrain.dual3d import coarsegrain_manifold3d
from conditioned import partition_returns, decompose_dimension
from spectral import operator, exact_returns
from uncertainty import paired_block_effect
from runtime_safety import atomic_json, job_lock


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def padded(values, size):
    return tuple(values) + (0,) * (size - len(values))


def run_validation(seed):
    report = {'scope': 'SYNTHETIC_METHOD_VALIDATION_ONLY',
              'primary_physics_result': 'NOT_COMPUTED',
              'production_gates_advanced': False,
              'canonical_integral_stratification': 'NOT_IMPLEMENTED',
              'fixtures': [], 'coarse_2d': [], 'coarse_3d_experimental': []}
    fixtures = [('S2', sphere(2), (1,0,1)), ('S3', sphere(3), (1,0,0,1)),
                ('B3', ball(), (1,0,0,0)), ('T2', torus(2,4), (1,2,1)),
                ('T3', torus(3,3), (1,3,3,1)), ('pinched_S3', pinched_spheres(), (1,0,0,2))]
    for name, k, expected in fixtures:
        for p in (2,11):
            if k.betti(p) != expected or not k.check_boundary_squared(p):
                raise RuntimeError(f'global homology validation failed: {name}, F{p}')
            for s in k.simplices:
                if k.local_betti(s,p) != k.local_betti_via_link(s,p):
                    raise RuntimeError(f'local homology formulas disagree: {name}, {s}')
        report['fixtures'].append({'name':name, 'simplices':len(k.simplices),
                                   'betti_F2':list(k.betti(2)), 'betti_F11':list(k.betti(11)),
                                   'local_betti_at_vertex_0_F2':list(k.local_betti((0,)))})
    for dimension, deltas in [(2,range(1,5)),(3,range(1,3))]:
        k = torus(dimension, 5 if dimension == 2 else 3)
        g = k.adjacency()
        for delta in deltas:
            for replica in range(4):
                rng_seed = seed + 100 * dimension + 10 * delta + replica
                seeds = poisson_seeds(g,delta,rng_seed)
                partition = voronoi(g,seeds,rng_seed + 1)
                validation = validate_partition(g,partition,delta)
                if dimension == 2:
                    dual, provenance = coarsegrain_surface(k,partition.labels)
                else:
                    dual, provenance = coarsegrain_manifold3d(k,partition.labels)
                sub = dual.subdivision()
                for p in (2,11):
                    if dual.betti(p) != padded(sub.betti(p),dimension + 1):
                        raise RuntimeError('incidence and subdivision homology disagree')
                    if delta == 1 and dual.betti(p) != k.betti(p):
                        raise RuntimeError('identity-scale homology failed')
                entry = {'delta':delta, 'replica':replica, 'seed':rng_seed,
                         'betti_F2':list(dual.betti(2)), 'betti_F11':list(dual.betti(11)),
                         'partition':validation,
                         'provenance_sha256':hashlib.sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()}
                if dimension == 2:
                    entry['parallel_edge_excess'] = provenance['parallel_edge_excess']
                    report['coarse_2d'].append(entry)
                else:
                    entry['nonacyclic_interface_components_F2'] = sum(
                        any(b > 0 for b in betti[1:]) for betti in provenance['interface_betti_F2'])
                    entry['method_status'] = provenance['method_status']
                    report['coarse_3d_experimental'].append(entry)
    neighbors = np.array([[(i-1)%13,(i+1)%13] for i in range(13)])
    m = operator(neighbors)
    mask = np.arange(13) < 4
    measured = partition_returns(m,{'A':mask,'B':~mask},40,block_size=3)
    full = exact_returns(m,40).mean(axis=0)
    err = float(np.max(np.abs(measured['P_all'] - full)))
    decomp = decompose_dimension(measured['P_class'],measured['counts'])
    if err > 1e-12 or decomp['maximum_identity_error'] > 1e-12:
        raise RuntimeError('conditional diffusion identities failed')
    report['diffusion'] = {'all_site_mixture_error':err,
                           'dimension_mixture_error':decomp['maximum_identity_error'],
                           'operator_unchanged':measured['operator_unchanged']}
    curves = np.array([np.exp(-.35*np.arange(30)),np.exp(-.01*np.arange(30))])
    weights = decompose_dimension(curves,[99,1])
    report['synthetic_return_weight_example'] = {'minority_size_fraction':.01,
        'minority_return_weight_at_sigma20':float(weights['weights'][1,20]),
        'identity_error':weights['maximum_identity_error']}
    rng = np.random.default_rng(seed)
    chains = []
    for _ in range(2):
        p = np.exp(-rng.uniform(.02,.15,(48,1,1))*np.arange(24))
        chains.append(np.repeat(p,2,axis=1))
    null = paired_block_effect(chains,[5,6,7,8],block_length=6,replicates=100,seed=seed)
    if not np.all(null['bootstrap_A'] == 0):
        raise RuntimeError('paired bootstrap zero-effect fixture failed')
    report['paired_bootstrap_null'] = {'A':null['A'],'A_CI95':null['A_CI95'].tolist(),
                                      'replicates':100,'block_length_configurations':6}
    report['status'] = 'SYNTHETIC_CHECKS_PASS_NOT_REPRODUCTION_PASS'
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seed',type=int,default=20260908)
    ap.add_argument('--output-dir',type=Path,default=ROOT/'results/methods')
    args = ap.parse_args()
    sources = sorted([* (ROOT/'src/topology').glob('*.py'), * (ROOT/'src/coarsegrain').glob('*.py'),
                      ROOT/'src/conditioned.py',ROOT/'src/uncertainty.py',ROOT/'src/runtime_safety.py',
                      ROOT/'src/spectral/__init__.py',Path(__file__)])
    contract = {'seed':args.seed, 'python':platform.python_version(), 'numpy':np.__version__,
                'scipy':scipy.__version__, 'sources':{str(p.relative_to(ROOT)):digest(p) for p in sources}}
    job = hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()[:16]
    target = args.output_dir/f'validation_{job}.json'
    manifest = args.output_dir/f'validation_{job}.manifest.json'
    with job_lock(args.output_dir/f'{job}.lock'):
        if target.exists() or manifest.exists():
            if not (target.exists() and manifest.exists()):
                raise RuntimeError('partial validation output exists; inspect rather than overwrite')
            previous = json.loads(manifest.read_text())
            if previous.get('contract') != contract or previous.get('output_sha256') != digest(target):
                raise RuntimeError('existing validation output failed provenance verification')
            print(json.dumps({'status':'SKIP_VERIFIED','report':str(target)}))
            return
        start = time.perf_counter()
        report = run_validation(args.seed)
        report['elapsed_seconds'] = time.perf_counter() - start
        report['contract'] = contract
        atomic_json(target,report)
        atomic_json(manifest,{'contract':contract,'output_sha256':digest(target)})
        print(json.dumps({'status':report['status'],'report':str(target),'sha256':digest(target)}))


if __name__ == '__main__':
    main()
