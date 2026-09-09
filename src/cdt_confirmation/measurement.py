"""All-root or explicitly uniform measurements of validated saved triangulations."""
from __future__ import annotations
from pathlib import Path
import gzip, importlib.util, json, resource, sys, time
import numpy as np
from cdt_mechanisms.triangulations import (stacked_sphere,random_flips,product_cdt,necks,
    audit_cdt,write_geometry,read_geometry,geometry_digest,undo_flips)
from cdt_mechanisms.graph import from_neighbors,distances
from cdt_mechanisms.bottlenecks import local_features,fiedler_sweep,wired_annulus_separator
from cdt_mechanisms.study import geometry_controls
from cdt_mechanisms.persistence import filtration_from_facets,betti_curve
from cdt_mechanisms.evidence import jsonable,sha256
from .fields import rooted,signature,independent_betti
from .walks import propagate
from .provenance import write_json,identity,stage


def kernel_sources():
    src=Path(__file__).resolve().parents[1]
    names=['cdt_confirmation/fields.py','cdt_confirmation/walks.py',
           'cdt_confirmation/provenance.py','cdt_confirmation/measurement.py']
    names += [p.relative_to(src).as_posix() for p in sorted((src/'cdt_mechanisms').glob('*.py'))]
    return {name:sha256(src/name) for name in names}


def legacy_validate(g):
    root=Path(__file__).resolve().parents[2]
    reference=root/'tests/mechanisms/reference/geometry_7086a739.py'
    if not reference.is_file(): raise ValueError('pinned original geometry validator missing')
    import hashlib
    raw=reference.read_bytes();blob=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    if blob!='c4205be18d7cb71b6ae722436319e966f6a117b5':raise ValueError('original validator hash mismatch')
    spec=importlib.util.spec_from_file_location('_cdt_original_geometry',reference)
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    return dict(blob_sha=blob,report=mod.validate(g))


def neck_features(faces):
    report=necks(faces);small=np.asarray([x['smaller_side'] for x in report['necks']],dtype=float)
    total=float(small.sum());q=small/total if total else np.asarray([])
    return dict(neck_count=len(small),mean_separated_vertices=float(small.mean()) if len(small) else 0.,
        largest_separated_vertices=float(small.max()) if len(small) else 0.,
        summed_separated_vertices=total,branch_size_entropy=float(-np.sum(q*np.log(q))) if len(q) else 0.,
        separated_vertex_sizes=small,definition='spatial non-facial separating triangles; regions can overlap')


