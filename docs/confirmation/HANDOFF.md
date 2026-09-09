# Installation, verification, and continuation

## Start with the delivered evidence, without modifying your repository

Extract `cdt-confirmation-update.zip` so the folder contains `APPLY_UPDATE.py`,
`VERIFY_BUNDLE.py`, `BUNDLE_MANIFEST.json`, and `payload/`.

On a Mac, after extraction into Downloads:

```bash
cd "$HOME/Downloads/cdt-confirmation-update"
python3 VERIFY_BUNDLE.py
python3 -m venv .venv-confirmation
.venv-confirmation/bin/python -m pip install \
  -r payload/environment/confirmation-requirements.txt
.venv-confirmation/bin/python payload/workflows/run_confirmation_pipeline.py \
  --mode verify
```

The environment is outside `payload/` so it does not contaminate the distributed
payload manifest. `--mode verify` checks the 94 selected evidence stages and then
runs 601 selected scientific/compatibility tests. It does not run the original
C++ suite, launch a simulation, or claim a physical result. The pinned legacy
Python compatibility fixture is checked against 20 Git blob SHAs before use.
`--without-baseline` on `test_confirmation.py` selects the 377 mechanism and new
confirmation tests only.

The tested Python version is 3.13.5. Exact tested package versions are in
`payload/environment/confirmation-tested.json`. A fresh environment is preferred
to replacing packages in your simulation environment. The manifest verifies
saved output bytes regardless of environment; recomputation identities also
include the numerical environment. Different versions may produce new stage IDs.

## Replay all constructed studies and generate a new collected report

```bash
cd "$HOME/Downloads/cdt-confirmation-update"
.venv-confirmation/bin/python payload/workflows/run_confirmation_pipeline.py \
  --mode synthetic --workers 2 --output-root "$PWD/reproduced-results"
```

The pipeline runs the selected tests, all-root measurement, primary/secondary
analysis, finite-size sensitivity, the paired FEM study, synthetic diagnostic
calibration, 11 figures, and an atomic collected report. It prints the report
path. This is an end-to-end **constructed-study** workflow, not an automated
physical-CDT completion claim. Completed stages with matching inputs, sources,
and environment are verified and reused. A changed locked census protocol is
refused rather than silently mixed with old measurements; use a fresh output
root for a changed design/environment.

Four workers were used for the main and FEM studies here. Two is the conservative
provided default. Every worker limits numerical-library threads to one. The
small-fixture timings are not estimates of physical simulation time.

To regenerate only the supplied figures, without changing any archived artifact:

```bash
.venv-confirmation/bin/python payload/workflows/plot_confirmation.py \
  --output "$PWD/regenerated-figures"
```

Individual commands, run with the bundle's environment, are:

```bash
.venv-confirmation/bin/python payload/workflows/run_confirmation.py \
  --output "$PWD/reproduced-results/census" --workers 2
.venv-confirmation/bin/python payload/workflows/run_confirmation.py \
  --output "$PWD/reproduced-results/census" --analyze
.venv-confirmation/bin/python payload/workflows/run_size_confirmation.py \
  --output "$PWD/reproduced-results/finite_size" --workers 2
.venv-confirmation/bin/python payload/workflows/run_operator_confirmation.py \
  --output "$PWD/reproduced-results/operators_final" --workers 2
.venv-confirmation/bin/python payload/workflows/run_diagnostic_calibration.py \
  --output "$PWD/reproduced-results/diagnostic_calibration"
.venv-confirmation/bin/python payload/workflows/collect_confirmation_results.py \
  --run-root "$PWD/reproduced-results" --output "$PWD/reproduced-results/reports"
```

The collector refuses an ambiguous or source-stale result selection. It does not
choose the most favorable statistical result. Standard output records the exact
completed stage path. The primary original selection is pinned separately in
`payload/docs/confirmation/FINAL_RUNS.json`.

## Physical data: use the native clone, not a fresh code-only clone

The physical readiness audit is read-only. It expects the original repository,
native completed-job manifests, `data/raw/<job>/diagnostics.csv`, the hashed
geometry files, and original build/gate records. A fresh Git clone normally lacks
the ignored raw dataset. The archive's constructed geometries cannot replace it.

Your previously used native repository path can be audited with:

```bash
cd "$HOME/Downloads/cdt-confirmation-update"
NATIVE_REPO="$HOME/Documents/Codex/2026-09-07/do-t/outputs/cdt-topology-dimred"
.venv-confirmation/bin/python payload/workflows/audit_physical_confirmation.py \
  --repo "$NATIVE_REPO" --output "$PWD/physical-readiness"
```

