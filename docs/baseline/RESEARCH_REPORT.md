# Native CDT baseline implementation and executed pilot

## Decision

**Native C++ Monte Carlo was actually compiled and executed. The requested equilibrium baseline reproduction is NOT ESTABLISHED.** The delivered execution covers 12 fresh, independently seeded production chains at three target volumes, with 1,536 saved production configurations. Every saved configuration passed an independent manifold validator. Slow spatial-profile observables fail the declared convergence screens in all three volume cohorts. A plausible spectral-dimension curve is not a substitute for this missing convergence evidence.

No existing production gate was changed. No topology-conditioned production was launched. No branch, commit, or push was created by this delivery.

## Source and build audit

The inspected repository base is `6fafad81840ecb03cc858953352b227d242d5ee1`. The native submodule is pinned to `JorenB/3d-cdt@5720c0b98d809b35974d5c6fe067a828fe6b1267`.

An actual direct clone was attempted and failed because the runtime could not resolve GitHub. The native source was then recovered through the connected GitHub interface, checked against Git blob hashes, and compiled in an isolated source export. This is **not** described as a full clean Git clone or an execution of the entire original repository. `configs/baseline/source_lock.json`, the source-recovery record, and build receipts identify the exact inputs.

The build first compiles the repository's original research driver with its existing, explicit proposal-ratio and inverse volume-penalty corrections. A second isolated generated copy applies the audited adapter fixes below. Original tracked simulator files are not overwritten. The native simulator paper is the basis for retaining the documented Metropolis and volume-fixing conventions [1].

Actual production build: `8b55ef4286f4053695f7`; SHA-256 `ce6658667083a61c7107e27753ef1b6f7ae06b198d3dd01f3292e1e27ddb4b30`. Compiler: GCC 14.2.0; Linux x86_64. Python and numerical-library versions are saved in `environment/baseline-tested.json`.

## Concrete fixes and tests

**Checkpoint parsing:** GNU libstdc++ RNG deserialization did not skip an intervening newline in the original checkpoint reader. The adapter explicitly consumes whitespace, verifies stream state, initializes vector lengths before reading, and validates the text/binary delimiter. Interrupted and extended runs now reproduce uninterrupted snapshots in the tested cases.

**Acceptance reporting:** the original deletion wrapper could return success even when `Universe::move62` rejected the move. The adapter returns that result. Same-seed original/adapter runs preserve geometry and random-stream evolution. A test-only fault injection deliberately forces the rejection branch to establish the reporting regression; this is not a claim that a particular physical pilot visited that rare branch.

**Runtime safety:** pool exhaustion aborts rather than masquerading as an ordinary rejected move; argument and integer-overflow checks precede execution. Signals stop at a checkpointable sweep boundary. File locks remain held by a live child process, and completed outputs are verified before reuse. Source, binary, initial geometry, parameters, seed lineage, and checkpoint horizon are recorded. Incomplete or corrupt evidence fails closed.

A generic product triangulation used in an early trial passed an abstract manifold check but did not satisfy the native simulator's ordering convention. That failed trial is retained. The executed runs use native-compatible oriented periodic seeds, followed by native Monte Carlo moves; no arbitrarily rewired graph is substituted for spacetime.

The official CLI and test launcher select multiprocessing `spawn` before parallel numerical work. Early direct-library tests emitted Python's multithreaded-fork warning; the final supported-entrypoint test run has no warnings. Direct library users must likewise choose a safe multiprocessing context.

## Executed design

The sampled model uses the pinned corrected native driver with action convention `-k0*N0 + k3*N3` and the existing quadratic volume-fixing term `4e-5*(N3-target)^2`. Time is periodic with 64 slices; spatial slices are spherical. The actual pilot uses `k0=1.0` and target total volumes 10,000, 30,000, and 60,000.

Each cohort has one excluded tuning job, four independently seeded initial-state dispersal jobs, and four independently reseeded production chains. All four production chains at one volume use exactly the same frozen `k3`. Dispersal uses declared target-volume factors 0.8, 0.95, 1.05, and 1.2. Tuning does not continue during production, and a shared checkpoint stream is not counted as multiple independent chains.

Pilot schedule: 1,500 tuning sweeps; 1,500 dispersal sweeps; 12,000 declared production warmup sweeps; 128 saved configurations per chain, separated by 100 sweeps. One pilot sweep is `target N3` proposed moves. The historical N10,000 configuration instead used 100,000 attempts per sweep, so bare sweep counts must not be compared as equal computational work.

