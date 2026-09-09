# Topology-conditioned dimensional reduction in 2+1D CDT

Active computational research. Read STATUS.md before interpreting any outputs.
The manuscript is outside scope. Numerical success is not presumed.

Python 3.13 and an Apple Clang-compatible C++14 compiler are used for the
original simulation environment. Existing simulator setup:

```sh
python3 -m venv .venv
.venv/bin/pip install -r environment/requirements.lock
git submodule update --init --recursive
.venv/bin/python workflows/build.py
mkdir -p data/raw data/geometry logs results/manifests
MPLCONFIGDIR=build/mpl .venv/bin/python external/3d-cdt/3dcdt_gen_init.py 0 8 data/raw/initial_T8.dat
PYTHONPATH=src .venv/bin/python -m pytest -q tests
.venv/bin/python workflows/run_chain_safe.py configs/reproduction/smoke.json
```

The research build applies documented corrections to a generated copy of
upstream source. It does not modify external/3d-cdt. The build manifest pins
the changed file hashes. The chain registry stores binary/input/output hashes,
parameters, seed, timestamps, commit and status, and skips verified completed jobs.
Failed same-binary jobs with a valid checkpoint can use the same command plus
`--resume`. Existing geometry files are compared, never replaced. Recovery
tests: `.venv/bin/python workflows/test_checkpoint.py`.
The safe entry point delegates to the unchanged original driver, preserving
its job IDs. Its advisory locks apply to cooperating new launches, not already
running legacy processes.

## Newly implemented methods

Exact finite-field topology, connected Voronoi sampling, incidence-preserving
2D duals, an explicitly experimental 3D dual, fixed-operator conditioned
returns, paired chain-block uncertainty, and fail-closed measurement gates
are implemented and synthetic-tested. They do not constitute a completed
CDT/EDT reproduction or a topology-conditioned physics result.

```sh
.venv/bin/python workflows/validate_methods.py
.venv/bin/python workflows/audit_saved_state.py
```

The first command runs small synthetic checks with hash-verified output reuse.
The second reports saved evidence once without pretending to observe live jobs.
[Computational handoff](docs/COMPUTATIONAL_HANDOFF.md) contains the exact new
test command, schemas and continuation instructions.
[Methods and limits](docs/METHODS_IMPLEMENTED_2026-09-08.md) distinguishes
finite-field local homology from full integral canonical stratification and
records the unresolved 3D coarse-graining choices.

Source references: [simulation paper](https://arxiv.org/abs/2310.16744),
[spectral scaling](https://arxiv.org/abs/1711.02685),
[effective topology](https://arxiv.org/abs/2510.05695),
[canonical stratification](https://arxiv.org/abs/1808.06568).

## Integer topology and paired-diffusion continuation

The new [continuation handoff](docs/CONTINUATION_DELIVERY.md) includes exact
integer homology, recursive canonical labels with integral map audits,
an experimental microscopic carrier relation, paired half-power return
estimation, overlap controls, hierarchical uncertainty, and a saved synthetic
study. These additions do **not** establish the primary CDT physics result.

```sh
python3 -m venv .venv-continuation
.venv-continuation/bin/python -m pip install -r environment/continuation-requirements.txt
.venv-continuation/bin/python workflows/test_continuation.py
.venv-continuation/bin/python workflows/run_continuation_study.py
```

The test wrapper deliberately selects the continuation suite. The original
C++/geometry integration tests still require the original simulator build.
