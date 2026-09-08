# Operational continuation state

## Current handles — supersede older running-work entries below

- 13823: job4a40078dbf0e6b9a5f5c extension384→768 samples, config
  equilibration_10000_768.json. Prior session60619 finished successfully.
- 90274: job8b3e5e63ecacfa361207 extension384→768 samples, config
  independent_10000_768.json. Prior session19336 finished successfully.
- 28894: jobd614ea076af1a31a8018 N30000 long-spacing continuation.
  Prior session43971 finished and all128 geometries validated.
- 45527: job590bcc4ae5515ad24761, k0=.5 N30000 baseline comparison.
  Spectral analysis47098 finished successfully.
- No analysis is running. Four single-thread simulators occupy the prior
  three-simulator-plus-analysis slots. Never duplicate live jobs.


The user's goal is ACTIVE and is the entire computational project in
`docs/PROJECT_BRIEF.txt`, not just the baseline. Do not mark it complete.
No manuscript. Never claim a gate passed without the numerical evidence.
Do not rerun completed experiments. Do not spawn agents (not authorized).

## Running work

- Current job: `4a40078dbf0e6b9a5f5c`.
- Config: `configs/reproduction/equilibration_10000.json`.
- Process was started through exec_command; session ID **60619** (extension; original79485 finished).
- Poll with write_stdin, bounded waits. Do not start it a second time.
- This is a full-state continuation of job `99188cc153094acfc0b4`, with
  20,000 dedicated burn sweeps, then 128 snapshots spaced by 200 sweeps.
  Each sweep is 100,000 attempted moves; k0=1, k3=1.1777799999999796,
  N3 target 10,000, T=64. Timeout 7,200 seconds.
- Checkpoints every 50 sweeps and after snapshots. Raw geometry is immutable.
- The first 128 snapshots are complete and validated (1,974.71 sec total).
  These are substantial computations: avoid filling the wait with redundant
  analyses or claiming that passing software tests completes the research.
- Job manifest remains running until independent geometry validation completes.

Workspace runtime: `/Users/swethasunilkumar/Documents/Codex/2026-09-07/do-t/work/venv/bin/python`.
Project root: `/Users/swethasunilkumar/Documents/Codex/2026-09-07/do-t/outputs/cdt-topology-dimred`.
Host has8GiB RAM/8logical CPUs. Measured resident simulator memory permits
two independent simulators plus one analysis; see COMPUTE.md.

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

### Exact UV precision work completed

- Commit a153c8f adds `src/spectral_exact_short.py`, three targeted passing
  tests, and benchmark/variance workflows. Prior sixteen tests passed earlier.
- Eight cached exact all-site return arrays through sigma=26 exist for 9918...
  indices 0,5,50,100,150,200,250,300. Do not repeat these propagations.
- `precision_variance.py` finished successfully (session42561, exit0).
  Sampling variance at512 starts / exact between-geometry variance is
  6.67,3.84,3.57,3.35,3.22 at sigma9,15,17,20,25 respectively. Nonstationary pilot.
- Sparse half-power identity gives two times per multiplication, about5sec per
  geometry through26. Selected row batches keep the full microscopic operator.
- RESULTS/MATH/COMPUTE updated with this evidence. No UV physics window frozen.

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

## Latest completed diagnostic and continuation decision

Stage 4a40078dbf0e6b9a5f5c completed its 20,000 burn +25,600 measurement
sweeps. All128 retained geometries validated. Total1,974.713sec.
N0 ESS1826.35 z0.476; N3 ESS1509.36 z0.679; peak-slice ESS18.271,
tau700.56 sweeps, split-z0.873. Insufficient effective samples; gate remains
closed. Immutable diagnostic: results/tables/4a40078dbf0e6b9a5f5c_through128_diagnostics.json.