The 27 native jobs executed **10,670,500,000 scheduled proposals**, of which **9,920,000,000** belong to the production jobs including their warmup. The 15 tuning/dispersal exports are excluded from the 1,536 production snapshots. All attempted schedules and all warmup/measurement traces remain available. No measurements were removed after seeing an unfavorable diagnostic.

A separate eight-chain, two-volume, 128-snapshot native smoke study and new temporary native integration fixtures were executed for testing. They are not included in the principal pilot counts above.

## Diagnostics: the physical blocker remains

The declared screens use rank-normalized/folded split R-hat at most 1.01, bulk and tail ESS at least 400, and Monte Carlo standard error relative to standard deviation at most 0.05. They cover native counts, the peak spatial-slice volume, translation-invariant profile summaries, and fixed diffusion observables. These are diagnostic policies, not a proof of equilibrium. Rank/folded diagnostics and local efficiency checks follow the methodological motivation in [3].

| Target N3 | N3 R-hat | Peak-slice R-hat | Peak-slice bulk ESS | Worst sampled-profile R-hat | Minimum sampled-profile bulk ESS |
|---:|---:|---:|---:|---:|---:|
| 10,000 | 1.006193 | 2.053801 | 5.347 | 2.925632 | 4.850 |
| 30,000 | 1.000851 | 1.801199 | 5.876 | 2.376240 | 5.241 |
| 60,000 | 1.003401 | 1.248224 | 12.732 | 1.623000 | 7.298 |

Volume is comparatively stable while shape is not. The current samples therefore cannot support an equilibrium baseline claim. Increasing thinning alone does not cure insufficient exploration. A longer declared warmup/new study or documented same-chain extension must be evaluated without retrospectively selecting favorable configurations.

## Ordinary diffusion measurements

Every production snapshot was checked by an independent C++ combinatorial validator, including reciprocal opposite-face neighbors, closed face incidence, connected geometry, periodic foliation, circular edge links, spherical vertex links, and spherical spatial slices. The C++ checker was cross-checked against a separate Python implementation on known fixtures. The checks do not rely on simulator caches.

Diffusion uses exact sparse probability propagation for the selected roots, not Monte Carlo walker noise. Root selection remains statistical: the pilot selects 16 roots uniformly without replacement for each declared root population, rather than evaluating every tetrahedron. The primary full-graph root sample is not sorted before taking nested subsets.

Both rho=0.8 and rho=0.4 are measured through 256 steps. The saved output contains **48,241,984 return-probability values** across 11,732 root-policy/operator arrays, including resolved excision sensitivities. This count includes step zero and repeated root locations under different operators; it is not a count of independent samples.

Two estimands are explicitly distinguished. In the first, root-averaged return probabilities are differentiated on each geometry and the resulting dimensions are averaged across geometries. In the second, the ensemble-mean return curve is differentiated. They are not generally equal. The first ordering matches the estimator definition in Cooperman's analysis; however, that paper removes the stalk before measurement, so the full-graph curves here are not a completed reproduction of its condensate observable [2].

| Target N3 | Exploratory full-graph Ds peak | Diffusion step at peak |
|---:|---:|---:|
| 10,000 | 2.441023 | 25 |
| 30,000 | 2.795125 | 80 |
| 60,000 | 2.940807 | 127 |

These peaks are selected within the declared 16–192 step analysis window, with a stationary-floor exclusion. The near-three value at the largest volume is descriptive only: the native profile screens still fail. No curve is fitted or constrained to return dimension two or three. No infinite-volume extrapolation is claimed.

Conditional uncertainty uses hierarchical circular block resampling, multiple block lengths, and separately reported finite-population root jackknife error. Plotted intervals are pointwise, not simultaneous, and are not validated equilibrium intervals when native diagnostics fail. Diffusion-rate sensitivity is evaluated at equal rho*sigma and reported rather than silently absorbed into a fitted clock.

## Stalk treatment and protocol amendment

The inherited `src/condensate.py` fits a cos-squared/constant form to individual configurations; its own documentation calls that an adaptation of the coherently averaged-profile prescription. The pilot resolves this adaptation for 402/512, 484/512, and 511/512 configurations at the three volumes. Both hold and renormalized excision boundaries are measured where valid, but **no ensemble estimate is made from only the successfully excised subset**. A matched historical observable remains unfinished.

An early design note described peak-slice roots as primary and uniform roots as a sensitivity. The explicit measurement protocol, frozen before the diffusion results were computed, designates uniform full-graph roots as primary and preserves peak-slice results as a separate sensitivity. Native count/profile diagnostics had already been inspected at that point. This change is documented, not portrayed as an externally preregistered experiment. The estimator and stalk distinctions are recorded in that measurement protocol.