The script checks that path and its required files rather than assuming they
exist. Point `NATIVE_REPO` to the actual native-data clone when your local path
has changed. Exit code 2 means blocked or not ready; the accompanying JSON gives
missing files, provenance failures, and observable-specific screens. It is not
an invitation to mark gates PASS. A saved running manifest is not evidence that
its process is currently alive.

The native audit checks actual original output names and stage metadata, not a
fictional replacement format. Independent-chain comparisons reject inherited
checkpoint RNG lineages and unequal saved schedules. New diagnostic defaults
are documented as additional necessary screens, not the repository's historical
preregistration. No existing completed run or raw geometry is overwritten.

Physical continuation still uses the original build and safe chain runner on
the native clone, after its inputs and branch/worktree are reviewed:

```bash
# These are the existing native entry points, not replacements supplied here.
python3 workflows/build.py
python3 workflows/run_chain_safe.py configs/reproduction/independent_10000.json --dry-run
```

A physical production run, fresh independent chain design, equilibration,
ordinary spectral reproduction, coupling/volume analysis, and converged FEM
comparison remain separate unfinished work. This delivery does not auto-launch
those expensive jobs or pretend its small constructed studies satisfy them.

## Install the code on a review branch

The audited base is `7086a739da6f3c0f56788e211c78424a0cf65c22` in
`uskutsav-cpu/cdt-topology-dimred`. A review-branch write was attempted through the
connector and failed with HTTP403. Nothing was pushed.

Use a clean review clone, not the directory containing active simulations:

```bash
cd "$HOME/Downloads"
git clone --recurse-submodules \
  https://github.com/uskutsav-cpu/cdt-topology-dimred.git cdt-confirmation-review
cd cdt-confirmation-review
git switch -c research/independent-mechanism-confirmation-20260909

python3 "$HOME/Downloads/cdt-confirmation-update/APPLY_UPDATE.py" \
  "$PWD" --dry-run --code-only
python3 "$HOME/Downloads/cdt-confirmation-update/APPLY_UPDATE.py" \
  "$PWD" --code-only
```

`--code-only` omits `results/` from installation to avoid putting roughly 200MB
of raw measurement artifacts into Git by default. Code, tests, reports, plotted
figures, compact computed summaries, and the pinned compatibility fixture are
still installed. The complete numerical evidence remains in the download.
Omit `--code-only` for a local full-evidence installation. Do not rerun the
installer on a dirty branch: inspect and commit your own changes explicitly.

The installer verifies all payload hashes, checks the exact repository origin
and ancestor commit, refuses `main`, `master`, detached HEAD, dirty worktrees,
symlink destinations and different existing files. Identical prerequisites are
preserved. It creates files exclusively and rolls back only files it created on
a copy failure. It does not reset, stash, create a branch, commit, or push.

After reviewing the installed changes:

```bash
git status --short
git diff --stat

git add src/cdt_confirmation src/cdt_mechanisms \
  tests/confirmation tests/mechanisms configs/confirmation docs/confirmation \
  validation/confirmation environment/confirmation-requirements.txt \
  environment/confirmation-tested.json \
  workflows/*confirmation*.py workflows/run_diagnostic_calibration.py \
  workflows/apply_mechanisms_update.py workflows/analyze_mechanism_secondary.py

git commit -m "Add independently tested all-root CDT mechanism confirmation"
git push -u origin research/independent-mechanism-confirmation-20260909
```

The installed `test_confirmation.py` tests the pinned reference compatibility
fixture, not arbitrary newer core changes. Full original-repository testing must
still be done after its actual simulator build, in addition to these 601 tests.
No raw or production-gate paths are selected by the code-only commit command.

## Important interpretation warnings

The new runner measures all roots. The historical prefix-selection persistence
path inside the reused `cdt_mechanisms.study.measure_geometry` is not used here
and should not be treated as uniformly sampled. The old top-level mechanism
runner is not included as this continuation's entry point. Two unchanged legacy
workflow files, `apply_mechanisms_update.py` and `analyze_mechanism_secondary.py`,
are retained because the existing mechanism tests import them. They are test
compatibility dependencies, not the installer or primary workflow for this
archive. Use the archive-level `APPLY_UPDATE.py` shown above.

These studies preserve global topology and alter local geometry. “Independent
chains” in a reused statistical result field means independently seeded geometry
clusters **for these constructed results**, not physical Markov chains.
Persistent-ball holes are not automatically ambient topology changes or canonical
local-homology singularities. Reported FEM confidence intervals and finite-matrix
spectral-tail bounds represent different uncertainty sources; neither establishes
a continuum limit.

See `RESEARCH_REPORT.md` for the actual findings and `PHASE_LEDGER.md` for all
18 requested phases, including every uncompleted physical requirement.
