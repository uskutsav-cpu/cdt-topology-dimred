"""Validated sparse undirected graph operations (no geometry claims)."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components, shortest_path


def adjacency(value, *, connected: bool = True) -> sparse.csr_matrix:
    """Reject directed, negative, nonfinite, looped, or isolated input.

    Positive symmetric weights are allowed; distances elsewhere are hop distances,
    not inverse-conductance distances. Duplicate sparse entries are summed.
    """
    a = sparse.csr_matrix(value, dtype=np.float64, copy=True)
    a.sum_duplicates(); a.eliminate_zeros(); a.sort_indices()
    if a.shape[0] != a.shape[1] or a.shape[0] < 2:
        raise ValueError("adjacency must be square with at least two vertices")
    if not np.isfinite(a.data).all() or np.any(a.data < 0):
        raise ValueError("weights must be finite and nonnegative")
    if np.any(a.diagonal() != 0):
        raise ValueError("supply a loop-free graph; laziness is added explicitly")
    d = a-a.T
    if d.nnz and np.max(np.abs(d.data)) > 1e-12:
        raise ValueError("graph must be undirected with symmetric weights")
    # Eliminate roundoff-level asymmetry instead of silently using a directed kernel.
    a = ((a+a.T)*0.5).tocsr()
    if np.any(np.asarray(a.sum(axis=1)).ravel() <= 0):
        raise ValueError("isolated vertices are not supported")
    if connected and connected_components(a, directed=False, return_labels=False) != 1:
        raise ValueError("graph must be connected")
    return a


def from_neighbors(neighbors) -> sparse.csr_matrix:
    raw = np.asarray(neighbors)
    if raw.ndim != 2 or raw.dtype.kind not in 'iu' or raw.shape[1] == 0:
        raise ValueError("neighbors must be a rectangular integer array")
    n, k = raw.shape
    if np.any(raw < 0) or np.any(raw >= n):
        raise ValueError("neighbor index out of range")
    if any(len(set(row)) != k for row in raw.tolist()):
        raise ValueError("duplicate neighbor; multiplicities require explicit weights")
    return adjacency(sparse.coo_matrix((np.ones(n*k),
                       (np.repeat(np.arange(n), k), raw.ravel())), shape=(n,n)))


def degrees(a) -> np.ndarray:
    return np.asarray(a.sum(axis=1)).ravel()


def distances(a, roots) -> np.ndarray:
    roots = checked_roots(roots, a.shape[0])
    return np.atleast_2d(shortest_path(a, directed=False, unweighted=True, indices=roots))


def checked_roots(roots, n: int) -> np.ndarray:
    r = np.asarray(roots)
    if r.ndim != 1 or r.dtype.kind not in 'iu' or len(r) == 0:
        raise ValueError("roots must be a nonempty integer vector")
    if np.any(r < 0) or np.any(r >= n) or len(np.unique(r)) != len(r):
        raise ValueError("roots must be distinct valid vertices")
    return r.astype(np.int64)


def digest(a) -> str:
    a = adjacency(a)
    h = hashlib.sha256()
    for item in [np.asarray(a.shape, dtype='<i8'), a.indptr.astype('<i8'),
                 a.indices.astype('<i8'), a.data.astype('<f8')]:
        h.update(item.tobytes())
    return h.hexdigest()


@dataclass(frozen=True)
class Cut:
    boundary_weight: float
    set_volume: float
    complement_volume: float
    conductance: float
    one_step_escape: float


def cut(a, vertices) -> Cut:
    """Full-graph conductance, not conductance of an induced/restricted walk."""
    raw = np.asarray(vertices)
    if raw.dtype.kind == 'b':
        if raw.shape != (a.shape[0],):
            raise ValueError("incorrect mask length")
        mask = raw.copy()
    else:
        if raw.ndim != 1 or raw.dtype.kind not in 'iu':
            raise ValueError("vertices must be integer indices or a boolean mask")
        if np.any(raw < 0) or np.any(raw >= a.shape[0]):
            raise ValueError("cut vertex out of range")
        mask = np.zeros(a.shape[0], dtype=bool); mask[raw] = True
    vol = float(degrees(a)[mask].sum())
    other = float(degrees(a)[~mask].sum())
    boundary = float(a[mask][:, ~mask].sum())
    if min(vol, other) <= 0:
        return Cut(boundary, vol, other, float('nan'), float('nan'))
    return Cut(boundary, vol, other, boundary/min(vol,other), boundary/vol)