## Memory-efficient analysis and validation

A first implementation retained the root dimension across every configuration, which would be too memory-intensive at the long-run preset. The final analysis reads one geometry at a time and retains the exact root mean, nested-half estimate, and root jackknife variance. Raw roots and return arrays remain untouched in the evidence. The reduction removes the root dimension from retained analysis storage; it does not approximate the declared statistics.

Cross-checks cover 2, 8, 16, and 64 roots and compare every downstream numerical result against the full-cube implementation. Reanalysis of the actual native pilot preserves both primary estimators and root-error summaries within 1e-12. Earlier analysis versions and their source snapshots are retained for provenance.

The final combined run passed **148 tests**: 139 new native-baseline tests and nine existing baseline tests. There were zero failures, skips, or warnings. Fourteen additional installer safety checks passed. The test-only statement coverage of the new namespace is 87.99%, not 100%. Worker-process numerical execution is not fully represented by this test-only coverage measurement.

The native tests include all four inverse families, deterministic replay, different seeds, interruption, extension, corrupt checkpoints/evidence, a fresh isolated rebuild, original/adapter geometry equivalence, and the reporting fault-injection control. A separately built AddressSanitizer/UndefinedBehaviorSanitizer binary passed an explicitly interrupted-and-resumed native run. This is not a claim of exhaustive C++ verification, nor a rerun of the entire original repository's test collection. The prior 601-test confirmation suite was not counted again in this run.

The final read-only verification checked **7,806 indexed artifacts**, 27 native jobs, all 1,536 production geometries, source snapshots, and independently recomputed both primary spectral estimators. Its result is `verified: true` and `REPRODUCTION_PASS: false`; those statements describe different questions.

## Packaged-payload checks

After ZIP extraction, all four data-part manifests verified **11,055 files / 2,955,089,331 bytes**, and the extracted source independently reverified the scientific evidence and primary estimates. The exact code payload then passed its **139-test new suite** from the extracted source export. These 139 are a subset of the recorded 148 combined tests, not extra unique tests.

Python's `zipfile.extractall` initially dropped the archived native executables' execute bits in this extra test. The ZIP entries retain mode 0755; restoring those declared modes allowed execution and the tests passed. The initial failure log is retained. This did not affect read-only evidence verification, and the Terminal `unzip` route in the handoff preserves the mode metadata. The Linux binaries remain provenance/build-specific artifacts, not Mac executables.

## Remaining requirements

The next substantive computation is longer fixed-coupling native sampling with sufficient slow-profile ESS and cross-chain agreement. The unexecuted long-run preset increases the proposal budget explicitly; it is not a guarantee that its schedule will pass. Its `plan` command shows the budget before execution. The `extend` command preserves the same numerical contract and each chain's own checkpoint, and refuses reductions or incompatible changes.

A genuine clean Git checkout of the pushed code branch, a platform-specific build, and the full original stack remain to be recorded outside this DNS-blocked runtime. The delivered clean-checkout helper performs that clone without overlaying uncommitted source. macOS CI is supplied but was not executed here.

Even after diagnostic success, the historical comparison needs a reviewed, matched stalk/condensate definition, coupling convention, diffusion clock, finite-volume treatment, and numerical reference. This code deliberately cannot turn an editable boolean into external scientific review. Existing production gates remain untouched until the appropriate evidence exists.

## Delivery layout

The code update is additive. The multi-gigabyte raw pilot is distributed separately in four evidence archives and is not silently committed to ordinary Git. Extracting all four into one directory reconstructs the complete study, an exact source export, and native build provenance. Native checkpoints and executables are platform/build-specific; the archived Linux executable is not a Mac program. ASCII geometries and numerical measurements are portable. A new Mac build should start its own study rather than claim that it resumed an incompatible Linux RNG checkpoint.

## Primary sources

[1] Brunekreef, Görlich and Loll, *Simulating CDT quantum gravity*, arXiv:2310.16744v1. https://arxiv.org/html/2310.16744v1

[2] Cooperman, *Scaling analyses of the spectral dimension in 3-dimensional causal dynamical triangulations*, arXiv:1711.02685. https://arxiv.org/abs/1711.02685

[3] Vehtari et al., *Rank-normalization, folding, and localization: An improved R-hat for assessing convergence of MCMC*, arXiv:1903.08008. https://arxiv.org/abs/1903.08008

These sources motivate definitions and checks. The execution counts and measured results above come from this delivery's own saved native evidence, not from those papers.
