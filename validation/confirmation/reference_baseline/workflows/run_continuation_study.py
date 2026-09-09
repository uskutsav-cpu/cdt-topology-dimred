"""Run the synthetic continuation study; NEVER issue a quantum-gravity result.

Executes integer topology, two stratification backends, experimental 3D carrier
mapping, exact/stochastic diffusion controls, a runtime/precision benchmark, and
hierarchical uncertainty. All outputs are source-hashed and immutable. This does
not start the C++ simulator or the user's remote/local chains.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import platform
import sys
import time
import numpy as np
import scipy
import sympy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from topology import SimplicialComplex
from topology.synthetic import sphere,ball,torus,pinched_spheres
from topology.integral import integral_homology,IntegralLocalSystem,local_homology_via_link
from topology.stratification import canonical_stratification
from coarsegrain.voronoi import poisson_seeds,voronoi,validate_partition
from coarsegrain.dual3d import coarsegrain_manifold3d
from coarsegrain.microscopic import map_incidence_carriers
from conditioned import partition_returns,decompose_dimension
from conditioned_stochastic import estimate_conditioned,probe_effect
from hierarchical_uncertainty import hierarchical_block_effect
from spectral import operator,dimension
from evidence_io import sha256,atomic_npz,source_hashes,verify_bundle
from runtime_safety import atomic_json,job_lock


def projective_plane():
    return SimplicialComplex([(0,1,2),(0,1,3),(0,2,4),(0,3,5),(0,4,5),
                             (1,2,5),(1,3,4),(1,4,5),(2,3,4),(2,3,5)])


def grid_neighbors(side):
    return np.array([[(x-1)%side+side*y,(x+1)%side+side*y,
                      x+side*((y-1)%side),x+side*((y+1)%side)]
                     for y in range(side) for x in range(side)],dtype=np.int64)


def bottleneck_neighbors(side=12):
    large=grid_neighbors(side)+5
    adjacency=[set(j for j in range(5) if j!=i) for i in range(5)]
    adjacency.extend(map(set,large.tolist()))
    for a,b in ((0,1),(5,6)):
        adjacency[a].remove(b);adjacency[b].remove(a)
    for a,b in ((0,5),(1,6)):
        adjacency[a].add(b);adjacency[b].add(a)
    return np.array([sorted(s) for s in adjacency],dtype=np.int64)


def _save_arrays(directory,name,**values):
    path=directory/name;atomic_npz(path,**values);return name


def _measure(directory,name,neighbors,regular,steps,probes,seed):
    M=operator(neighbors);masks={'regular':regular,'singular':~regular}
    start=time.perf_counter()
    exact=partition_returns(M,masks,steps,block_size=16)
    exact_seconds=time.perf_counter()-start
    start=time.perf_counter()
    estimated=estimate_conditioned(M,masks,steps,probes=probes,seed=seed,batch_size=16)
    estimator_seconds=time.perf_counter()-start
    d=decompose_dimension(exact['P_class'],exact['counts'])
    if d['maximum_identity_error']>1e-10:
        raise ArithmeticError('exact return/dimension mixture identity failed')
    window=np.arange(3,min(13,steps))
    delta=exact['Ds_class'][0]-exact['Ds_class'][1]
    se=estimated.standard_error
    absolute=np.abs(estimated.mean-exact['P_class'])
    standardized=float(np.max(absolute[:,1:]/(se[:,1:]+1e-12)))
    if standardized>10:
        raise ArithmeticError('stochastic oracle comparison exceeds ten empirical standard errors')
    path=_save_arrays(directory,name,neighbors=neighbors,regular=regular,singular=~regular,
        P_exact=exact['P_class'],P_estimate=estimated.mean,P_standard_error=se,
        probe_returns=estimated.samples,Ds_exact=exact['Ds_class'],counts=exact['counts'],
        P_all_exact=exact['P_all'],weights_exact=d['weights'])
    return {'artifact':path,'sites':len(neighbors),'counts':exact['counts'].tolist(),
            'synthetic_window':window.tolist(),'A_exact':float(delta[window].mean()),
            'probe_effect':probe_effect(estimated,window,replicates=200,seed=seed+1),
            'exact_seconds':exact_seconds,'estimator_seconds':estimator_seconds,
            'observed_speed_ratio_exact_over_estimator':exact_seconds/estimator_seconds,
            'exact_operator_applications':len(neighbors)*steps,
            'stochastic_operator_applications':estimated.operator_applications,
            'operator_application_reduction_factor':len(neighbors)*steps/estimated.operator_applications,
            'maximum_absolute_return_error':float(absolute.max()),
            'maximum_relative_return_error_in_window':float(np.max(absolute[:,window]/exact['P_class'][:,window])),
            'maximum_relative_standard_error_in_window':float(np.max(se[:,window]/np.maximum(estimated.mean[:,window],1e-14))),
            'maximum_standardized_return_error':standardized,
            'dimension_mixture_error':d['maximum_identity_error'],
            'estimator':estimated.summary(),'scope':'SYNTHETIC_GRAPH_ONLY'}


def run_study(directory,params):
    seed=params['seed'];steps=params['steps'];probes=params['probes']
    report={'status':'IN_PROGRESS','scope':'SYNTHETIC_SOFTWARE_AND_METHOD_STUDY_ONLY',
            'physics_result':'NOT_COMPUTED','production_gates_advanced':False,
            'topology':[],'random_complex_cross_checks':{},'coarse_3d':[],
            'diffusion_controls':[],'benchmark':None}
    fixtures=[('S1',sphere(1)),('S2',sphere(2)),('S3',sphere(3)),('B3',ball(3)),
              ('T2',torus(2,3)),('T3',torus(3,3)),('pinched_S3',pinched_spheres(3)),
              ('RP2',projective_plane())]
    for name,k in fixtures:
        start=time.perf_counter();groups=integral_homology(k)
        exact=canonical_stratification(k,method='integral',audit_incidence=name not in ('T2','T3'))
        fast=canonical_stratification(k)
        if exact.simplex_dimension!=fast.simplex_dimension:
            raise ArithmeticError(f'stratification backends disagree: {name}')
        local=IntegralLocalSystem(k)
        for s in k.simplices:
            if local.homology(s)!=local_homology_via_link(k,s):
                raise ArithmeticError(f'integral local/link disagreement: {name},{s}')
        report['topology'].append({'fixture':name,'simplices':len(k.simplices),
            'integral_homology':[g.as_dict() for g in groups],
            'stratum_cell_counts':dict(sorted(Counter(exact.simplex_dimension.values()).items())),
            'incidence_maps_audited':len(exact.incidence_certificates),
            'local_link_checks':len(k.simplices),'elapsed_seconds':time.perf_counter()-start})
        atomic_json(directory/f'stratification_{name}.json',exact.as_dict())
    start=time.perf_counter()
    for replicate in range(params['random_complexes']):
        rng=np.random.default_rng(seed+10000+replicate)
        cells=[s for size in range(1,5) for s in combinations(range(6),size) if rng.random()<.16]
        k=SimplicialComplex(cells)
        a=canonical_stratification(k,method='integral');b=canonical_stratification(k)
        if a.simplex_dimension!=b.simplex_dimension:
            raise ArithmeticError(f'random complex stratification mismatch at replicate {replicate}')
    report['random_complex_cross_checks']={'count':params['random_complexes'],'mismatches':0,
                                          'elapsed_seconds':time.perf_counter()-start}
    for side in params['sides']:
        fine=torus(3,side);graph=fine.adjacency()
        for delta in params['deltas']:
            # Identity-scale repeats are redundant up to region renaming.
            for realization in range(1 if delta==1 else params['realizations']):
                rng_seed=seed+side*1000+delta*100+realization
                start=time.perf_counter()
                seeds=poisson_seeds(graph,delta,rng_seed)
                partition=voronoi(graph,seeds,rng_seed+1)
                checked=validate_partition(graph,partition,delta)
                record={'side':side,'delta':delta,'realization':realization,'seed':rng_seed,
                        'partition':checked,'scope':'EXPERIMENTAL_SYNTHETIC_3D'}
                try:
                    coarse,provenance=coarsegrain_manifold3d(fine,partition.labels)
                    mapped=map_incidence_carriers(fine,partition.labels,coarse,provenance)
                except (ValueError,MemoryError) as error:
                    record.update(status='REJECTED_NO_PHYSICS_RESULT',error=str(error))
                    report['coarse_3d'].append(record)
                    continue
                name=f'carrier_T3_side{side}_delta{delta}_seed{rng_seed}'
                details={k:v for k,v in mapped.items() if not isinstance(v,np.ndarray)}
                atomic_json(directory/f'{name}.json',details)
                _save_arrays(directory,f'{name}.npz',
                    **{k:v for k,v in mapped.items() if isinstance(v,np.ndarray)},
                    validation_status='EXPERIMENTAL',mapping_definition=mapped['mapping_definition'])
                record.update(status='COMPUTED_EXPERIMENTAL',class_counts=mapped['class_counts'],
                    mapping_artifact=f'{name}.json',mapping_arrays=f'{name}.npz',
                    coarse_betti_F2=list(coarse.betti(2)),
                    interface_components_with_nonzero_higher_betti=sum(any(v>0 for v in b[1:])
                        for b in provenance['interface_betti_F2']),
                    production_eligible=False)
                if delta==1 and (not mapped['regular'].all() or coarse.betti(2)!=(1,3,3,1)):
                    raise ArithmeticError('identity-scale 3D carrier or topology test failed')
                if mapped['measurement_eligible_synthetically'] and not mapped['ambiguous'].any():
                    record['conditioned_measurement']=_measure(directory,f'{name}_returns.npz',
                        mapped['neighbors'],mapped['regular'],steps,probes,rng_seed+2)
                else:
                    record['conditioned_measurement_status']='UNDEFINED_EMPTY_OR_AMBIGUOUS_CLASS_NOT_ZERO_EFFECT'
                record['elapsed_seconds']=time.perf_counter()-start
                report['coarse_3d'].append(record)
    # A symmetry null and an intentionally inhomogeneous positive control.
    neighbors=grid_neighbors(8);regular=np.arange(len(neighbors))>=5
    null=_measure(directory,'diffusion_symmetry_null.npz',neighbors,regular,steps,probes,seed+20000)
    null['interpretation']='origin-label null on a homogeneous synthetic periodic grid'
    if abs(null['A_exact'])>1e-10:raise ArithmeticError('symmetry null has a spurious exact effect')
    report['diffusion_controls'].append(null)
    neighbors=bottleneck_neighbors(12);regular=np.arange(len(neighbors))>=5
    positive=_measure(directory,'diffusion_bottleneck_positive.npz',neighbors,regular,steps,probes,seed+20001)
    positive['interpretation']='artificial dense-clique/torus bottleneck; labels are NOT CDT topology labels'
    if positive['A_exact']<=0:raise ArithmeticError('synthetic positive control did not give its designed direction')
    report['diffusion_controls'].append(positive)
    side=params['benchmark_side'];neighbors=grid_neighbors(side);regular=np.arange(len(neighbors))%3!=0
    report['benchmark']=_measure(directory,'diffusion_benchmark.npz',neighbors,regular,steps,
                                 params['benchmark_probes'],seed+21000)
    rng=np.random.default_rng(seed+30000);chains=[]
    for length in (16,20):
        chain=[]
        for i in range(length):
            configs=[]
            for j in range(1+i%3):
                p=np.exp(-rng.uniform(.02,.12,(6+j,1,1))*np.arange(20))
                configs.append(np.repeat(p,2,axis=1))
            chain.append(configs)
        chains.append(chain)
    bootstrap=hierarchical_block_effect(chains,[3,4,5,6],block_length=4,replicates=100,seed=seed)
    if not np.all(bootstrap['bootstrap_A']==0):raise ArithmeticError('paired hierarchy broke a zero-effect identity')
    report['hierarchical_null']={'A':bootstrap['A'],'CI95':bootstrap['A_CI95'].tolist(),
        'configuration_count':bootstrap['configuration_count'],'chain_count':bootstrap['chain_count'],
        'replicates':100,'block_length_configurations':4,'scope':'synthetic paired noise only'}
    report['status']='PASS_SYNTHETIC_CONTINUATION_NOT_REPRODUCTION_PASS'
    return report


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir',type=Path,default=ROOT/'results/continuation')
    ap.add_argument('--seed',type=int,default=20260908)
    ap.add_argument('--quick',action='store_true')
    args=ap.parse_args(argv)
    if args.seed<0:raise ValueError('seed must be nonnegative')
    params={'seed':args.seed,'steps':32 if args.quick else 64,'probes':128 if args.quick else 512,
            'random_complexes':12 if args.quick else 128,'sides':[3] if args.quick else [3,4],
            'deltas':[1,2] if args.quick else [1,2,3],'realizations':1 if args.quick else 4,
            'benchmark_side':16 if args.quick else 32,'benchmark_probes':128 if args.quick else 256}
    paths=sorted((ROOT/'src').rglob('*.py'))+[Path(__file__)]
    contract={'parameters':params,'sources':source_hashes(ROOT,paths),'python':platform.python_version(),
              'numpy':np.__version__,'scipy':scipy.__version__,'sympy':sympy.__version__}
    job=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()[:16]
    directory=args.output_dir/job
    with job_lock(args.output_dir/f'{job}.lock'):
        if directory.exists():
            verify_bundle(directory,expected_contract=contract,source_root=ROOT)
            print(json.dumps({'status':'SKIP_VERIFIED','directory':str(directory)}));return
        directory.mkdir(parents=True)
        start=time.perf_counter();report=run_study(directory,params)
        report['elapsed_seconds']=time.perf_counter()-start
        report['environment']={'platform':platform.platform(),'processor':platform.processor(),
            'logical_cpus':os.cpu_count(),'thread_env':{k:os.environ.get(k) for k in
             ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')}}
        atomic_json(directory/'report.json',report)
        artifacts={str(p.relative_to(directory)):sha256(p) for p in sorted(directory.rglob('*')) if p.is_file()}
        atomic_json(directory/'manifest.json',{'contract':contract,'artifacts':artifacts})
        verify_bundle(directory,expected_contract=contract,source_root=ROOT)
        print(json.dumps({'status':report['status'],'directory':str(directory),'artifacts':len(artifacts),
                          'elapsed_seconds':report['elapsed_seconds']}))


if __name__=='__main__':main()
