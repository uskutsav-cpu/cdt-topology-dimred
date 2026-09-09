# Paired half-power diffusion and uncertainty

## Estimator and exact identities

The microscopic transition matrix is unchanged. Class labels restrict origins,
never paths. For independent full-graph Rademacher vectors z, E[zz^T]=I. Let
x_k=M^k z. Symmetry of M gives, site by site,

    E[x_k(i)^2] = (M^(2k))_ii
    E[x_k(i) x_(k+1)(i)] = (M^(2k+1))_ii.

One sparse propagation therefore supplies an odd and an even return time.
All origin classes share the same probes. The class-weighted mixture identity
holds on each probe realization, not just in expectation. Even-time individual
estimates are nonnegative. Odd-time estimates can be negative; no clipping is
performed. A conventional z(i)(M^s z)(i) implementation is included as an
independent backend. Exhaustive sign-vector tests reproduce exact diagonals.

The random-probe foundation is related to the diagonal estimator of Bekas,
Kokiopoulou and Saad, “An estimator for the diagonal of a matrix,” Applied
Numerical Mathematics 57 (2007), 1214–1229. The paired half-power equations
above are derived explicitly rather than assumed from that reference.
https://doi.org/10.1016/j.apnum.2007.01.003

## Reproducibility and costs

Probe streams are indexed by (seed, probe number). Changing batch size does
not change the generated probes. `first_probe` supports disjoint continuation
ranges. Independent probes are retained, allowing paired uncertainty estimates.

The sparse-work comparison counts applications to individual vector columns,
not Python API calls: P*ceil(S/2) for half-power versus N_start*S for the
original all-origin reference propagator. A block call processes several
columns at once. This is not a comparison against every possible specialized
exact algorithm. A vertex-transitive lattice, for example, has symmetry that a
specialized solver could exploit.

Memory is controlled by probe batches, an explicit estimated-array budget,
and a work cap. The estimate is not a hard RSS ceiling and excludes caller
inputs, Python overhead and numerical-library workspace. The preserved
probe-by-class-by-time array is included in the estimate. For small graphs,
exact propagation may be faster; the saved benchmarks report this rather than
claiming a universal speedup.

## Accuracy and interpretation

Unbiased P estimation does not imply unbiased Ds=-sigma(P_(s+1)-P_(s-1))/P_s.
Negative or zero mean returns invalidate the derivative. Probe bootstrap draws
retain class and time pairing; any invalid nonlinear draw prevents issuance
of a percentile interval rather than being silently dropped. Those intervals
cover only probe noise for a fixed geometry, not ensemble/MCMC/coarse-seed
uncertainty. Fixed probe counts must be calibrated against exact or independent
higher-precision references before production. Synthetic benchmark precision
is not a project-wide precision gate.

`hierarchical_uncertainty.py` separately handles chronological configuration
blocks within each supplied independent chain, coarse seed realizations within
configuration, and probes within seed realization. All class/time coordinates
remain paired. Configurations receive equal weight; seeds receive equal weight
within their configuration. It reports both dimension-of-mean-return and
mean-of-configuration-dimensions. Block length is in stored configurations.
Thermalization, sufficiently long blocks, independence between chains, and
adequate coarse sampling remain scientific assumptions.

## Controls

`conditioned_controls.py` implements outcome-blind exact categorical overlap
weighting, with equal covariate-bin distributions between classes. It reports
excluded nonoverlap and changes the estimand to overlap support. Covariate bins
must be frozen before inspecting outcome curves. Configuration-grouped folds
never split a configuration across folds.

Stratified permutation tests preserve class counts within each matching bin.
They require an explicit exchangeability-assumption string; the code does not
validate that assumption. Spatially correlated topology labels generally do
not justify naive shuffling. Their one-sided Monte Carlo p-value uses the +1
correction and is neither an equilibrium certificate nor a causal conclusion.

## Production interface

`workflows/measure_conditioned_fast.py` requires the four original evidence-
backed gates, geometry/label hashes, and an independently approved mapping
artifact. It refuses explicitly experimental mappings. It supports no gate-
bypass flag. Outputs and manifests are immutable and cache-verified. Existing
exact measurement code remains available and unchanged.
