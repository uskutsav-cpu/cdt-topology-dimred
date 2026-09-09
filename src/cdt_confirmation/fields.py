"""Oriented persistence over prime fields, independently reduced from the F2 backend."""
from __future__ import annotations
import math
import numpy as np
from cdt_mechanisms.persistence import (Interval, validate_filtration, filtration_from_facets,
                                      persistent_homology, betti_curve)


def prime(p):
    if isinstance(p, (bool,np.bool_)) or not isinstance(p,(int,np.integer)):
        raise ValueError('integer prime required')
    p=int(p)
    if p<2 or p>65521 or any(p%d==0 for d in range(2,math.isqrt(p)+1)):
        raise ValueError('field characteristic must be prime <=65521')
    return p


def persistence_prime(filtration, p=3, *, budget=200_000):
    p=prime(p); f=validate_filtration(filtration)
    if len(f)>budget or any(len(s)>4 for s in f):
        raise ValueError('dimension or simplex budget exceeded')
    ss=sorted(f,key=lambda s:(f[s],len(s),s)); ix={s:i for i,s in enumerate(ss)}
    reduced={}; births=set(); killed=set(); bars=[]
    for j,s in enumerate(ss):
        col={} if len(s)==1 else {ix[s[:i]+s[i+1:]]:(1 if i%2==0 else p-1) for i in range(len(s))}
        while col:
            lead=max(col)
            if lead not in reduced: break
            factor=col[lead]
            for row,value in reduced[lead].items():
                new=(col.get(row,0)-factor*value)%p
                if new: col[row]=new
                else: col.pop(row,None)
        if not col:
            births.add(j); continue
        lead=max(col)
        if lead not in births: raise ArithmeticError('invalid chain-complex pairing')
        inv=pow(col[lead],-1,p)
        reduced[lead]={r:v*inv%p for r,v in col.items()}
        killed.add(lead); b=ss[lead]
        bars.append(Interval(len(b)-1,f[b],f[s],b,s))
    for j in sorted(births-killed):
        s=ss[j]; bars.append(Interval(len(s)-1,f[s],math.inf,s,None))
    return sorted(bars,key=lambda b:(b.dimension,b.birth,b.death,b.birth_simplex))


def signature(bars):
    return sorted((b.dimension,float(b.birth),float(b.death)) for b in bars if b.death>b.birth)


def rank_prime(matrix,p):
    p=prime(p); raw=np.asarray(matrix)
    if raw.ndim!=2 or raw.dtype.kind not in 'iu': raise ValueError('integer matrix required')
    a=(raw%p).astype(np.int64); rank=0
    for col in range(a.shape[1]):
        nz=np.flatnonzero(a[rank:,col])
        if not len(nz): continue
        j=rank+int(nz[0]); a[[rank,j]]=a[[j,rank]]
        a[rank]=a[rank]*pow(int(a[rank,col]),-1,p)%p
        for i in range(rank+1,a.shape[0]):
            if a[i,col]: a[i]=(a[i]-a[i,col]*a[rank])%p
        rank+=1
        if rank==a.shape[0]: break
    return rank


def independent_betti(filtration,scale,p,*,max_entries=8_000_000):
    p=prime(p); f=validate_filtration(filtration)
    by={d:sorted(s for s,v in f.items() if len(s)==d+1 and v<=scale) for d in range(4)}
    ranks=[0]
    for dim in range(1,4):
        rows={s:i for i,s in enumerate(by[dim-1])}; shape=(len(rows),len(by[dim]))
        if shape[0]*shape[1]>max_entries: raise ValueError('dense reference rank budget exceeded')
        a=np.zeros(shape,dtype=np.int64)
        for j,s in enumerate(by[dim]):
            for k in range(len(s)): a[rows[s[:k]+s[k+1:]],j]=(-1)**k
        ranks.append(rank_prime(a,p))
    ranks.append(0)
    return [len(by[d])-ranks[d]-ranks[d+1] for d in range(4)]


def features(bars,horizon,volume):
    if horizon<0 or volume<1: raise ValueError('invalid horizon/volume')
    positive=[b for b in bars if b.dimension==1 and b.death>b.birth]
    finite=[b for b in positive if math.isfinite(b.death)]
    life=np.asarray([b.death-b.birth for b in finite]); total=float(life.sum())
    probs=life/total if total else np.asarray([])
    return dict(H1_finite_count=len(finite),H1_censored_count=len(positive)-len(finite),
        H1_finite_total_persistence=total,H1_finite_max_lifetime=float(life.max()) if len(life) else 0.,
        H1_finite_mean_lifetime=float(life.mean()) if len(life) else None,
        H1_finite_median_lifetime=float(np.median(life)) if len(life) else None,
        H1_mean_birth=float(np.mean([b.birth for b in finite])) if finite else None,
        H1_mean_death=float(np.mean([b.death for b in finite])) if finite else None,
        H1_persistence_entropy=float(-np.sum(probs*np.log(probs))) if len(probs) else 0.,
        H1_observed_persistence=float(sum(max(0.,min(horizon,b.death)-b.birth) for b in positive)),
        H1_total_per_tetrahedron=total/volume)


def rooted(tetra,distance,horizon,*,fields=(2,),budget=200_000):
    cells=np.asarray(tetra); d=np.asarray(distance,dtype=float)
    if cells.ndim!=2 or cells.shape[1]!=4 or cells.dtype.kind not in 'iu': raise ValueError('integer tetrahedra required')
    if d.shape!=(len(cells),) or not np.isfinite(d).all() or np.any(d<0): raise ValueError('invalid distances')
    if isinstance(horizon,bool) or not isinstance(horizon,int) or horizon<0: raise ValueError('invalid horizon')
    chars=tuple(prime(p) for p in fields)
    if not chars or len(set(chars))!=len(chars): raise ValueError('distinct fields required')
    selected=d<=horizon; f=filtration_from_facets(cells[selected],d[selected],budget=budget); out={}
    for p in chars:
        bars=persistent_homology(f,budget=budget) if p==2 else persistence_prime(f,p,budget=budget)
        out[p]=dict(bars=bars,features=features(bars,horizon,int(selected.sum())),
                    betti=betti_curve(bars,np.arange(horizon+1)))
    return dict(fields=out,simplex_count=len(f),volume=int(selected.sum()),whole_geometry=bool(selected.all()))
