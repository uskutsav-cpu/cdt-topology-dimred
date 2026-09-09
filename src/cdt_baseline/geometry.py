"""Independent closed-manifold checks without Python asserts or native caches."""
from __future__ import annotations
from collections import defaultdict
from itertools import combinations
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from geometry import read_geometry


def connected(adjacency):
    if not adjacency:
        return False
    start=next(iter(adjacency)); seen={start}; stack=[start]
    while stack:
        for v in adjacency[stack.pop()]:
            if v not in seen:
                seen.add(v);stack.append(v)
    return len(seen)==len(adjacency)


def validate_geometry(g) -> dict:
    times=np.asarray(g.time);tet=np.asarray(g.tetra);nb=np.asarray(g.neighbors)
    if times.ndim!=1 or times.dtype.kind not in 'iu' or len(times)<4:
        raise ValueError('invalid vertex-time array')
    if tet.ndim!=2 or tet.shape[1]!=4 or tet.dtype.kind not in 'iu' or len(tet)<5:
        raise ValueError('invalid tetrahedron array')
    n=len(tet);n0=len(times);T=int(times.max())+1
    if T<3 or set(times.tolist())!=set(range(T)) or np.any(tet<0) or np.any(tet>=n0):
        raise ValueError('invalid foliation/vertex indices')
    if nb.shape!=tet.shape or nb.dtype.kind not in 'iu' or np.any(nb<0) or np.any(nb>=n):
        raise ValueError('invalid dual neighbors')
    if not g.ordered:
        raise ValueError('native baseline exports must use opposite-face ordering')
    cells=np.sort(tet,axis=1)
    if np.any(np.diff(cells,axis=1)==0) or len(np.unique(cells,axis=0))!=n:
        raise ValueError('duplicate/degenerate tetrahedra')
    if len(np.unique(tet))!=n0:
        raise ValueError('unused vertices')
    profiles=np.zeros(T,dtype=np.int64);types=np.zeros(3,dtype=np.int64)
    face_map={};edges=defaultdict(list);vertex_face_counts=np.zeros(n0,dtype=np.int64)
    vertex_tet_counts=np.bincount(tet.ravel(),minlength=n0)
    slice_faces=defaultdict(list)
    for i,(cell,unsorted) in enumerate(zip(cells,tet)):
        values,counts=np.unique(times[cell],return_counts=True)
        if len(values)!=2:
            raise ValueError('tetrahedron does not connect exactly two times')
        lower=next((int(v) for v in values if (int(v)+1)%T in values),None)
        if lower is None:
            raise ValueError('nonadjacent time slices')
        lower_count=int(np.count_nonzero(times[cell]==lower))
        types[{3:0,1:1,2:2}[lower_count]]+=1
        if lower_count==3:
            profiles[lower]+=1
        for a,b in combinations(range(4),2):
            v,w=int(cell[a]),int(cell[b]);op=[int(cell[k]) for k in range(4) if k not in (a,b)]
            edges[v,w].append(tuple(op))
        if len(set(nb[i]))!=4 or i in nb[i]:
            raise ValueError('dual self-neighbor or duplicate neighbor')
        for k in range(4):
            face=tuple(sorted(int(v) for l,v in enumerate(unsorted) if l!=k))
            j=int(nb[i,k])
            if i not in nb[j] or not set(face).issubset(tet[j]):
                raise ValueError('opposite face / reciprocal neighbor mismatch')
            if face in face_map:
                old,count=face_map[face]
                if count!=1 or old!=j:
                    raise ValueError('face incidence is not exactly two')
                face_map[face]=(old,2)
            else:
                face_map[face]=(i,1)
                for v in face:vertex_face_counts[v]+=1
                if all(times[v]==times[face[0]] for v in face):slice_faces[int(times[face[0]])].append(face)
    if any(count!=2 for _,count in face_map.values()):
        raise ValueError('open face')
    # Every edge link must be one circle: no disjoint circles or repeated edges.
    degrees=np.zeros(n0,dtype=np.int64);vertex_adj=defaultdict(set)
    for (v,w),opposites in edges.items():
        degrees[v]+=1;degrees[w]+=1;adj=defaultdict(set)
        for a,b in opposites:
            if b in adj[a]:raise ValueError('repeated link edge')
            adj[a].add(b);adj[b].add(a)
            # Connectivity in the link of v and w is inherited from these edges.
            vertex_adj[v].add(w);vertex_adj[w].add(v)
        if any(len(x)!=2 for x in adj.values()) or not connected(adj):
            raise ValueError('edge link is not a circle')
    # Closed two-manifold vertex links + chi=2 are connected spheres only after
    # explicitly checking connectivity (dual star adjacency through faces).
    if np.any(degrees-vertex_face_counts+vertex_tet_counts!=2):
        raise ValueError('vertex link Euler characteristic is not two')
    stars=defaultdict(set)
    for i,row in enumerate(tet):
        for v in row:stars[int(v)].add(i)
    for v,star in stars.items():
        first=next(iter(star));seen={first};stack=[first]
        while stack:
            for j in nb[stack.pop()]:
                if int(j) in star and int(j) not in seen:
                    seen.add(int(j));stack.append(int(j))
        if seen!=star:raise ValueError('vertex link disconnected')
    for t in range(T):
        faces=slice_faces[t];es=defaultdict(int);verts=set();adj=defaultdict(set)
        for f in faces:
            verts.update(f)
            for a,b in combinations(f,2):es[a,b]+=1;adj[a].add(b);adj[b].add(a)
        if not faces or any(c!=2 for c in es.values()) or not connected(adj) or len(verts)-len(es)+len(faces)!=2:
            raise ValueError('spatial slice is not a connected closed sphere')
        # Spatial vertex links must also be circles (not a pinched sphere).
        links=defaultdict(lambda:defaultdict(set))
        for a,b,c in faces:
            for v,x,y in ((a,b,c),(b,a,c),(c,a,b)):
                links[v][x].add(y);links[v][y].add(x)
        for v,la in links.items():
            if any(len(x)!=2 for x in la.values()) or not connected(la):
                raise ValueError('spatial vertex link not a circle')
    A=csr_matrix((np.ones(n*4),(np.repeat(np.arange(n),4),nb.ravel())),shape=(n,n))
    if connected_components(A,directed=False,return_labels=False)!=1:
        raise ValueError('disconnected spacetime')
    chi=n0-len(edges)+len(face_map)-n
    if chi!=0:raise ValueError('spacetime Euler characteristic is not zero')
    peak=int(profiles.argmax());distance=np.minimum((np.arange(T)-peak)%T,(peak-np.arange(T))%T)
    return dict(N0=n0,N1=len(edges),N2=len(face_map),N3=n,chi=chi,time_extent=T,
                N31=int(types[0]),N13=int(types[1]),N22=int(types[2]),
                spatial_volume=profiles.tolist(),peak_volume=int(profiles.max()),
                peak_time=peak,profile_width=float(np.sqrt(np.sum(profiles*distance**2)/profiles.sum())),
                profile_participation=float(profiles.sum()**2/np.sum(profiles**2)),
                profile_peak_fraction=float(profiles.max()/profiles.sum()),
                all_edge_links_circles=True,all_vertex_links_S2=True,all_spatial_slices_S2=True)
