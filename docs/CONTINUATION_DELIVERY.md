# CDT topology continuation — executed implementation, unfinished physics

## Delivery status

This update is based on main commit
`d9ddb4ebe6f065013c2ad27ab055d4f6020f1c2e`. It extends the prior implementation;
it is not a replacement repository. The GitHub integration rejected branch
creation with HTTP 403, `Resource not accessible by integration`. No new branch,
commit, pull request or push was made on GitHub during this continuation.

The package installer verifies payloads, tested dependencies and existing file
hashes, refuses a dirty or conflicting checkout, applies the complete patch,
and by default commits only declared files as
`uskutsav-cpu <uskutsav@gmail.com>`. It never stashes, resets, force-pushes or
runs the simulator. `--push` explicitly requests a normal push through your
local Git credentials. `--no-commit` leaves reviewed changes uncommitted.

## Apply the downloaded package

Extract `cdt-topology-continuation.zip`. It contains a directory named
`cdt-topology-continuation` with `APPLY_UPDATE.py`, the patch, the payload and a
manifest. Open a terminal in your **existing repository root**, then run:

```sh
python3 ~/Downloads/cdt-topology-continuation/APPLY_UPDATE.py "$PWD" --dry-run
python3 ~/Downloads/cdt-topology-continuation/APPLY_UPDATE.py "$PWD"
```

The second command applies and commits locally; it does not push. A differing
file is a conflict to inspect, not permission for the installer to overwrite
it. Running this against an extracted source-only directory without Git is not
supported. No new raw simulation data or old running-chain manifest is changed.

## Run the tested scope

Keep the existing simulator environment separate:

```sh
python3 -m venv .venv-continuation
printf '*\n' > .venv-continuation/.gitignore
.venv-continuation/bin/python -m pip install -r environment/continuation-requirements.txt
.venv-continuation/bin/python workflows/test_continuation.py
.venv-continuation/bin/python workflows/run_continuation_study.py
```

The full synthetic study is already saved. A matching source/environment/
parameter combination verifies and reuses its artifacts instead of rerunning.
`--quick` runs a smaller smoke study. A changed environment produces a distinct
hash-addressed run. A partial/corrupt result is refused, not overwritten.

```sh
.venv-continuation/bin/python workflows/verify_continuation_results.py \
  results/continuation/072513df954dbb8b --check-source
```

The scoped test wrapper runs **224 tests**: the previous 102 and 122 new ones.
It does not claim to run the legacy C++ integration suite. The added CI
workflow is configured, but no hosted CI execution was possible because the
new code was not pushed.

## Implemented changes

Exact integer homology, torsion factors, relative local complexes and explicit
incidence chain maps now use Smith forms and mapping-cone certificates.
Recursive canonical labels have two independent backends, with exact incidence
audits. See `INTEGRAL_METHODS.md`.

An outcome-blind experimental microscopic carrier relation retains all touched
coarse cells and audits fine-piece provenance. It records ambiguous cells and
microscopic distance to the singular set. It is not a continuous-map certificate
or a physics-validated prescription. See `MICROSCOPIC_CARRIER_REVIEW.md`.

Shared full-graph probes now estimate all class-conditioned returns in batches.
A symmetric half-power identity supplies two times per propagation, while a
second Hutchinson backend independently checks the estimator. Probe-level
results, paired uncertainty, work/memory budgets, hashed caches and a gated
production CLI are included. See `STOCHASTIC_METHODS.md`.

Outcome-blind overlap matching, assumption-explicit stratified permutations,
configuration-grouped folds and hierarchical block/seed/probe uncertainty are
implemented and tested. These routines do not establish exchangeability,
equilibrium, a physical effect, or causality.

## Actual executed study

Saved run: `results/continuation/072513df954dbb8b/`. Its manifest verifies 49
artifacts. The run completed in approximately 15.4 seconds in the recorded
container; this is a measurement, not a prediction for other machines.

| Executed check | Observed result |
|---|---|
| Eight integral topology fixtures | Expected free ranks/torsion and local-link identities agree |
| 128 additional random complexes | Zero disagreements between stratification backends |
| Integral incidence-map audits | 316 accepted covering maps have acyclic cones |
| Every fixture simplex, relative vs link local homology | 911 agreements |
| 18 small T3 coarse constructions | Two identity-scale recoveries; all provenance audits succeeded |
| Nonempty conditioned comparison on those constructions | One; 17 contrasts undefined because a class is empty |
| Homogeneous grid null, exact A | -7.54951657e-16 |
| Engineered bottleneck positive control, exact A | 1.2382835273; synthetic graph only |
| 1,024-site grid benchmark, 64 times, 256 probes | 8x fewer vector-column operator applications; observed 3.38x runtime ratio |
| Benchmark max relative return error, sigma 3–12 | 0.778%; max empirical relative standard error 1.097% |
| Paired hierarchy null, 36 synthetic configurations in two chains | A=0 and interval [0,0] |

The runtime comparison is against the existing all-start reference propagator
in this container, not all optimized exact methods. Small-graph stochastic runs
were sometimes slower. Mean-return accuracy and Ds precision must be calibrated
on real geometries before production. A designed positive control is not a
quantum-gravity discovery; a toy null is not a null CDT physics result.

## Still required for the research result

All four default production gates remain NOT_ESTABLISHED. Complete the actual
ordinary-spectral finite-volume/coupling reproduction; reproduce the 2D CDT/EDT
effective-topology result; independently validate the 3D prescription and
microscopic mapping; freeze the primary scales/window/masks and uncertainty
plan; then execute production ensembles, defensible geometric/spatial controls,
and finite-size/coupling robustness. The new stochastic production command is
blocked until that evidence exists. Old saved chain diagnostics are not new
simulations and do not certify current process liveness.

No manuscript, experimental positive/null CDT conclusion, or percentage of
research completion is claimed.
