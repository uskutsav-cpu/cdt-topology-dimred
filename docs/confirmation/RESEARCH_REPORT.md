# CDT mechanism confirmation: executed research report

**Status: constructed-geometry evidence; physical CDT mechanism not established.**

Reference repository: `uskutsav-cpu/cdt-topology-dimred`, commit
`7086a739da6f3c0f56788e211c78424a0cf65c22`.
The reference remains a research baseline, not a completed physics result.
This delivery is additive. It does not change the simulator, original raw data,
original README/STATUS, or production-gate configuration.

## 1. What was actually completed

The continuation computed **88 geometry states in 64 independently seeded
construction groups**, with **48,768 all-root censuses** and **2,389,632 exact
return-probability values**. There are 48 independently constructed primary
geometries, eight before/after intervention pairs, and eight construction seeds
paired across three sizes. The before/after states and cross-size states are
not counted as independent statistical samples. One additional deterministic
geometry calibrates the FEM clock and is separate from the 88 states.

The delivered evidence contains **94 verified stages and 594 numerical artifacts**,
including geometry files, diffusion arrays, root measurements, positive-length
barcodes for the census/size studies, prime-field comparisons, permutation nulls,
operator spectra, validation reports, and input/source hashes. These numbers
exclude documentation and regenerated figures. An additional collector produces
11 PNG/SVG figures and a concise report without selecting new hypotheses.

**601 scientific/compatibility tests passed**: 246 earlier mechanism tests,
224 selected existing continuation tests, and 131 new confirmation tests.
Separately, **14 installer-safety tests passed** on temporary real Git fixtures.
The new numerical namespace has **71.82% test-only statement coverage**.
Full research runs execute additional measurement/analysis paths outside that
coverage run; no 100% coverage or full-repository validation is claimed.

Twenty reference Python source files were reconstructed from saved packages
and connector reads and verified against their Git blob SHAs at the audited
commit. The selected compatibility tests use these pinned copies. They do not
silently substitute for running the original C++ simulator or the full repository
suite. No C++ build or physical simulation was executed in this continuation.

## 2. The principal scientific finding

The earlier exploratory persistence result was not simply accepted. The previous
measurement path sorted a random set of roots and then took its smallest labels
for persistence. That subset is not uniform. This continuation bypasses that path
and measures **every tetrahedral starting point** for its primary F2 analysis.
The legacy `cdt_mechanisms.study.measure_geometry` code is preserved as a historical
dependency; its old prefix-selection persistence path is not used by the new
confirmation runner. Do not use that legacy path for a claimed unbiased replication.

The earlier selected relation motivates one frozen primary hypothesis: the
all-root mean finite H1 total persistence at radius horizon 8 is negatively
associated with whole-geometry Ds at step 32. The protocol, new construction
seeds, source hashes, direction, endpoint, and statistical plan were fixed in
this session before the confirmation analysis. This is not an externally
registered preregistration and does not correct the older discovery study.

Sixteen new geometries form the training group; 32 further new geometries form
the confirmation group. Each has 96 vertices, 528 tetrahedra, four periodic time
slices, and a degree-four dual graph. All are constructed product triangulations,
not samples from a physical CDT Boltzmann ensemble. They have no reproduced
physical condensate/stalk distribution. The walk moves with probability 0.5;
these results must not be numerically conflated with the native baseline's
rho = 0.8 calculation.

### Frozen confirmation result

- Independent confirmation geometries: 32.
- Pearson r: **-0.375990111**.
- 95% geometry-bootstrap correlation interval: **[-0.664634, -0.036715]**.
- Prespecified one-sided geometry-permutation p: **0.0180**,
  using 9,999 permutations.
- Linear slope: **-0.028862657** Ds units per persistence unit;
  95% geometry-bootstrap interval **[-0.058708, -0.002651]**.

The association therefore replicates at a much more modest strength than the
previous selected eight-geometry exploratory result. Differences in roots,
geometry seeds, sample size, and selection all changed; the reduction in apparent
strength cannot be attributed solely to the sampling correction.

### The local controlled result has the opposite sign

Within each confirmation geometry, the analysis adjusts for log neighborhood
volumes at radii 4 and 8, a unit-equilateral curvature proxy, tetrahedron type,
time-slice position, and configuration fixed effects. Uncertainty is clustered
by the 32 independent construction geometries, not by the 16,896 roots.

