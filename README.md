# Topology-conditioned dimensional reduction in 2+1D CDT

Active computational research. Read STATUS.md before interpreting any outputs.
The manuscript is outside scope. Numerical success is not presumed.

Python 3.13 and an Apple Clang-compatible C++14 compiler are used.

```sh
python3 -m venv .venv
.venv/bin/pip install -r environment/requirements.lock
git submodule update --init --recursive
.venv/bin/python workflows/build.py
mkdir -p data/raw data/geometry logs results/manifests
MPLCONFIGDIR=build/mpl .venv/bin/python external/3d-cdt/3dcdt_gen_init.py 0 8 data/raw/initial_T8.dat
PYTHONPATH=src .venv/bin/python -m pytest -q tests
.venv/bin/python workflows/run_chain.py configs/reproduction/smoke.json
```

The research build applies documented corrections to a generated copy of
upstream source. It does not modify external/3d-cdt. The build manifest pins
the changed file hashes. The chain registry stores binary/input/output hashes,
parameters, seed, timestamps, commit and status, and skips verified completed jobs.
Failed same-binary jobs with a valid checkpoint can use the same command plus
`--resume`. Existing geometry files are compared, never replaced. Recovery
tests: `.venv/bin/python workflows/test_checkpoint.py`.

Source references: [simulation paper](https://arxiv.org/abs/2310.16744),
[spectral scaling](https://arxiv.org/abs/1711.02685),
[effective topology](https://arxiv.org/abs/2510.05695),
[canonical stratification](https://arxiv.org/abs/1808.06568).
