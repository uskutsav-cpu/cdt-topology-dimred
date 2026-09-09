"""Exact F2 homology and genuine nested-subcomplex persistence.

This is geodesic-ball persistence of the original triangulation, NOT the
non-nested Voronoi/Delaunay effective-topology construction. Barcodes require
filtration maps; Betti curves from unrelated coarse samples are not barcodes.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from collections import defaultdict
import math
import numpy as np


@dataclass(frozen=True)
class Interval:
    dimension: int
    birth: float
    death: float                 # infinity means right-censored/essential
    birth_simplex: tuple[int,...]
    death_simplex: tuple[int,...] | None


def simplex_key(vertices) -> tuple[int,...]:
    raw=tuple(vertices)
    if not raw or any(not isinstance(v,(int,np.integer)) or isinstance(v,(bool,np.bool_)) or v<0 for v in raw):
        raise ValueError("simplices require nonnegative integer labels")
    s=tuple(sorted(map(int,raw)))
    if len(set(s))!=len(s): raise ValueError("repeated simplex vertex")
    return s


def filtration_from_facets(facets, values=None, *, budget=200_000) -> dict:
    facets=list(facets)
    if not facets: raise ValueError("empty complex")
    if values is None: values=[0.]*len(facets)
    if len(values)!=len(facets): raise ValueError("one filtration value per facet required")
    out={}
    for facet,value in zip(facets,values):
        s=simplex_key(facet); value=float(value)
        if not math.isfinite(value): raise ValueError("nonfinite filtration value")
        if len(s)>4: raise ValueError("this audited backend supports dimension <=3")
        for size in range(1,len(s)+1):
            for f in combinations(s,size):
                out[f]=min(out.get(f,float('inf')),value)
        if len(out)>budget: raise ValueError("simplex budget exceeded")
    return out


def validate_filtration(filtration) -> dict:
    f={}
    for raw,value in filtration.items():
        s=simplex_key(raw); v=float(value)
        if not math.isfinite(v): raise ValueError("nonfinite filtration value")
        if s in f: raise ValueError("duplicate simplex under canonical ordering")
        f[s]=v
    if not f: raise ValueError("empty filtration")
    for s,v in f.items():
        if len(s)>1:
            for face in combinations(s,len(s)-1):
                if face not in f or f[face]>v:
                    raise ValueError("missing face or non-monotone filtration")
    return f


def persistent_homology(filtration, *, budget=200_000) -> list[Interval]:
    f=validate_filtration(filtration)
    if len(f)>budget: raise ValueError("simplex budget exceeded")
    simplices=sorted(f,key=lambda s:(f[s],len(s),s)); index={s:i for i,s in enumerate(simplices)}
    reduced={}; births=set(); killed=set(); intervals=[]
    for j,s in enumerate(simplices):
        col=0
        if len(s)>1:
            for face in combinations(s,len(s)-1): col ^= 1<<index[face]
        while col:
            pivot=col.bit_length()-1
            if pivot not in reduced: break
            col ^= reduced[pivot]
        if not col:
            births.add(j)
        else:
            pivot=col.bit_length()-1
            if pivot not in births:
                raise ArithmeticError("boundary reduction violated chain-complex pairing")
            reduced[pivot]=col; killed.add(pivot)
            b=simplices[pivot]
            intervals.append(Interval(len(b)-1,f[b],f[s],b,s))
    for i in sorted(births-killed):
        s=simplices[i]; intervals.append(Interval(len(s)-1,f[s],float('inf'),s,None))
    return sorted(intervals,key=lambda x:(x.dimension,x.birth,x.death,x.birth_simplex))


def betti_curve(intervals, scales, *, max_dimension=3) -> np.ndarray:
    scales=np.asarray(scales,dtype=float)
    if scales.ndim!=1 or not np.isfinite(scales).all(): raise ValueError("invalid scales")
    out=np.zeros((len(scales),max_dimension+1),dtype=int)
    for bar in intervals:
        if 0<=bar.dimension<=max_dimension:
            out[:,bar.dimension]+=(bar.birth<=scales)&(scales<bar.death)
    return out


def rank_f2(columns: list[int]) -> int:
    pivots={}
    for col in columns:
        while col:
            lead=col.bit_length()-1
            if lead not in pivots:
                pivots[lead]=col; break
            col ^= pivots[lead]
    return len(pivots)


def independent_betti(facets) -> list[int]:
    """Dimension-separated boundary rank check independent of persistence pairing."""
    f=filtration_from_facets(facets); by=defaultdict(list)
    for s in f: by[len(s)-1].append(s)
    top=max(by); ranks={0:0,top+1:0}
    for dim in range(1,top+1):
        rows={s:i for i,s in enumerate(sorted(by[dim-1]))}; cols=[]
        for s in by[dim]:
            c=0
            for face in combinations(s,dim): c ^= 1<<rows[face]
            cols.append(c)
        ranks[dim]=rank_f2(cols)
    return [len(by[k])-ranks[k]-ranks[k+1] for k in range(top+1)]


def geodesic_ball_persistence(tetra, dual_distances, max_radius: int, *, budget=200_000) -> dict:
    """K_r = union of tetrahedra within dual-hop distance r, including all faces.

    Scale and ant distance use the same dual metric. Balls can have nontrivial
    boundary topology even when the ambient manifold is nonsingular.
    """
    cells=np.asarray(tetra); d=np.asarray(dual_distances,dtype=float)
    if cells.ndim!=2 or cells.shape[1]!=4 or cells.dtype.kind not in 'iu':
        raise ValueError("tetra must be an integer (N,4) array")
    if d.shape!=(len(cells),) or not np.isfinite(d).all() or np.any(d<0):
        raise ValueError("invalid dual distances")
    if not isinstance(max_radius,int) or max_radius<0: raise ValueError("invalid horizon")
    selected=d<=max_radius
    if not np.any(selected): raise ValueError("no tetrahedra in ball")
    f=filtration_from_facets(cells[selected],d[selected],budget=budget)
    bars=persistent_homology(f,budget=budget)
    scales=np.arange(max_radius+1); curve=betti_curve(bars,scales)
    summaries=[]
    for dim in range(1,4):
        positive=[b for b in bars if b.dimension==dim and b.death>b.birth]
        finite=[b for b in positive if np.isfinite(b.death)]
        censored=[b for b in positive if not np.isfinite(b.death)]
        summaries.append(dict(dimension=dim,finite_intervals=len(finite),
            censored_intervals=len(censored),
            finite_total_persistence=float(sum(b.death-b.birth for b in finite)),
            observed_persistence=float(sum(max(0,min(b.death,max_radius)-b.birth) for b in positive))))
    return dict(intervals=bars,scales=scales,betti=curve,summary=summaries,
                simplex_count=len(f),whole_geometry=bool(selected.all()),
                definition='nested union of dual-distance tetrahedral balls; F2')