The adjusted H1 persistence coefficient for local Ds32 is
**+0.010571075**, with interval
**[+0.006492, +0.014650]**.
Its within-family Holm p is 9.467356e-06.
A cluster-score sign-flip diagnostic gives p = 0.0005, under its stated approximate
sign-symmetry assumption. Root-label destruction is only a diagnostic negative
control, not a claim of spatial exchangeability.

An independent statsmodels fit with explicit configuration dummy variables
reproduces both the coefficient and its cluster standard error to within 1e-10.
This is an arithmetic cross-check, not validation of the causal assumptions.

**Interpretation:** persistence is a candidate geometry-level marker, not an
established universal local trapping mechanism. Whole-geometry Ds differentiates
an averaged return probability; local Ds differentiates each root's return.
These are different estimands. The sign reversal and remaining confounding mean
that neither coefficient can be promoted to an isolated topological causal effect.

## 3. Conductance and branching

The controlled radius-4 conductance coefficient for local Ds16 is
**+1.213170654**, with interval
**[+0.968857, +1.457485]** and within-family Holm p
4.732492e-11. Higher conductance means a weaker
bottleneck, so this direction is consistent with stronger bottlenecks accompanying
lower local Ds after the declared controls. It remains a constructed-ensemble
association, not a theorem about every finite-time local spectral dimension.

Five secondary spatial-neck descriptors were evaluated with a separate Holm
correction. Neck count has r = -0.783817;
entropy of separated-region sizes has r =
-0.801892.
Both have within-family Holm p = 0.0025. These are secondary findings and require
new replication rather than being relabeled as primary discoveries. Separated
regions can overlap: the size entropy is a graph/triangulation descriptor, not a
proved physical branching probability or a continuum branching dimension.

Existing exact wired edge-cut witnesses, Fiedler sweep cuts, annular components,
cycle statistics, and local radial conductance are reused. A sweep supplies a
cut witness, not an exact Cheeger constant. Spatial separating triangles are not
spacetime handles. The all-root persistence census is exhaustive; expensive wired
cuts and odd-field validation use explicitly uniform subsets.

## 4. Matching does not rescue a causal persistence claim

The high/low-persistence comparison has 10,416 eligible
roots and retains 732 pairs, or
**14.06%** of eligible roots. The largest
absolute post-match standardized covariate difference is
0.180943,
exceeding the declared 0.1 balance criterion. The balance screen therefore fails.

The high-minus-low matched difference is
-0.009584986, with interval
[-0.052814, +0.029846], across 31 matched geometry
clusters. This is inconclusive and applies only to the overlap subset. It must
not be presented as a population-wide causal result. Matching orientation is
covered by a known-effect regression test so high-minus-low cannot silently flip.

## 5. Scale matching

The confirmation scan evaluates radii 2, 3, 4, 6, 8 against steps 8, 12, 16, 24, 32.
The global max-statistic permutation p is **0.0005**. Individual-cell adjusted
p values and the entire 5-by-5 correlation matrix are saved.

This establishes associations in this scan, not the proposed scaling law.
Training selects the sequence of radii
**[6.0, 3.0, 3.0, 4.0, 4.0]**; the descriptive ridge exponent
is -0.161192, not a clean
positive square-root ridge. The held-out signed-correlation score has p = 0.0005,
but the measured-distance alignment error is
0.404155, versus
0.404909 for the square-root
benchmark. That tiny descriptive difference is not an independently significant
advantage and has no uncertainty-based scaling-law interpretation here.

Exact displacement distributions, RMS distance, mean distance, median distance,
and 90th-percentile distance are saved. The square root is a benchmark, not an
assumption imposed on CDT. No delta ~ c sqrt(sigma) result is established.

## 6. Persistence correctness and scope

F2 persistence is calculated for every one of the 48,768 roots across the three
executed studies. On independently uniform validation subsets, there are
**3,840 additional F3/F5 barcode comparisons**, with **zero disagreements** in
these constructed examples. There are **216 independent dimension-separated
boundary-rank checks**. Tests include odd-field orientations and an RP2 torsion
fixture that deliberately differs between characteristic 2 and odd fields.
Agreement on the measured examples does not prove field independence in general.

Finite lifetimes, counts, means, maxima, entropy, birth/death summaries, normalized
total persistence, observed persistence, and right-censored intervals are
separated. A right-censored interval at horizon 8 is not automatically a true
ambient essential class. Zero-length intervals are not treated as persistent
features. Positive-length barcodes for primary and size censuses are retained;
paired-study geometries and root summaries support exact regeneration.