Started same-job extension with configs/reproduction/equilibration_10000_384.json
and --extend-job 4a40078dbf0e6b9a5f5c. No new tuning or burn, no old sweeps repeated.
It requests384 total saved configurations (76,800 total measurement sweeps).
The128-snapshot manifest is preserved as .through_128.json. Resume a FAILED
extension with the same config, --extend-job and --resume, not while running.
The target follows observed slow-mode ESS, not any conditioned spectral result.

Live extension session60619; do not restart.

Live baseline measurement session9243:
`workflows/measure_returns.py 4a40078dbf0e6b9a5f5c --total 128 --stride 4`.
32 saved geometries,512 starts,256 steps, immutable per-configuration cache.
Runs concurrently with extension. Do not duplicate it. Final aggregate remains
exploratory until equilibrium and sampling uncertainties are established.
Future extension measurements reuse these indices by keeping stride4.

## Latest baseline measurement / fixed comparison design

Session9243 completed:32 configurations (indices0,4,...124),512 starts,256
steps. Ds peak2.79319873; maximum relative return sampling SE0.01678961.
No equilibrium claim. These per-start arrays are immutable and reused later.

Session4647 is LIVE: `workflows/measure_exact_uv.py 4a40078dbf0e6b9a5f5c
--total 128 --stride 4`. It computes ALL-site returns through26 on those32
geometries, crosschecks all512 saved basis starts, and saves exact UV curves
plus finite-population corrected sampling variance comparison. Source-hashed
per-geometry caches; no stochastic uncertainty from start sampling remains.
Poll session4647; do not duplicate it. Extension60619 is also still live.

`configs/reproduction/baseline_design.json` fixes upcoming independent10k,
volumes30k/60k atT64, and k0=.5,1,1.5,2,2.5 atN30000. Seven executable configs
are prepared, NOT RUN. Fresh random streams, common saved starting geometry,
2000 tune +20000 burn +128 stride200 measurements initially; must diagnose
and extend appropriately, check independent-chain convergence. k3 guesses
are explicitly heuristic, then retuned. No inherited RNG checkpoints for
these independent chains. Do not claim the unrun design is reproduction.
Next simulator after60619 should address any remaining same-chain problem,
or begin independent_10000.json if diagnostics permit the comparison.

## Latest authoritative sessions

-60619: extension4a40078dbf0e6b9a5f5c still running.
-55518: NEW independent job8b3e5e63ecacfa361207, configindependent_10000.json,
 fresh RNG, running concurrently. Neither chain should be restarted.
-4647: FINISHED exit0.32 exact all-site UV geometries through26, all crosschecked
 against512 saved starts. Noise/exact between-geometry variance=4.922,3.352,
 3.072,2.771,2.456 at sigma9,15,17,20,25. No equilibrium claim.
-Added rank_split_rhat to diagnostics.py and two tests. It follows primarypaper
 normal-score denominatorS+1/4, not currentStan manual typoS-1/4. Tests invoked
 with PYTHONPATH=src (initial invocation without it failed collection only).
 Do not use lowESSRhat as convergence proof. New independentchain not complete.
-Memory query allowed via escalated read-onlyps: simulatorRSS~2.6MiB, driver14MiB,
 exactUVanalysis~845MiB. Earlier sequential-only rule was conservative; changed
 based on evidence to two independent simulators. No subagents were spawned.

## Latest efficient rho comparison

Added spectral_thinning.py: M_new=(1-q)I+qM_old gives binomial mixture of saved
returns for q=rho_new/rho_old<=1. Truncation error bounded by omitted binomial
mass, never silently renormalized. New direct-propagation/error-bound test
passed (PYTHONPATH=src pytest tests/test_thinning.py).

