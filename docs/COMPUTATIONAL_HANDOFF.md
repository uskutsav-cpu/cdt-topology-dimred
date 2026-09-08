# Computational handoff — tested methods, unfinished research

## Read first

`STATUS.md` gives current saved evidence. `RESULTS.md` preserves the earlier
numerical history. `docs/METHODS_IMPLEMENTED_2026-09-08.md` defines the new
algorithms and their limits. No manuscript was written.

The remote snapshot's running manifests are historical records, not proof of
live workers. This environment did not access the Mac's processes or binary
checkpoints. Do not restart or duplicate those jobs from a stale session ID.

## Test and validate the new modules

Use the project's installed Python environment, from the repository root:

```sh
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/test_topology_foundations.py tests/test_coarsegrain_foundations.py \
  tests/test_conditioned_analysis.py tests/test_runtime_foundations.py \
  tests/test_conditioned_workflow.py
.venv/bin/python workflows/validate_methods.py
```

The second command runs only small synthetic computations. Completed outputs
are source/parameter hashed and reused after verification. Its success means
SYNTHETIC_CHECKS_PASS_NOT_REPRODUCTION_PASS. It does not need the C++ simulator
or old raw data. The full historical suite still requires the original build
and geometry fixtures; the 102-test claim is specifically the new suite.

## One-shot progress instead of repeated token-consuming polling

```sh
.venv/bin/python workflows/audit_saved_state.py
.venv/bin/python workflows/audit_saved_state.py \
  --only-changes results/methods/last_saved_state.json
```

Identical saved evidence is silent with `--only-changes`. Neither command
starts a polling loop or claims to observe live processes. The longest saved
matched-chain comparison is selected even when it fails; an older passing
record is not substituted. This audit does not revalidate the raw geometries.

## Continue original chains without changing their IDs

For future invocations use the advisory single-writer wrapper:

```sh
.venv/bin/python workflows/run_chain_safe.py CONFIG.json --dry-run
.venv/bin/python workflows/run_chain_safe.py CONFIG.json
.venv/bin/python workflows/run_chain_safe.py CONFIG.json --extend-job EXISTING_JOB_ID
.venv/bin/python workflows/run_chain_safe.py CONFIG.json --extend-job EXISTING_JOB_ID --resume
```

Replace CONFIG.json and EXISTING_JOB_ID with a verified existing config/job.
Resume only a failed job with the original matching binary/checkpoint.
The wrapper hashes and calls the unchanged original `run_chain.py`, preserving
old IDs, cache semantics, and checkpoint contracts. It does not rebuild or
change simulator physics. POSIX file locks support the intended macOS/Linux
hosts, and are released by the OS after a crash. All cooperating new launchers
must use the wrapper; it cannot retroactively lock a legacy process already
running through the old entry point. Verify those processes before launching.

## Conditioned measurement interface (blocked by default)

The geometry NPZ uses the existing exporter format with integer `neighbors`
of shape N x 4. A separate mapped-label NPZ must contain:

- boolean `regular` and `singular` arrays of length N;
- optional boolean `start_mask` defining the population, otherwise all N sites;
- scalar `geometry_sha256` equal to the geometry NPZ's exact SHA256;
- nonempty scalar `mapping_definition` describing how the labels were obtained.

Both classes must be nonempty, disjoint, and partition the start population.
This update supplies no scientifically validated 3D-to-microscopic label map.

```sh
.venv/bin/python workflows/measure_conditioned.py GEOMETRY.npz LABELS.npz \
  --steps 256 --block-size 32 --output results/conditioned/MEASUREMENT.npz
```

This intentionally fails until all four gates in
`configs/methods/production_gates.json` have real validated evidence. Each gate
needs `status: PASS` and a nonempty `evidence` list of objects with `path` and
`sha256`; evidence must be inside this repository and match its recorded hash.
Do not promote a synthetic fixture to scientific gate evidence. A work cap of
500,000,000 estimated scalar updates prevents an accidental unbounded exact
all-site run. Profile a scalable, precision-validated estimator for larger data.

## Remaining scientific order

1. Complete the finite-volume/coupling reproduction and precision diagnostics
   on the actual long-chain outputs; retain the distinction between diagnostic
   screens and demonstrated equilibrium. The N10000 matched screens have
   passed, but they do not automatically open the full reproduction gate.
2. Use the 2D implementation for a real CDT/EDT effective-topology reproduction,
   checking the author's sampling/tie conventions and Betti curves.
3. Validate or replace the experimental 3D prescription, especially collapsed
   noncontractible interfaces/junctions; complete the required local-homology
   incidence-map/canonical-stratification machinery.
4. Define and validate microscopic preimages independently of return data.
5. Freeze masks, coarse scales, diffusion window, estimand, and block lengths;
   then run gated conditioned measurements, matched geometric controls and
   appropriate nulls, finite-size/coupling robustness, and uncertainty analysis.

Parallel synthetic software work is allowed without claiming new CDT physics.
No percentage of total research completion is inferred from passing tests.
