"""Lossless upstream geometry interchange and independent combinatorial checks."""
from pathlib import Path
from dataclasses import dataclass
from itertools import combinations
from collections import defaultdict, Counter
import hashlib, json
import numpy as np

@dataclass
class Geometry:
    time: np.ndarray
    tetra: np.ndarray
    neighbors: np.ndarray
    ordered: bool = True

def read_geometry(path):
    a=np.fromstring(Path(path).read_text(),dtype=np.int64,sep=' ')
    if len(a)<4: raise ValueError('truncated geometry')
    ordered,n0=a[:2]; pos=2+n0
    if a[pos]!=n0: raise ValueError('vertex count sentinel')
    n3=int(a[pos+1]); pos+=2
    if len(a)!=pos+8*n3+1 or a[-1]!=n3: raise ValueError('tetra count sentinel')
    rows=a[pos:-1].reshape(n3,8)
    return Geometry(a[2:2+n0].copy(), rows[:,:4].copy(),rows[:,4:].copy(),bool(ordered))

def write_geometry(g,path):
    a=np.concatenate(([int(g.ordered),len(g.time)],g.time,[len(g.time),len(g.tetra)],np.column_stack((g.tetra,g.neighbors)).ravel(),[len(g.tetra)]))
    with open(path,'x') as f: np.savetxt(f,a,fmt='%d')

def validate(g, links=True):
    n0,n3=len(g.time),len(g.tetra); T=int(g.time.max())+1
    assert T>=3 and g.time.min()==0
    assert g.tetra.shape==(n3,4) and g.neighbors.shape==(n3,4)
    assert g.tetra.min()>=0 and g.tetra.max()<n0
    assert g.neighbors.min()>=0 and g.neighbors.max()<n3
    assert len(set(g.tetra.ravel()))==n0
    edges=set(); faces=defaultdict(list); vertex_links=defaultdict(list); unique=set(); types=Counter()
    profile=np.zeros(T,dtype=int)
    for i,row in enumerate(g.tetra):
        vs=tuple(sorted(map(int,row))); assert len(set(vs))==4 and vs not in unique; unique.add(vs)
        times=Counter(g.time[row]); assert len(times)==2
        lower=next((t for t in times if (t+1)%T in times),None); assert lower is not None
        typ=(times[lower],times[(lower+1)%T]); assert typ in [(3,1),(2,2),(1,3)]
        types[str(typ)]+=1
        if typ==(3,1): profile[lower]+=1
        for e in combinations(vs,2): edges.add(e)
        for f in combinations(vs,3): faces[f].append(i)
        for v in vs: vertex_links[v].append(tuple(w for w in vs if w!=v))
        assert len(set(g.neighbors[i]))==4 and i not in g.neighbors[i]
        for j in g.neighbors[i]:
            assert i in g.neighbors[j] and len(set(row)&set(g.tetra[j]))==3
        if g.ordered:
            for k,j in enumerate(g.neighbors[i]): assert set(np.delete(row,k))<=set(g.tetra[j])
    assert all(len(v)==2 for v in faces.values())
    assert n0-len(edges)+len(faces)-n3==0
    for i in range(T):
        sf=[f for f in faces if all(g.time[v]==i for v in f)]
        se={e for f in sf for e in combinations(f,2)}
        sv={v for f in sf for v in f}
        assert len(sv)-len(se)+len(sf)==2, 'spatial slice is not a sphere'
    # A connected closed triangulated 2-manifold with chi=2 is S^2.
    # Also require every link vertex neighborhood to be a cycle.
    if links:
        for v,triangles in vertex_links.items():
            ef=defaultdict(list); verts=set(); around=defaultdict(list)
            for k,tr in enumerate(triangles):
                verts.update(tr)
                for e in combinations(tr,2): ef[e].append(k)
                for w in tr: around[w].append(tuple(x for x in tr if x!=w))
            assert all(len(x)==2 for x in ef.values()),('link edge incidence',v)
            assert len(verts)-len(ef)+len(triangles)==2,('link Euler',v)
            adj=defaultdict(set)
            for a,b in ef.values(): adj[a].add(b); adj[b].add(a)
            assert len(reachable(adj,0))==len(triangles),('disconnected link',v)
            for es in around.values():
                aj=defaultdict(set)
                for a,b in es: aj[a].add(b); aj[b].add(a)
                assert all(len(x)==2 for x in aj.values())
                assert len(reachable(aj,next(iter(aj))))==len(aj)
    return {'N0':n0,'N1':len(edges),'N2':len(faces),'N3':n3,'chi':0,'time_extent':T,'tetra_types':dict(types),'spatial_volume':profile.tolist(),'all_vertex_links_S2':bool(links)}

def reachable(adj,start):
    seen={start}; todo=[start]
    while todo:
        for b in adj[todo.pop()]:
            if b not in seen: seen.add(b); todo.append(b)
    return seen

def export_npz(source,destination,metadata):
    g=read_geometry(source); report=validate(g)
    metadata={**metadata,'input_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),'validation':report}
    with open(destination,'xb') as f:
        np.savez_compressed(f,time=g.time,tetra=g.tetra,neighbors=g.neighbors,ordered=g.ordered,metadata=json.dumps(metadata))
    return report