`rho_from_saved.py 4a40078dbf0e6b9a5f5c --total128 --stride4` completed in<1sec
using all32 cached start-mean curves. rho=.2,.4,.6,.8 peaks2.82296,2.81274,
2.80283,2.79320 and scaled peak times62.2,63.6,64.8,66.4. Tailbound1.81e-34.
CSV/NPZ/JSON saved with input hashes. No repeated sparse propagation. Original
curve caches remain unchanged. This is exploratory; baseline gate stays closed.
Simulation sessions60619 and55518 were both revalidated live this turn.

## Third simulator launched after analysis finished

Session43971: jobdc0bd0d263f25696be2d, volume_30000.json, fresh RNG,
N30000/T64/k0=1. Tuning reachedN3=29732 at sweep1359 (elapsed76.27sec).
Handle revalidated live. Do not restart.
Sessions60619 and55518 also revalidated live this turn. Exact UV analysis
has finished; its compute slot is now used for this third simulator. Three
single-thread simulators, no heavy analysis currently running. This extends
the initial two-simulator cap using the now-free analysis slot and the earlier
measured low simulator resident memory. Do not add more jobs without checking
resource use and the scientific need. Finite-size outputs are not yet available.

## Saved-data figure completed

`plot_saved_baseline.py 4a40078dbf0e6b9a5f5c` renders exact vs sampled UV Ds
and rho-scaled curves using saved tables only. PDF and PNG saved under
results/figures/4a40078dbf0e6b9a5f5c_precision_and_rho.*. PDF rendered through
pdftoppm and visually checked: readable labels, no clipping; explicitly
marked equilibrium not certified. Exact/sample ensemble means are close even
though per-geometry start-sampling variance exceeded physical variation.
Bothfacts are compatible. Visible parity artifacts occur at the first few
steps; no production UV cutoff has been chosen from topology labels.
All three simulation handles60619,55518,43971 verified live this turn.

## Cross-chain workflow ready

`workflows/compare_chains.py JOB1 JOB2` refuses running jobs, compares common
post-burn prefixes, reports rank/folded split Rhat, per-split single-chain ESS,
full-chain summaries and RNG lineage. Input-hashed JSON avoids overwriting a
comparison with different chain data. Syntax checked; numerical Rhat tests
already passed. Apply to4a400... and8b3e... only after both complete. This is
not an automatic convergence gate; time extent/RNG independence must agree.
Independent job8b3e... has entered measurements (sweep22362, elapsed974.29sec)
after2000 tune +20000 burn. Session55518 revalidated live. Other sessions
60619 and43971 also remain active as last checked this turn.

## Completed convergence comparison and next extensions

4a400... through384: all384 geometries validate, 76,800 measurement sweeps;
N0 ESS5660.87 z0.478, N3 ESS4626.33 z0.174, peak_slice ESS29.074,
tau1320.785, z1.036. Extension took2511.716sec incl validation. Original128
stage was1974.713sec, so same-stage total4486.429sec. Gate still fails.

8b3e... through128: all128 geometries validate, total2228.804sec;
N0 ESS2139.80 z0.602, N3 ESS1735.77 z1.516, peak_slice ESS21.522,
tau594.727, z0.568. Gate still fails. Both are T64,k0=1,target10000,
same driver, distinct RNG origins; frozen k3 differs slightly after tuning
(1.17778 vs1.17798), mean N3 agrees within diagnostic uncertainty.

compare_chains.py completed on both before extensions. Common first25,600
measurement sweeps: rank/folded splitRhat N0=1.000159,N3=1.000515,
peak_slice=1.019292; minimum split peakESS9.176. Saved input-hashed JSON
under results/tables/chain_comparison_*.json. Rhat1.019>1.01 and lowESS,
so no convergence certification. Do not mistake agreement in mean counts
for agreement in slow profile fluctuations.

Started extensions from exact checkpoints:4a400... to768 total snapshots,
8b3e... to384. No tuning,burn,old sweeps,or exports repeated. Previous complete
manifests preserved as4a400...through_384.json and8b3e...through_128.json.
New live handles13823 and19336. Resume only if genuinely failed using both
--extend-job JOB and --resume with the matching new config. N30000 session
43971 remains live. Goal remains active, not blocked or complete.

