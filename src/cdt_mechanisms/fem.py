"""Intrinsic P1 tetrahedral FEM with consistent mass and metric-preserving refinement.

The generalized eigenproblem is K u = lambda M u. Replacing it with the
unweighted vertex Laplacian is NOT FEM. Default unit edge lengths correspond
to regular Euclidean tetrahedra; a non-equilateral Wick-rotated geometry must
supply its actual edge lengths. This module does not infer them from a graph.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
import math
import numpy as np
from scipy import sparse, linalg


@dataclass
class MetricMesh:
    tetra: np.ndarray
    edge_lengths: dict[tuple[int,int],float]

    @property
    def n_vertices(self):
        return int(np.max(self.tetra))+1


@dataclass
class FEM:
    stiffness: sparse.csr_matrix
    mass: sparse.csr_matrix
    volume: float
    n_tetra: int


def metric_mesh(tetra, edge_lengths=None) -> MetricMesh:
    raw=np.asarray(tetra)
    if raw.ndim!=2 or raw.shape[1]!=4 or raw.dtype.kind not in 'iu' or len(raw)==0 or np.any(raw<0):
        raise ValueError("integer nonnegative tetrahedra required")
    canonical=[tuple(sorted(map(int,row))) for row in raw]
    if any(len(set(c))!=4 for c in canonical) or len(set(canonical))!=len(canonical):
        raise ValueError("degenerate or duplicate tetrahedron")
    if set(raw.ravel())!=set(range(int(raw.max())+1)):
        raise ValueError("vertex labels must be contiguous and all used")
    edges={e for c in canonical for e in combinations(c,2)}
    if edge_lengths is None: lengths={e:1. for e in edges}
    else:
        lengths={tuple(sorted(map(int,k))):float(v) for k,v in edge_lengths.items()}
        if set(lengths)!=edges: raise ValueError("provide exactly one length per mesh edge")
    if any(not np.isfinite(v) or v<=0 for v in lengths.values()):
        raise ValueError("edge lengths must be positive and finite")
    return MetricMesh(np.asarray(raw,dtype=np.int64).copy(),lengths)


def local_element(length_matrix) -> tuple[np.ndarray,np.ndarray,float,np.ndarray]:
    """Local K, consistent M, volume, coordinates reproducing the edge metric."""
    length=np.asarray(length_matrix,dtype=float)
    if length.shape!=(4,4) or not np.isfinite(length).all() or not np.allclose(length,length.T,rtol=0,atol=1e-13):
        raise ValueError("symmetric finite 4x4 lengths required")
    if np.any(length.diagonal()!=0) or np.any(length[np.triu_indices(4,1)]<=0):
        raise ValueError("invalid tetrahedral lengths")
    sq=length**2; gram=(sq[0,1:,None]+sq[0,None,1:]-sq[1:,1:])/2
    try: chol=np.linalg.cholesky(gram)
    except np.linalg.LinAlgError as exc: raise ValueError("edge metric is not a nondegenerate Euclidean tetrahedron") from exc
    if np.linalg.cond(gram)>1e12: raise ValueError("ill-conditioned tetrahedron")
    volume=float(np.prod(chol.diagonal())/6)
    b=np.vstack((-np.ones(3),np.eye(3)))
    k=volume*b@np.linalg.solve(gram,b.T)
    m=volume*(np.ones((4,4))+np.eye(4))/20
    coordinates=np.vstack((np.zeros(3),chol))
    return k,m,volume,coordinates


def cell_lengths(mesh: MetricMesh, cell) -> np.ndarray:
    out=np.zeros((4,4))
    for i,j in combinations(range(4),2):
        out[i,j]=out[j,i]=mesh.edge_lengths[tuple(sorted((int(cell[i]),int(cell[j]))))]
    return out


def assemble(mesh: MetricMesh, *, lumped: bool=False) -> FEM:
    # Revalidate public dataclass inputs, including missing/unused edge lengths.
    mesh=metric_mesh(mesh.tetra,mesh.edge_lengths)
    rows=[]; cols=[]; kval=[]; mval=[]; volume=0.
    for cell in mesh.tetra:
        k,m,v,_=local_element(cell_lengths(mesh,cell)); volume+=v
        rows.extend(np.repeat(cell,4)); cols.extend(np.tile(cell,4)); kval.extend(k.ravel()); mval.extend(m.ravel())
    n=mesh.n_vertices
    k=sparse.coo_matrix((kval,(rows,cols)),shape=(n,n)).tocsr()
    m=sparse.coo_matrix((mval,(rows,cols)),shape=(n,n)).tocsr()
    if lumped: m=sparse.diags(np.asarray(m.sum(axis=1)).ravel(),format='csr')
    if not np.allclose(np.asarray(k.sum(axis=1)).ravel(),0,atol=1e-10):
        raise ArithmeticError("FEM stiffness does not annihilate constants")
    if not np.isclose(float(m.sum()),volume,rtol=1e-11):
        raise ArithmeticError("FEM mass does not integrate the volume")
    return FEM(k,m,volume,len(mesh.tetra))


def full_spectrum(fem: FEM, *, dense_limit: int=1600) -> dict:
    n=fem.stiffness.shape[0]
    if n>dense_limit:
        raise ValueError("full-spectrum budget exceeded; low modes cannot establish short-time Ds")
    k=fem.stiffness.toarray(); m=fem.mass.toarray()
    vals,vecs=linalg.eigh(k,m,check_finite=True)
    residual=np.linalg.norm(k@vecs-(m@vecs)*vals,ord='fro')/max(1.,np.linalg.norm(k@vecs,ord='fro'))
    if vals[0]<-1e-8 or residual>1e-8: raise ArithmeticError("generalized eigensolver validation failed")
    vals=np.maximum(vals,0)
    return dict(eigenvalues=vals,residual=float(residual),complete=True,n_modes=n,
                zero_modes=int(np.sum(vals<1e-9)),volume=fem.volume)


def midpoint_refinement(mesh: MetricMesh) -> tuple[MetricMesh,sparse.csr_matrix]:
    """Conforming 1-to-8 tetrahedral refinement, preserving the original metric.

    Each central octahedron is divided along a deterministic internal diagonal.
    Boundary faces have the same 1-to-4 subdivision from either side. This is a
    numerical FEM refinement, not a newly sampled CDT configuration.
    """
    mesh=metric_mesh(mesh.tetra,mesh.edge_lengths); n=mesh.n_vertices
    edges=sorted(mesh.edge_lengths); mids={e:n+i for i,e in enumerate(edges)}
    cells=[]; lengths={}; rows=list(range(n)); cols=list(range(n)); weights=[1.]*n
    for e,idx in mids.items():
        rows.extend([idx,idx]); cols.extend(e); weights.extend([.5,.5])
    for cell in mesh.tetra:
        _,_,_,coords=local_element(cell_lengths(mesh,cell))
        pos={int(v):coords[i] for i,v in enumerate(cell)}
        mid_for={}
        for a,b in combinations(map(int,cell),2):
            e=tuple(sorted((a,b))); idx=mids[e]; mid_for[frozenset(e)]=idx; pos[idx]=(pos[a]+pos[b])/2
        children=[]
        for a in map(int,cell):
            children.append((a,*(mid_for[frozenset((a,b))] for b in map(int,cell) if b!=a)))
        a,b,c,d=map(int,cell)
        opposite=[(mid_for[frozenset(e)],mid_for[frozenset(f)])
                  for e,f in [((a,b),(c,d)),((a,c),(b,d)),((a,d),(b,c))]]
        p,q=min(tuple(sorted(pair)) for pair in opposite)
        inverse={value:key for key,value in mid_for.items()}
        ring=sorted(v for v in inverse if v not in (p,q))
        # Four edges around the octahedron's equatorial square.
        ring_edges=[(u,v) for u,v in combinations(ring,2) if len(inverse[u]&inverse[v])==1]
        if len(ring_edges)!=4: raise ArithmeticError("invalid midpoint octahedron")
        children.extend((p,q,u,v) for u,v in ring_edges)
        for child in children:
            cells.append(child)
            for u,v in combinations(child,2):
                e=tuple(sorted((u,v))); length=float(np.linalg.norm(pos[u]-pos[v]))
                if e in lengths and not np.isclose(lengths[e],length,rtol=1e-10,atol=1e-12):
                    raise ArithmeticError("shared-face metrics disagree")
                lengths[e]=length
    refined=metric_mesh(np.asarray(cells,dtype=np.int64),lengths)
    prolongation=sparse.coo_matrix((weights,(rows,cols)),shape=(refined.n_vertices,n)).tocsr()
    return refined,prolongation


def refinement_audit(coarse: FEM, fine: FEM, prolongation) -> dict:
    dk=prolongation.T@fine.stiffness@prolongation-coarse.stiffness
    dm=prolongation.T@fine.mass@prolongation-coarse.mass
    kerr=float(np.max(np.abs(dk.data))) if dk.nnz else 0.
    merr=float(np.max(np.abs(dm.data))) if dm.nnz else 0.
    verr=abs(coarse.volume-fine.volume)
    if kerr>1e-9 or merr>1e-9 or verr>1e-9*max(1,coarse.volume):
        raise ArithmeticError("metric-preserving FEM refinement failed the nested-space patch test")
    return dict(stiffness_galerkin_error=kerr,mass_galerkin_error=merr,volume_error=verr)
