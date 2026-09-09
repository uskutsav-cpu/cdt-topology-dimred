"""Paired chain-block uncertainty, with the sampling unit made explicit."""
import numpy as np
from spectral import dimension
from conditioned import _positive_int


def circular_block_indices(n, block_length, rng):
    n = _positive_int(n, 'chain length', 2)
    block_length = _positive_int(block_length, 'block length')
    if 2 * block_length > n:
        raise ValueError('at least two blocks per chain required')
    starts = rng.integers(n, size=(n + block_length - 1) // block_length)
    return ((starts[:, None] + np.arange(block_length)) % n).ravel()[:n]


def paired_block_effect(chains, window, *, block_length, replicates=1000, seed=0):
    """Bootstrap A=mean_window(D_R-D_Q); input per chain: draw x 2 x sigma.

    Resample chronological configuration BLOCKS within each independent chain.
    The SAME selected indices resample both classes and all diffusion times.
    Each chain retains its original length; pooling weights configurations
    equally. This estimand is not a site-count-weighted ensemble average.

    block_length is in STORED CONFIGURATIONS, not sweeps. It must be chosen
    using relevant autocorrelation diagnostics and tested for sensitivity.
    This function cannot certify equilibrium or create causal identification.
    """
    block_length = _positive_int(block_length, 'block length')
    replicates = _positive_int(replicates, 'replicates', 20)
    arrays = [np.asarray(c, float) for c in chains]
    if not arrays or any(c.ndim != 3 or c.shape[1] != 2 or len(c) < 2 * block_length for c in arrays):
        raise ValueError('nonempty chains of draw x 2 x sigma, with >=2 blocks, required')
    shape = arrays[0].shape[1:]
    if any(c.shape[1:] != shape or not np.isfinite(c).all() or (c <= 0).any() for c in arrays):
        raise ValueError('all chains need matching, positive finite return curves')
    w = np.asarray(window)
    if (w.ndim != 1 or not len(w) or w.dtype.kind not in 'iu'
            or len(set(w.tolist())) != len(w) or w.min() < 1 or w.max() >= shape[1] - 1):
        raise ValueError('unique interior integer diffusion times required')
    n = sum(len(c) for c in arrays)
    pooled = sum(c.sum(axis=0) for c in arrays) / n
    observed_ds = dimension(pooled)
    observed_delta = observed_ds[0] - observed_ds[1]
    observed = float(observed_delta[w].mean())
    rng = np.random.default_rng(seed)
    effects = np.empty(replicates)
    delta_samples = np.empty((replicates, shape[1]))
    for b in range(replicates):
        mean = sum(c[circular_block_indices(len(c), block_length, rng)].sum(axis=0)
                   for c in arrays) / n
        ds = dimension(mean)
        delta_samples[b] = ds[0] - ds[1]
        effects[b] = delta_samples[b, w].mean()
    lower = np.full(shape[1], np.nan)
    upper = lower.copy()
    lower[1:-1], upper[1:-1] = np.quantile(delta_samples[:, 1:-1], [.025, .975], axis=0)
    mean_per_configuration_ds = sum(dimension(c).sum(axis=0) for c in arrays) / n
    return {'A': observed, 'A_CI95': np.quantile(effects, [.025, .975]),
            'delta_Ds': observed_delta, 'delta_pointwise_CI95': np.stack((lower, upper)),
            'Ds_of_mean_return': observed_ds,
            'mean_of_configuration_Ds': mean_per_configuration_ds,
            'bootstrap_A': effects, 'configuration_count': n,
            'chain_count': len(arrays), 'block_length_configurations': block_length,
            'seed': seed, 'replicates': replicates, 'window': w,
            'inference_status': 'requires independently validated equilibrated inputs; intervals are pointwise'}
