"""Partition-conditioned returns with an UNCHANGED microscopic operator.

Exact propagation is streamed in start-site blocks. No graph excision or
walk confinement is performed. This module computes observables, not evidence
that any supplied label is a validated topological stratum.
"""
from numbers import Integral
import numpy as np
from scipy.sparse import csr_matrix
from spectral import exact_returns, dimension


def checked_operator(matrix):
    m = csr_matrix(matrix, dtype=float, copy=True)
    if not m.shape[0] or m.shape[0] != m.shape[1]:
        raise ValueError('nonempty square transition matrix required')
    m.sum_duplicates()
    if not np.isfinite(m.data).all() or np.any(m.data < 0):
        raise ValueError('transition probabilities must be finite and nonnegative')
    diff = m - m.T
    if diff.nnz and np.max(np.abs(diff.data)) > 1e-12:
        raise ValueError('symmetric microscopic diffusion operator required')
    if not np.allclose(np.asarray(m.sum(axis=1)).ravel(), 1, rtol=0, atol=1e-12):
        raise ValueError('transition matrix must preserve probability')
    return m


def _positive_int(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return int(value)


def partition_returns(matrix, masks, steps, *, block_size=32, start_mask=None):
    """Exact class means. Masks partition start_mask (all nodes by default).

    Paths still visit all microscopic nodes even when the start population is
    condensate-only. Complexity is O(steps * edges * number_of_starts), with
    O(nodes * block_size) propagation memory, not a dense nodes-squared matrix.
    """
    m = checked_operator(matrix)
    steps = _positive_int(steps, 'steps', 0)
    block_size = _positive_int(block_size, 'block_size')
    n = m.shape[0]
    starts = np.ones(n, dtype=bool) if start_mask is None else np.asarray(start_mask)
    if starts.dtype != np.bool_ or starts.shape != (n,) or not starts.any():
        raise ValueError('nonempty boolean start mask of length n required')
    if not masks or any(not isinstance(k, str) or not k for k in masks):
        raise ValueError('named, nonempty partition required')
    arrays = [np.asarray(mask) for mask in masks.values()]
    if any(mask.dtype != np.bool_ or mask.shape != (n,) or not mask.any() for mask in arrays):
        raise ValueError('every class must be a nonempty boolean mask of length n')
    coverage = np.sum(arrays, axis=0)
    if not np.array_equal(coverage, starts.astype(int)):
        raise ValueError('class masks must partition precisely the start population')
    curves, counts = [], []
    for mask in arrays:
        ids = np.flatnonzero(mask)
        total = np.zeros(steps + 1)
        for i in range(0, len(ids), block_size):
            total += exact_returns(m, steps, ids[i:i + block_size]).sum(axis=0)
        curves.append(total / len(ids))
        counts.append(len(ids))
    curves = np.asarray(curves)
    counts = np.asarray(counts, dtype=int)
    fractions = counts / counts.sum()
    return {'names': tuple(masks), 'counts': counts, 'P_class': curves,
            'P_all': fractions @ curves, 'Ds_class': dimension(curves),
            'operator_unchanged': True, 'start_count': int(counts.sum())}


def decompose_dimension(curves, counts):
    """Exact mixture identity for this code's linear central derivative.

    Ds_all = sum_c w_c(sigma) Ds_c, w_c = f_c P_c / sum_j f_j P_j.
    Size fractions alone are NOT the contribution weights. Across ensembles,
    combine at configuration level or retain count/return covariance explicitly.
    """
    curves = np.asarray(curves, float)
    counts = np.asarray(counts, float)
    if curves.ndim != 2 or curves.shape[1] < 3 or counts.shape != (len(curves),):
        raise ValueError('class x time curves and one count per class required')
    if (not np.isfinite(curves).all() or (curves <= 0).any()
            or not np.isfinite(counts).all() or (counts <= 0).any()):
        raise ValueError('positive finite curves and counts required')
    fractions = counts / counts.sum()
    total = fractions @ curves
    weights = fractions[:, None] * curves / total
    direct = dimension(total)
    reconstructed = np.sum(weights * dimension(curves), axis=0)
    residual = float(np.max(np.abs(direct[1:-1] - reconstructed[1:-1])))
    return {'P_all': total, 'weights': weights, 'Ds_all': direct,
            'Ds_reconstructed': reconstructed, 'maximum_identity_error': residual}