def _gzip_json(path,data):
    with Path(path).open('xb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:
            f.write(json.dumps(jsonable(data),sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def measure(g,out,design,*,seed,faces=None):
    start=time.perf_counter();out=Path(out);audit=audit_cdt(g);legacy=legacy_validate(g)
    a=from_neighbors(g.neighbors);n=len(g.tetra);rng=np.random.default_rng(seed+970_001)
    count=design['roots'];roots=np.arange(n) if count=='all' else np.sort(rng.choice(n,min(int(count),n),replace=False))
    # Field-validation roots are an independent uniform subset, never the smallest labels.
    nfield=min(design['field_roots'],len(roots));field_roots=set(map(int,rng.choice(roots,nfield,replace=False)))
    data=propagate(a,roots,design['max_steps'],moving_probability=design['moving_probability'])
    np.savez_compressed(out/'diffusion.npz',**{k:v for k,v in data.items() if isinstance(v,np.ndarray)})
    controls=geometry_controls(g,a,roots,design['radii']);ff=local_features(a,roots,design['radii'])
    by={(f['root'],f['radius']):f for f in ff};dall=distances(a,roots)
    rows=[];bars=[];field_checks=[];independent_checks=[]
    for i,(root,d) in enumerate(zip(roots,dall)):
        chars=design['fields'] if int(root) in field_roots else [2]
        top=rooted(g.tetra,d,design['horizon'],fields=chars)
        row=dict(root=int(root),**top['fields'][2]['features'],topology_ball_volume=top['volume'],
                 whole_geometry=top['whole_geometry'],curvature_proxy=float(controls['root_equilateral_deficit'][i]),
                 time_slice=int(controls['lower_time'][i]),tetra_type=int(controls['lower_vertex_count'][i]))
        for radius in design['radii']:
            local=by[(int(root),radius)]
            for key in ['conductance','one_step_escape','ball_vertices','shell_vertices',
                        'annular_components','spanning_annular_branches','graph_cycle_fraction']:
                row[f'{key}_r{radius}']=local[key]
        row['betti']=top['fields'][2]['betti']
        for sigma in design['sigmas']:
            row[f'Ds_{sigma}']=float(data['ds'][i,sigma]);row[f'pre_mix_{sigma}']=bool(data['pre_mix'][i,sigma])
            row[f'return_{sigma}']=float(data['returns'][i,sigma]);row[f'rms_{sigma}']=float(np.sqrt(data['msd'][i,sigma]))
        rows.append(row)
        bars.append(dict(root=int(root),fields={str(p):signature(rec['bars']) for p,rec in top['fields'].items()}))
        if len(chars)>1:
            for p in chars:
                if p!=2:field_checks.append(dict(root=int(root),field=p,same_barcode_as_F2=signature(top['fields'][2]['bars'])==signature(top['fields'][p]['bars'])))
            if not independent_checks:
                # Small independent rank calculation on a nested ball (no pairing reuse).
                radius=3;mask=d<=radius;f=filtration_from_facets(g.tetra[mask],d[mask])
                for p in chars:
                    b=independent_betti(f,radius,p)
                    actual=betti_curve(top['fields'][p]['bars'],[radius])[0].tolist()
                    if b!=actual:raise ArithmeticError('independent boundary rank disagreement')
                    independent_checks.append(dict(root=int(root),radius=radius,field=p,betti=b))
    cuts=[]
    # Exact wired-cut validation is intentionally a uniformly sampled secondary subset.
    for root in sorted(rng.choice(sorted(field_roots),min(4,len(field_roots)),replace=False)):
        try:cuts.append(wired_annulus_separator(a,int(root),1,4))
        except ValueError:cuts.append(dict(root=int(root),undefined=True))
    _gzip_json(out/'positive_barcodes.json.gz',bars);write_json(out/'root_measurements.json',rows)
    write_geometry(g,out/'geometry.dat')
    aggregates={}
    numeric=[key for key in rows[0] if key not in ['root','betti','time_slice','tetra_type']]
    for key in numeric:
        values=np.asarray([float(row[key]) if row[key] is not None else np.nan for row in rows])
        finite=np.isfinite(values);aggregates[key]=float(values[finite].mean()) if finite.any() else None
    np.savez_compressed(out/'betti_curves.npz',roots=roots,scales=np.arange(design['horizon']+1),betti=np.asarray([r['betti'] for r in rows]))
    summary=dict(seed=seed,source_kind='constructed_non_Boltzmann' if faces is not None else 'saved_geometry',
        audit=audit,legacy_validation=legacy,geometry_digest=geometry_digest(g),n_roots=len(roots),root_census=len(roots)==n,
        primary_horizon=design['horizon'],field_roots=sorted(field_roots),field_checks=field_checks,independent_rank_checks=independent_checks,
        aggregates=aggregates,full_ds={str(s):float(data['full_ds'][s]) for s in design['sigmas']},
        full_return={str(s):float(data['full_return'][s]) for s in design['sigmas']},
        mean_pre_mix={str(s):float(data['pre_mix'][:,s].mean()) for s in design['sigmas']},
        fiedler=fiedler_sweep(a),wired_cuts=cuts,necks=neck_features(faces) if faces is not None else None,
        mass_error=data['mass_error'],moving_probability=data['moving_probability'],
        runtime_seconds=time.perf_counter()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        production_gates_changed=False)
    write_json(out/'summary.json',summary)


def construct_job(payload):
    design,seed,output,sources=payload
    config=dict(design=design,seed=seed,kind='constructed_non_Boltzmann')
    ident=identity(config,sources=sources)
    def producer(path):
        initial=stacked_sphere(design['spatial_vertices'],seed=seed)
        faces,ledger=random_flips(initial,design['flips'],seed=seed+10_000)
        if undo_flips(faces,ledger)!=initial:raise ArithmeticError('reversal failed')
        g=product_cdt(faces,design['time_slices'])
        measure(g,path,design,seed=seed,faces=faces)
        write_json(path/'surgery.json',dict(seed=seed,ledger=ledger,exact_combinatorial_reversal=True,
            note='valid spatial flips then product reconstruction; not sampled 3D CDT Monte Carlo moves'))
    path,reused=stage(output,ident,producer)
    return dict(seed=seed,path=str(path),reused=reused)
