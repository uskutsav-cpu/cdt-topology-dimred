# Operational continuation state

The user's goal is ACTIVE and is the entire computational project in
`docs/PROJECT_BRIEF.txt`, not just the baseline. Do not mark it complete.
No manuscript. Never claim a gate passed without the numerical evidence.
Do not rerun completed experiments. Do not spawn agents (not authorized).

## Running work

- Current job: `4a40078dbf0e6b9a5f5c`.
- Config: `configs/reproduction/equilibration_10000.json`.
- Process was started through exec_command; session ID **79485**.
- Poll with write_stdin, bounded waits. Do not start it a second time.
- This is a full-state continuation of job `99188cc153094acfc0b4`, with
  20,000 dedicated burn sweeps, then 128 snapshots spaced by 200 sweeps.
  Each sweep is 100,000 attempted moves; k0=1, k3=1.1777799999999796,
  N3 target 10,000, T=64. Timeout 7,200 seconds.
- Checkpoints every 50 sweeps and after snapshots. Raw geometry is immutable.
- At last inspection it was at burn sweep 4,622, elapsed C++ time 351.8 sec.
  These are substantial computations: avoid filling the wait with redundant
  analyses or claiming that passing software tests completes the research.
- Job manifest remains running until independent geometry validation completes.

Workspace runtime: `/Users/swethasunilkumar/Documents/Codex/2026-09-07/do-t/work/venv/bin/python`.
Project root: `/Users/swethasunilkumar/Documents/Codex/2026-09-07/do-t/outputs/cdt-topology-dimred`.
Host has 8 GiB RAM / 8 logical CPUs. Prefer one large simulator process at a time.

## Completed work

- Pinned untouched upstream v1.0.1 (5720c0b98d809b35974d5c6fe067a828fe6b1267), builds.
- Explicit paper-grounded corrections in generated build; source untouched.
  See DECISIONS.md. Do not remove corrections to force a curve.
- Geometry import/export, closed-manifold validation, exact/walker/trace
  diffusion, derivatives, diagnostics, precision sampling, checkpoint recovery,
  completed-job extension, and checkpoint transfer to a new stage.
- 16 Python tests last passed; four move/inverse tests passed; low-level restart
  tests and cross-driver V1 checkpoint transfer preserve byte-identical output.
- Clean local clone `work/fresh-check` built and passed the then-current 12
  tests and restart tests. Later changes have targeted tests; don't repeat a
  full build without a reason.
- MATH.md, PHYSICS.md, DECISIONS.md, COMPUTE.md and REPRODUCTION.md exist.

### Actual jobs (all complete except current one)

- b3a0a98d4955072c7e32 and ba00c6fedfc34568c04a: deterministic debug replicas, 4 snapshots each.
- 6e6f2fe5d7f4709d8982: N~3,000 T16 pilot, 128 snapshots; ESS~6, fails screen.
- 341d14fabe08e6c5b531: first N~10,000 T64 chain, 128 snapshots;
  volume ESS~109 but peak-slice ESS~16. 717.7 seconds including validation.
- 99188cc153094acfc0b4: continuation, extended in place from 128 to 320
  snapshots WITHOUT rerunning prior steps; prior manifest .through_128.json.
  Total 16,000 candidate measurement sweeps, stride 50.
  N0 split-z=2.26, peak-slice ESS=14.84, peak-slice split-z=2.18: FAILS
  equilibrium screen. This motivated the new dedicated burn-in above.

### Measurements already saved — do not recompute

- Full-lattice pilot spectra in results/tables and figures.
- Eight-configuration stalk/boundary/rho sensitivity for 341d...:
  full-lattice Ds peak 2.407; condensate-start / excised peaks ~2.76–2.81.
  Different boundary conventions give similar curves. Fits saved explicitly.
- Precision pilot on three 9918... geometries: 320–384 starts needed to meet
  2% return SE over sigma 9..64. Selected 512 fixed starts subsequently.
- `workflows/measure_returns.py 99188cc153094acfc0b4 --total 320` COMPLETED:
  64 configurations (every fifth retained snapshot), 512 starts, sigma 0..256.
  All individual start-return curves saved. Maximum relative SE=0.017388.
  Aggregate Ds peak (sigma>=10)=2.78654. This is EXPLORATORY because the
  underlying chain failed equilibration. Block-4 bootstrap bands are diagnostic,
  not certified equilibrium confidence intervals.
- The precision pilot starts for configuration 0 were reused in this measurement.
- No novel topology-conditioned curves or effect sizes exist.

## Immediate next work

1. Let current burn-in/measurement job finish; inspect diagnostics and retained
   configurations. Use `workflows/summarize_registry.py` for actual job tables.
2. Examine slow observables and autocorrelation. Do not certify equilibrium from
   elapsed sweeps alone. Current screening uses ESS>=50, split-z<2, n>=50*tau.
3. For a sufficiently equilibrated ensemble, use incremental `measure_returns.py`
   and retain individual return curves. A completed job can extend samples with
   `--extend-job JOB` using a config differing ONLY by increased samples.
   Failed extensions resume with BOTH `--extend-job JOB --resume`.
   Ordinary failed jobs use the original config plus `--resume`.
4. Still required for the baseline gate: credible finite-size scaling at fixed T,
   rho scaling, coupling convention/phase scan, independent-chain/long-mode checks.
   N3000 T16 versus N10000 T64 is NOT a controlled finite-size comparison.
5. Only after the baseline gate: 2D effective-topology reproduction, then validated
   3D construction, canonical stratification, mapping, conditioned physics,
   confounders, bootstrap/permutation, size/coupling scaling and final package.
6. Keep RESULTS.md and STATUS.md factual. They lag the last extension and should
   be updated with the values above before the eventual final deliverable.

## Important implementation notes

- Geometry checks now group spatial faces once (faster than a scan per slice).
- Same-binary restart preserves pools/free lists, bag order and both RNGs.
- Stage transfer supports `initial_checkpoint` in config; inherited RNG state is
  explicitly recorded and the configured seed does not reset it. The V1 transfer
  from the old to current driver was tested with identical continuation snapshots.
- Config parameters/time are stage-local; parent lineage records prior evolution.
- Current code commit at last build: c26ec71. Subsequent data files may be untracked.
- Python source has no topology implementation yet: respect the user's gates.
- Literature PDFs/text and a rendered equation verification are in work/literature.
- PDF skill was read and its artifact-operation marker run successfully. Existing
  figures have been visually checked; render new final PDFs before delivery.
- Goal is not BLOCKED_COMPUTE merely because runs take time. Continue useful work
  and do not fabricate completion. No results-v1.0 tag has been made.