These are barcodes of a genuinely nested union of tetrahedra selected by dual-hop
distance, including all faces. They are **not** the non-nested coarse-graining
fingerprint of the effective-topology papers, and they do not establish canonical
stratification or local-homology singularities of physical 3D CDT. The earlier
integral/coarse-graining modules and their selected tests were retained; the
paper-level 2D CDT/EDT reproduction and validated 3D effective-topology mapping
remain unfinished.

## 7. Valid interventions and actual geometric changes

Eight fresh construction seeds are compared before and after 240 valid spatial
edge flips. Every before/after geometry passes the pinned original validator:
valid tetrahedral incidence, neighbor relations, manifold links, spherical
spatial slices, and the declared foliation. Exact reversal restores the original
spatial complex. This is not arbitrary dual-graph rewiring.

The intervention preserves global topology, vertex count, tetrahedron count,
edge count, spatial volume profile, and degree-four dual regularity. It does not
hold all local geometry fixed. A separate executed geometric audit reports mean
changes of -0.272143 in edge-order SD,
+0.174852 in the root curvature proxy,
+3.289773 in radius-4 ball volume,
+17.126894 in radius-8 ball volume, and
-0.166921 in mean dual distance.
These changes are additional reasons not to call this isolated topology surgery.

The mean exact dual-walk Ds32 change is
**+0.112864295**, with paired
geometry-bootstrap interval **[+0.062814, +0.163571]**.
The mean neck-count change is -11.125.
One pair lowers dual Ds despite having fewer necks. The result is not a universal
monotonic law. No topology-changing triangulation move or physical-CDT matched
pair was produced in this continuation.

## 8. FEM comparison: explicitly unresolved

The code assembles the tetrahedral stiffness and consistent mass matrices and
solves K u = lambda M u. It does not rename another graph Laplacian as FEM.
Metric-preserving refinement is evaluated at 96, 720, and 5,664 vertices, with
528, 4,224, and 33,792 tetrahedra. The first two spectra are complete; the third
retains 256 low modes. Residuals, mass orthogonality, Galerkin identities, volume,
and low-mode Ritz monotonicity are checked. Complete-versus-truncated comparisons
are covered by tests.

A separate deterministic reference geometry fixes the time conversion before
interventions are compared. The median FEM-to-dual eigenvalue ratio is
115.411381; individual calibration ratios
range from 84.823 to 432.125.
This large spread is evidence against treating the conversion as a unique proved
physical clock. It is never fitted separately to make each intervention agree.

The mean refined FEM change is
**+0.012191928**, with paired
sampling interval **[-0.012785, +0.033115]**.
This interval crosses zero. It does not include every numerical/discretization
uncertainty. The separate finite-matrix omitted-spectrum bounds are conditional
on the computed ordered spectrum and are not continuum error certificates.

All eight pairs fail the last-refinement comparison screen at the locked endpoint.
The remaining refinement changes exceed the 0.05 tolerance. Thus the final
classification is **UNRESOLVED**, not cross-operator confirmation, and not a
proved continuum disagreement. There is no basis for selecting another window
post hoc solely to manufacture agreement.

## 9. Finite-size sensitivity

Eight further seeds are paired across 240, 528, and 1,104 tetrahedra. All roots
are measured at each size. The respective persistence–Ds32 correlations are
+0.070715, -0.427370, -0.298352.
Every 95% interval crosses zero. Mean Ds32 changes from
2.331207 to 2.587597 over the
grid. No finite-size scaling law or size-stable mechanism is established.

Every inspected root/time passes the declared return-above-stationary-floor
screen. This does not eliminate finite-volume effects: the observed size
sensitivity demonstrates why the floor screen alone is insufficient.

## 10. Physical readiness and the precise blocker

The container has the previous mechanism package and selected reference Python
files, but no mounted native physical geometries, native diagnostics/manifests,
built simulator, or complete original checkout. Direct cloning failed with
`Could not resolve host: github.com`. Connector reads supplied selected source
and repository metadata, not a usable binary archive. The Library search found
prior reports/packages, not the required physical dataset.

The new read-only native audit recognizes the original driver's CSV columns,
measurement phases, output hashes, geometry files, stages, and checkpoint/RNG
lineage. It refuses to equate an inherited checkpoint RNG with a fresh independent
seed. It checks observable/geometry consistency, acceptance counts, fixed k3 in
measurement, source validity, and unequal schedules rather than silently dropping
unmatched observations. It never infers live process status from a saved manifest.

