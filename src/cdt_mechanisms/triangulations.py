"""Constructed foliated S2 x S1 triangulations and reversible valid interventions.

These are legal combinatorial CDT-type geometries, NOT samples from the CDT
Boltzmann measure. Spatial edge flips are propagated through a product
construction; they are not asserted to be individual simulator Pachner moves.
"""
from __future__ import annotations
from collections import defaultdict, Counter
from itertools import combinations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import numpy as np
import networkx as nx
from .graph import from_neighbors
from .persistence import simplex_key


def canonical_faces(faces) -> tuple:
    out=tuple(sorted(simplex_key(f) for f in faces))
    if not out or any(len(f)!=3 for f in out) or len(set(out))!=len(out):
        raise ValueError("need distinct nondegenerate triangular faces")
    return out


def sphere_audit(faces) -> dict:
    f=canonical_faces(faces); edges=defaultdict(list); verts=set(); links=defaultdict(list)
    for i,tri in enumerate(f):
        verts.update(tri)
        for e in combinations(tri,2): edges[e].append(i)
        for v in tri: links[v].append(tuple(w for w in tri if w!=v))
    if any(len(x)!=2 for x in edges.values()): raise ValueError("not a closed surface")
    primal=nx.Graph(); primal.add_nodes_from(verts); primal.add_edges_from(edges)
    if not nx.is_connected(primal): raise ValueError("disconnected surface")
    for v,es in links.items():
        g=nx.Graph(es)
        if len(es)!=g.number_of_edges() or not nx.is_connected(g) or any(d!=2 for _,d in g.degree):
            raise ValueError(f"vertex {v} link is not a circle")
    chi=len(verts)-len(edges)+len(f)
    if chi!=2: raise ValueError("closed connected surface is not a sphere")
    return dict(vertices=len(verts),edges=len(edges),faces=len(f),chi=chi,
                all_vertex_links_cycles=True)


def bipyramid(n_vertices: int) -> tuple:
    if not isinstance(n_vertices,int) or n_vertices<5: raise ValueError("need >=5 vertices")
    ring=n_vertices-2
    f=[]
    for i in range(ring):
        f.extend([(i,(i+1)%ring,ring),(i,(i+1)%ring,ring+1)])
    f=canonical_faces(f); sphere_audit(f); return f


def stacked_sphere(n_vertices: int, *, seed=0, mode='random') -> tuple:
    if not isinstance(n_vertices,int) or n_vertices<4: raise ValueError("need >=4 vertices")
    if mode not in ('random','chain','balanced'): raise ValueError("unknown stacking mode")
    faces=set(combinations(range(4),3)); depth={f:0 for f in faces}; rng=np.random.default_rng(seed)
    for v in range(4,n_vertices):
        ordered=sorted(faces)
        if mode=='random': old=ordered[int(rng.integers(len(ordered)))]
        elif mode=='chain': old=max(ordered,key=lambda f:(depth[f],f))
        else: old=min(ordered,key=lambda f:(depth[f],f))
        lev=depth.pop(old); faces.remove(old)
        for e in combinations(old,2):
            new=tuple(sorted((*e,v))); faces.add(new); depth[new]=lev+1
    result=canonical_faces(faces); sphere_audit(result); return result


def spatial_edges(faces) -> dict:
    es=defaultdict(list)
    for f in faces:
        for e in combinations(f,2): es[e].append(f)
    return dict(es)


def flippable_edges(faces) -> list[tuple]:
    f=canonical_faces(faces); es=spatial_edges(f); valid=[]
    for e,incident in sorted(es.items()):
        if len(incident)!=2: continue
        opposites=tuple(sorted(next(v for v in tri if v not in e) for tri in incident))
        if len(set(opposites))==2 and opposites not in es: valid.append(e)
    return valid


def edge_flip(faces, edge) -> tuple[tuple, dict]:
    f=canonical_faces(faces); e=simplex_key(edge)
    if len(e)!=2: raise ValueError("edge must contain two vertices")
    es=spatial_edges(f)
    if e not in es or len(es[e])!=2: raise ValueError("edge must have two incident faces")
    old=es[e]; other=tuple(sorted(next(v for v in tri if v not in e) for tri in old))
    if len(set(other))!=2 or other in es: raise ValueError("flip would create duplicate edge")
    new=[tuple(sorted((*other,v))) for v in e]
    result=canonical_faces((set(f)-set(old))|set(new)); sphere_audit(result)
    return result,dict(removed=[list(x) for x in old],added=[list(x) for x in new],
                       old_edge=list(e),new_edge=list(other))