## Independent spectral comparison started

Three simulators revalidated live:13823,19336,43971. Latest main stage sweep
98228, independent49019, larger35134; checkpoints continue advancing.
Started `measure_returns.py 8b3e5e63ecacfa361207 --total128 --stride4` on the
already validated first128 independent geometries. It measures32 geometries,
512 fixed starts,256 steps; all per-start returns cached and reusable. This
is a moderate dense propagation workload (~40MiB per state array), not the
~845MiB all-site sparse-power analysis. It may run alongside three lightweight
simulators; do not start another analysis simultaneously. No equilibrium claim.

Independent return-measurement live session:94006. Poll; do not duplicate.

## Independent spectra completed

Session94006 finished successfully.32 independent geometries,512 starts,
sigma0..256. PeakDs2.7979867, maxrelative returnSE0.01959395. Saved all
per-start arrays. rho_from_saved.py also completed on this chain without
new propagation:rho=.2,.4,.6,.8 peaks2.82734,2.81728,2.80751,2.79799,
rescaled peaks63.0,64.4,65.4,66.4.

Descriptive first32-vs-first32 chain spectrum comparison saved as
independent_baseline_spectral_comparison.csv/json, reproducible through
compare_saved_spectra.py JOB1 JOB2. Over sigma9..64 max|Ds difference|=.005557,
maxrelative P difference=.002536. This numerical agreement does not override
the failed slow-mode convergence diagnostics. Main/independent extensions
13823/19336 andN30000 session43971 remain live; no analysis remains running.

## Completed N30000 pilot and efficient continuation

Jobdc0bd0d263f25696be2d finished, all128 exports validated, total3036.592sec
(C++2653.844sec). MeanN3=30021.215, ESS1782.86,z0.231; N0ESS1340.25,z0.080.
Peak_slice mean697.511, SD90.531, tau2953.656sweeps, ESS4.334,z1.771.
The short record fails both effective-sample and chain-length screens. Slow
shape fluctuations, not volume counts, remain the issue. Saved through128
diagnostics JSON. Do not certify equilibrium.

Started new stage d614ea076af1a31a8018, session28894,
configvolume_30000_long.json. EXACT checkpoint continuation, no tuning or
burn repeated, frozenk3=1.1761599999999985, samples128,stride2400, attempts100k,
307,200 new sweeps, timeout28800sec. Predicted ESS~52 if measured tau persists;
this is a schedule estimate, not evidence. Twelvefold fewer saved/validated
geometries than stride200 for the same simulation effort. Old candidate
measurements remain retained; do not relabel them post hoc as burn-in. Include
lineage and check long-mode consistency when assessing the combined trajectory.
When measuring this future long-spaced stage, avoid default stride4 thinning
without statistical justification; all128 snapshots may be useful.

Started baseline measurement47098:
measure_returns.py dc0bd0d263f25696be2d --total128 --stride8
(16 geometries,512 starts,256steps; per-start curves cached). No equilibrium
claim; this provides first controlled volume comparison atfixedT64,k0=1.
13823 and19336 continue in parallel. No other process should be restarted.

## First controlled finite-volume spectrum completed

47098 finished:16 N30000 geometries,512 starts,256steps. PeakDs2.9435603,
maxrelative samplingSE0.0174189. Per-start curves saved. Compared with32
N10000 geometries atsameT64,k0=1,rho=.8: measured condensate volumes9002.375
and29126.563; peakDs2.79320 and2.94356 at sigma83 and129. Ds15=2.52228 and
2.53403; Ds25=2.62842 and2.64883. This is qualitative finite-volume evidence,
not asymptotic scaling or a convergence/reproduction pass.

