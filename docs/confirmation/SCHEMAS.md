# Saved evidence schema

A `cdt-confirmation-stage-v1` directory is complete only when `manifest.json`
exists, `complete` is true, the exact artifact set matches, and every artifact
hash verifies. The identity contains the measurement or analysis configuration,
input hashes, numerical source hashes, and the numerical environment. A lock or
partial directory is not a completed stage.

## Census and finite-size geometry stages

`geometry.dat` uses the native lossless ordered tetrahedron interchange format.
`summary.json` records the seed, full-root flag, original-validator blob hash,
geometry hash, topology/graph aggregate features, field comparisons, independent
rank checks, timing/RSS and the non-physical construction provenance.

`diffusion.npz` contains roots, integer sigma including zero, exact returns,
mean-square displacement, local Ds, stationary return levels, pre-mix masks,
full-return trace and its Ds, and measured distance distributions/quantiles.
Undefined log slopes at unsupported endpoints are NaN, never fabricated zeros.

`root_measurements.json` contains one row per root. Columns distinguish radii,
time endpoints, unit-equilateral curvature proxy, tetrahedron type and time
slice. Empty finite-bar lifetime means/medians are null. Right-censored counts
and observed persistence are not silently collapsed into finite-bar statistics.

`positive_barcodes.json.gz` stores positive-length interval multiplicities by
root and field. Null death denotes right censoring in the truncated filtration;
it is not automatically an essential ambient class. Zero-length intervals are
intentionally omitted from this saved barcode representation. The field subset
is independently uniform; the F2 primary census includes every root.

## Paired operators

`operators.json` stores exact reversal/validity checks, FEM mesh sizes, complete
or truncated spectra, eigenpair/orthogonality residuals, Galerkin/volume audits,
Ritz changes, fixed-clock heat traces, conditional finite-matrix tail bounds and
refinement flags. `diffusion.npz` stores exact dual-walk observations.
`root_persistence.json` stores the paired-study root features; full barcodes can
be regenerated exactly from its saved geometry. The separate clock-reference
stage is never fitted to each intervention's outcome.

## Analysis

The primary `analysis.json` identifies the frozen primary test, training and
confirmation results, cluster-based controlled estimates, destructive negative
controls, matching/balance, corrected scan, held-out selected ridge and separate
secondary neck-descriptor tests. `primary_nulls.npz` preserves permutation nulls.
The legacy field `independent_chains` is a geometry-cluster count in these
constructed-study results, not a count of physical CDT chains.

`FINAL_RUNS.json` points to the delivered original numerical snapshots.
`COMPUTED_RESULTS.json` combines their values for plotting and reading; it is
not a replacement for the hashed underlying stages. The portable collector
verifies current-source inputs and emits a new atomic report/figure stage.

## Physical readiness

The native audit reads existing `results/manifests/*.json`, their original
stage/parameters metadata and hashed native CSV/geometry outputs. Its output
contains missing requirements, validation failures and diagnostic screens.
`BLOCKED` means unavailable/insufficient input, not a measured physics null.
The synthetic calibration NPZ is explicitly labeled not CDT.