def undo_flips(faces, ledger) -> tuple:
    result=canonical_faces(faces)
    for operation in reversed(ledger):
        result,_=edge_flip(result,operation['new_edge'])
    return result


def random_flips(faces, count: int, *, seed=0) -> tuple[tuple,list]:
    if not isinstance(count,int) or count<0: raise ValueError("invalid flip count")
    result=canonical_faces(faces); initial=result; rng=np.random.default_rng(seed); ledger=[]
    for _ in range(count):
        choices=flippable_edges(result)
        if not choices: raise ValueError("no admissible edge flip")
        result,record=edge_flip(result,choices[int(rng.integers(len(choices)))])
        ledger.append(record)
    if undo_flips(result,ledger)!=initial: raise ArithmeticError("reverse intervention failed")
    return result,ledger


def necks(faces) -> dict:
    """Separating non-facial 3-cycles on a validated spherical spatial slice."""
    f=canonical_faces(faces); sphere_audit(f); es=spatial_edges(f); g=nx.Graph(); g.add_edges_from(es)
    face_set=set(f); candidates=[]
    for a in sorted(g):
        higher={b for b in g[a] if b>a}
        for b in sorted(higher):
            for c in sorted(higher.intersection(g[b])):
                if c>b and (a,b,c) not in face_set: candidates.append((a,b,c))
    records=[]
    for tri in candidates:
        remaining=g.copy(); remaining.remove_nodes_from(tri)
        components=sorted((len(c) for c in nx.connected_components(remaining)),reverse=True)
        if len(components)>1:
            records.append(dict(vertices=list(tri),component_sizes=components,
                                smaller_side=min(components)))
    return dict(separating_triangle_count=len(records),necks=records,
                definition='separating non-facial spatial 3-cycles, not spacetime handles')


@dataclass
class Triangulation:
    time: np.ndarray
    tetra: np.ndarray
    neighbors: np.ndarray
    ordered: bool=True


def build_neighbors(tetra) -> np.ndarray:
    raw=np.asarray(tetra)
    if raw.ndim!=2 or raw.shape[1]!=4 or raw.dtype.kind not in 'iu' or len(raw)==0:
        raise ValueError("need integer tetrahedra")
    seen=set(); incidence=defaultdict(list)
    for i,row in enumerate(raw):
        cell=simplex_key(row)
        if cell in seen: raise ValueError("duplicate tetrahedron")
        seen.add(cell)
        for k in range(4):
            face=tuple(sorted(int(v) for j,v in enumerate(row) if j!=k)); incidence[face].append((i,k))
    nei=np.full(raw.shape,-1,dtype=np.int64)
    for face,incident in incidence.items():
        if len(incident)!=2: raise ValueError(f"face {face} has incidence {len(incident)}, not 2")
        (a,k),(b,l)=incident; nei[a,k]=b; nei[b,l]=a
    from_neighbors(nei)
    return nei


def product_cdt(faces, time_slices: int=4) -> Triangulation:
    f=canonical_faces(faces); sphere_audit(f)
    if not isinstance(time_slices,int) or time_slices<3: raise ValueError("need >=3 periodic time slices")
    verts=sorted({v for tri in f for v in tri}); mapping={v:i for i,v in enumerate(verts)}
    f=canonical_faces([[mapping[v] for v in tri] for tri in f]); n=len(verts); cells=[]
    for t in range(time_slices):
        u=(t+1)%time_slices
        for a,b,c in f:
            a0,b0,c0=a+t*n,b+t*n,c+t*n; a1,b1,c1=a+u*n,b+u*n,c+u*n
            cells.extend([(a0,b0,c0,c1),(a0,b0,b1,c1),(a0,a1,b1,c1)])
    tetra=np.asarray(cells,dtype=np.int64)
    return Triangulation(np.repeat(np.arange(time_slices),n),tetra,build_neighbors(tetra))