finite_size_pilot.py creates source-hashed tables and PDF/PNG from saved
returns only. Rendered PDF throughpdftoppm and visually checked: no clipping,
legible labels, explicitlypilot/convergencepending. Outputs committed.

Freed analysis slot assigned to fourth single-thread simulator:
job590bcc4ae5515ad24761,session45527,configcoupling_0p5_30000.json.
Predeclaredk0=.5, N30000,T64 comparison withfresh RNG. Three others remain
13823,19336,28894. No heavy analysis currentlyrunning; do not add another
CPU-intensive job without a completion or resource check. All base comparisons
remain gated on proper diagnostics. Novel topology work has not begun.

## Completed-stage comparison during extensions

compare_chains.py now accepts archived stage identifiers such as
4a40078dbf0e6b9a5f5c.through_384. It reads the original diagnostic prefix,
verifies its SHA256 against that completed manifest, and refuses two revisions
of the same physical chain as independent inputs. Running current manifests
are still rejected. This allows comparing completed stages while later
continuations run, without stopping them.

Validated against the archived4a400...through384 and8b3e...through128:
exact diagnostic hashes verified and ALL numeric diagnostics match the prior
completed-stage calculation. No simulation or diffusion was repeated.
When19336 finishes its384 stage while13823 still runs, compare
4a40078dbf0e6b9a5f5c.through_384 with8b3e5e63ecacfa361207 immediately.
Four simulators13823,19336,28894,45527 were revalidated live this turn.

## Independent384 completed; cross-chain issue persists

Session19336 finished, all384 geometries validate; extension2795.833sec.
First128 stage2228.804sec, total5024.637sec. Measurement length76,800sweeps.
N0 ESS6624.03,z0.231; N3 ESS5257.20,z0.984; peak_slice ESS52.729,
tau728.248,z1.447. This is the first chain passing all existing single-chain
screens. It is not a multi-chain or physics reproduction pass.

Compared4a400...through384 with8b3e...through384 (while4a400 extension stayed
live). Exact completed-prefix hashes verified. Over76,800 common sweeps,
peak_slice rank/folded splitRhat1.033155 and minimum splitESS13.492. N0/N3
Rhat~1.0000. Thus slow-mode multi-chain convergence remains unestablished.
Saved input-hashed comparison JSON. Do not claim convergence from scalar
count agreement or matching spectral peaks.

Started8b3e... extensionto768 total samples, configindependent_10000_768.json,
NEW session90274. No previous MC sweeps/tuning/burn/exports repeated.
Previous manifest preserved as8b3e...through_384.json. Other live handles
13823(main10kto768),28894(longN30000),45527(k0=.5N30000).
No analysis running. Next available physics baseline work includes completing
k0 grid andN60000 once a slot frees, while resolving convergence honestly.

## Main768 MC complete; validation and broader spectra running

Main4a400... C++ reached173600 final stage sweep:153600 measurement sweeps.
N0 ESS12021.66,z1.032; N3 ESS9286.96,z0.369; peak_slice ESS73.009,
tau1051.928,z0.481. ALL single-chain screens pass. Saved through768 diagnostic
JSON. Geometry validation remains under session13823; at last inspection488
of768 exports exist. Do not mark that session complete until exit0.

Started session32940:
measure_returns.py 4a40078dbf0e6b9a5f5c --total768 --stride12.
This selects64 geometries spanning the full trajectory, reuses11 matching
previous128-stage measurement caches, and computes only missing start-return
arrays. It can run during validation, may finish withpending indices, and is
safe to rerun after export completion because valid caches skip. Do not
concurrently duplicate32940. No new simulation was started in the main slot.
Other live simulators90274,28894,45527 continue. After32940 finishes and
13823 validates, check pending counts and finish only missing measurements.
The768-vs768 cross-chain comparison must wait for independent90274; previous
Rhat1.033 refers to384-vs384 stages and must not be presented as a fresh768
comparison. Baseline coupling/volume gates remain incomplete.
