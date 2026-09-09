"""Rooted radial cuts, branching proxies and independently auditable separators.

Annular component counts and graph cycle rank are graph statistics, NOT homology
of a spacetime manifold. A Fiedler sweep is a cut upper bound, not an exact
Cheeger constant. Empty complements are undefined, never perfect bottlenecks.
"""
from __future__ import annotations
from dataclasses import asdict
import numpy as np
import networkx as nx
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import eigsh
from .graph import adjacency, checked_roots, degrees, distances, cut


def local_features(value, roots, radii) -> list[dict]:
    a = adjacency(value); roots = checked_roots(roots, a.shape[0])
    rr = np.asarray(radii)
    if rr.ndim != 1 or rr.dtype.kind not in 'iu' or len(rr) == 0 or np.any(rr < 1):
        raise ValueError("radii must be positive integers")
    if len(np.unique(rr)) != len(rr):
        raise ValueError("duplicate radii")
    deg = degrees(a); ds = distances(a, roots); out = []
    for root, d in zip(roots, ds):
        for radius in sorted(rr.tolist()):
            mask = d <= radius; ball = a[mask][:,mask]
            c = cut(a, mask)
            n = int(mask.sum()); e = ball.nnz // 2
            annulus = (d > radius // 2) & mask
            count, labels = connected_components(a[annulus][:,annulus], directed=False)
            ann_d = d[annulus]
            # Count only components joining the inner and outer annular shells.
            branches = sum(bool(np.any(ann_d[labels == k] == radius//2+1)
                                and np.any(ann_d[labels == k] == radius))
                           for k in range(count))
            cycle_rank = e-n+1  # Ball in a connected unweighted graph is connected.
            out.append(dict(root=int(root), radius=int(radius), ball_vertices=n,
                            shell_vertices=int(np.sum(d == radius)),
                            mean_degree=float(deg[mask].mean()),
                            degree_variance=float(deg[mask].var()),
                            graph_cycle_rank=int(cycle_rank),
                            graph_cycle_fraction=float(cycle_rank/max(e,1)),
                            annular_components=int(count),
                            spanning_annular_branches=int(branches),
                            saturated_ball=bool(n == a.shape[0]), **asdict(c)))
    return out


def fiedler_sweep(value) -> dict:
    a = adjacency(value); n = a.shape[0]; d = degrees(a)
    q = sparse.diags(1/np.sqrt(d))
    lap = sparse.eye(n,format='csr')-q@a@q
    if n <= 128:
        vals, vecs = np.linalg.eigh(lap.toarray())
    else:
        # Deterministic initial vector; the reported cut may differ in degenerate eigenspaces.
        vals, vecs = eigsh(lap, k=2, which='SM', tol=1e-11,
                           v0=np.linspace(1.,2.,n))
        order = np.argsort(vals); vals,vecs = vals[order],vecs[:,order]
    gap = max(0., float(vals[1])); order = np.argsort(vecs[:,1]/np.sqrt(d), kind='stable')
    seen = np.zeros(n,dtype=bool); boundary=0.; vol=0.; best=float('inf'); best_k=0
    total = d.sum()
    for k,v in enumerate(order[:-1],1):
        lo,hi = a.indptr[v:v+2]
        boundary += d[v]-2*float(a.data[lo:hi][seen[a.indices[lo:hi]]].sum())
        vol += d[v]; seen[v] = True
        phi = max(0.,boundary)/min(vol,total-vol)
        if phi < best:
            best,best_k = phi,k
    witness = order[:best_k]
    # Recompute the winning cut, independent of incremental floating-point updates.
    phi = cut(a,witness).conductance
    return dict(normalized_gap=gap, sweep_conductance=float(phi),
                cheeger_lower_bound=gap/2, cheeger_upper_bound=min(1.,np.sqrt(2*gap)),
                witness_vertices=witness.tolist(), exact_cheeger=False)


def wired_annulus_separator(value, root: int, inner: int, outer: int) -> dict:
    """Exact min EDGE cut between a wired inner ball and the exterior of outer.

    This is not a minimum vertex neck or an exact 3-manifold neck. The endpoint
    sets prevent the trivial single-root-degree cut when inner > 0.
    """
    a = adjacency(value)
    if not (isinstance(inner,int) and isinstance(outer,int) and 0 <= inner < outer):
        raise ValueError("require integer 0 <= inner < outer")
    d = distances(a,[root])[0]
    core=np.flatnonzero(d<=inner); exterior=np.flatnonzero(d>outer)
    if not len(exterior):
        raise ValueError("outer ball fills graph: separator undefined")
    g = nx.DiGraph(); g.add_nodes_from(range(a.shape[0]+2))
    coo=a.tocoo()
    for u,v,w in zip(coo.row,coo.col,coo.data):
        g.add_edge(int(u),int(v),capacity=float(w))
    source,sink=a.shape[0],a.shape[0]+1
    wire=float(a.sum()+1)
    for v in core: g.add_edge(source,int(v),capacity=wire)
    for v in exterior: g.add_edge(int(v),sink,capacity=wire)
    strength,parts=nx.minimum_cut(g,source,sink)
    witness=np.asarray(sorted(v for v in parts[0] if v<a.shape[0]),dtype=int)
    actual=cut(a,witness)
    if abs(actual.boundary_weight-strength)>1e-8:
        raise ArithmeticError("separator witness did not verify")
    return dict(root=int(root), inner=inner, outer=outer, cut_weight=float(strength),
                witness_vertices=witness.tolist(), conductance=actual.conductance,
                core_vertices=len(core), exterior_vertices=len(exterior))