def audit_cdt(g: Triangulation, *, vertex_links=True) -> dict:
    """Independent combinatorial checks; unlike legacy asserts these stay on under -O."""
    time=np.asarray(g.time); cells=np.asarray(g.tetra); neighbors=np.asarray(g.neighbors)
    if time.ndim!=1 or time.dtype.kind not in 'iu' or len(time)<4:
        raise ValueError("invalid vertex times")
    if cells.ndim!=2 or cells.shape[1]!=4 or cells.dtype.kind not in 'iu':
        raise ValueError("invalid tetrahedra")
    if np.any(cells<0) or np.any(cells>=len(time)):
        raise ValueError("tetra vertex out of range")
    T=int(time.max())+1
    if T<3 or set(time.tolist())!=set(range(T)) or len(set(cells.ravel()))!=len(time):
        raise ValueError("invalid foliation or unused vertices")
    expected=build_neighbors(cells)
    if neighbors.shape!=expected.shape or neighbors.dtype.kind not in 'iu':
        raise ValueError("invalid neighbors")
    if g.ordered:
        if not np.array_equal(expected,neighbors): raise ValueError("neighbor face slots disagree")
    elif not np.array_equal(np.sort(expected,axis=1),np.sort(neighbors,axis=1)):
        raise ValueError("neighbor incidence disagrees")
    edges=set(); faces=set(); link=defaultdict(list); types=Counter(); profile=np.zeros(T,dtype=int)
    for row in cells:
        ct=Counter(map(int,time[row])); lower=next((t for t in ct if (t+1)%T in ct),None)
        if len(ct)!=2 or lower is None: raise ValueError("noncausal time incidence")
        typ=(ct[lower],ct[(lower+1)%T])
        if typ not in ((3,1),(2,2),(1,3)): raise ValueError("invalid CDT tetra type")
        types[str(typ)]+=1
        if typ==(3,1): profile[lower]+=1
        s=tuple(sorted(map(int,row))); edges.update(combinations(s,2)); faces.update(combinations(s,3))
        if vertex_links:
            for v in s: link[v].append(tuple(w for w in s if w!=v))
    for t in range(T):
        sf=[f for f in faces if all(time[v]==t for v in f)]
        sphere_audit(sf)
    if vertex_links:
        for triangles in link.values(): sphere_audit(triangles)
    chi=len(time)-len(edges)+len(faces)-len(cells)
    if chi!=0: raise ValueError("incorrect closed 3-manifold Euler characteristic")
    return dict(N0=len(time),N1=len(edges),N2=len(faces),N3=len(cells),chi=chi,
                time_extent=T,tetra_types=dict(types),spatial_volume=profile.tolist(),
                all_vertex_links_S2=bool(vertex_links),dual_regular_degree=4,
                boltzmann_sample=False)


def write_geometry(g: Triangulation, path) -> None:
    p=Path(path)
    if p.exists(): raise FileExistsError(p)
    values=np.concatenate(([int(g.ordered),len(g.time)],g.time,[len(g.time),len(g.tetra)],
                           np.column_stack((g.tetra,g.neighbors)).ravel(),[len(g.tetra)]))
    with p.open('x') as f: np.savetxt(f,values,fmt='%d')


def read_geometry(path) -> Triangulation:
    """Strict legacy .dat parser; never silently truncates floating/non-numeric text."""
    tokens=Path(path).read_text().split()
    try: a=np.asarray([int(t) for t in tokens],dtype=np.int64)
    except (ValueError,OverflowError) as exc: raise ValueError("invalid integer geometry") from exc
    if len(a)<4 or a[0] not in (0,1) or a[1]<4: raise ValueError("invalid geometry header")
    ordered,n0=map(int,a[:2]); pos=2+n0
    if pos+2>=len(a) or a[pos]!=n0 or a[pos+1]<1: raise ValueError("vertex count sentinel")
    n3=int(a[pos+1]); pos+=2
    if len(a)!=pos+8*n3+1 or a[-1]!=n3: raise ValueError("tetra count sentinel")
    rows=a[pos:-1].reshape(n3,8)
    return Triangulation(a[2:2+n0].copy(),rows[:,:4].copy(),rows[:,4:].copy(),bool(ordered))


def geometry_digest(g) -> str:
    h=hashlib.sha256()
    for array in (g.time,g.tetra,g.neighbors):
        a=np.asarray(array,dtype='<i8'); h.update(np.asarray(a.shape,dtype='<i8').tobytes()); h.update(a.tobytes())
    h.update(bytes([bool(g.ordered)])); return h.hexdigest()