Additional necessary-screen defaults are four independent chains, rank/folded
split Rhat <= 1.01, and bulk/tail ESS >= 400. These defaults were introduced in
this continuation and are not retroactively claimed to be the repository's old
preregistration. Historical two-chain diagnostic summaries were not recomputed.

The executed five-case diagnostic calibration uses synthetic arrays: independent
Gaussian chains pass; shifted, highly autocorrelated, identical, and constant
chains fail or are undefined. These arrays are clearly labeled **not CDT**.
The actual runtime physical audit reports **BLOCKED**, zero valid native jobs,
and no physical measurements. This is missing evidence, not a measured physical
failure to converge. Coupling effects, mediation, physical volume scaling,
condensate/stalk-conditioned results, and physical FEM checks are not computed.

## 11. Reproducibility and performance

Numerical stages are content addressed by configuration, input hashes, numerical
source hashes, and environment. Results are published only after successful
completion and hashing; partial temporary directories do not count as completed.
Concurrent stages use locks. Changed, extra, missing, and symlink artifacts are
rejected. The native audit also hashes its recomputed report into its identity,
so unchanged manifests cannot mask later corruption of a raw data file.

Measured first-study elapsed times on this container are approximately
110.88 seconds for the 48 primary geometries
with four workers, 91.41
seconds for the size grid with three workers, and
94.45 seconds for the final FEM/intervention
study with four workers. These exclude coding, development, reading, packaging,
and other tests; they are not estimates of physical-CDT compute time. The maximum
recorded primary-worker RSS is 148.47
MiB. Physical equilibration time and precision requirements cannot be inferred
from these small constructed fixtures.

Use `HANDOFF.md` for exact environment, test, verification, replay, read-only
physical-audit, review-branch installation, and push commands. The orchestrator
runs the selected tests, cached/fresh studies, analysis, calibration, figures,
and collected report. It deliberately does not launch a physical simulation.

## 12. Git status and research conclusion

Creation of review branch
`research/independent-mechanism-confirmation-20260909` was attempted and rejected
by GitHub with HTTP 403, `Resource not accessible by integration`. **No branch,
commit, push, or PR was created.** The additive installer verifies the bundle,
requires the correct origin and a clean named review branch descending from the
reference commit, and refuses differing existing files. It never stashes,
resets, commits, pushes, or modifies a production gate.

The strongest current constructed evidence supports a bottleneck association.
The persistence hypothesis survives weakly between geometries but not as a
universal negative local relationship. Poor matching overlap, finite-size
sensitivity, and unresolved FEM refinement materially restrict interpretation.
The physical CDT result remains open because the relevant ensemble measurements
have not been performed here. The computed null, reversal, and unresolved results
are retained rather than being replaced by the hoped-for pattern.

## Primary literature and method scope

1. Cooperman, *Scaling analyses of the spectral dimension in 3-dimensional
   causal dynamical triangulations*, arXiv:1711.02685. Reports coupling-dependent short-distance
   dimensional reduction and tentatively proposes a branched-polymeric
   explanation; it does not establish that mechanism.
   https://arxiv.org/abs/1711.02685
2. van der Duin, Loll, Schiffer and Silva, *Quantum Gravity and Effective Topology*,
   arXiv:2510.05695. Demonstrates coarse-graining fingerprints in 2D CDT/EDT;
   that is not the same construction as the nested tetrahedral-ball barcodes here.
   https://arxiv.org/html/2510.05695v1
3. van der Duin, Loll, Schiffer and Silva, *Exploring Quantum Spacetime with
   Topological Data Analysis*,
   arXiv:2510.05693. Relevant to the still-uncompleted effective-topology
   reproduction/mapping work; not evidence that this continuation has completed it.
   https://arxiv.org/html/2510.05693v1
4. Caceffo and Clemente, *Spectral Analysis of Causal Dynamical Triangulations
   via Finite Element Method*, arXiv:2010.07179. Motivates independent FEM and
   refinement rather than presuming agreement with the dual graph.
   https://arxiv.org/abs/2010.07179
5. Brunekreef, Görlich and Loll, *Simulating CDT quantum gravity*,
   arXiv:2310.16744. Reference for actual Monte Carlo simulation and triangulation
   mechanics; the constructed ensembles here are not a substitute for it.
   https://arxiv.org/html/2310.16744v1

No claim of literature-complete novelty, a new theorem, or a completed quantum-
gravity mechanism is made. All numerical claims above come from the delivered
selected run files, not from the literature or historical prose summaries.
