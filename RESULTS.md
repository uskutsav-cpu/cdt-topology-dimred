# Computational results — in progress

PRIMARY RESULT: NOT COMPUTED. Ordinary spectral reproduction has not passed.
No topology-conditioned effect, confidence interval or permutation p-value
is available. No positive or null physics claim is made.

Completed observations:

- Untouched upstream v1.0.1 builds. Detailed-balance discrepancies documented
  in DECISIONS.md; the research build implements the cited paper's factors.
- Sixteen prior Python tests pass; three new exact-short-return tests pass.
- Four move/inverse pairs restore the identical tetrahedron vertex sets.
- Two same-seed debug runs give four byte-identical configurations.
- Checkpoint interruptions during tuning and measurement each reproduce five
  byte-identical final configurations.
- 128 N3~3,000 pilot configurations pass independent closed-manifold checks.
  Mean N3=2913.9922. Volume ESS=5.76; peak-slice ESS=6.18. Statistical screen
  fails. Full-lattice Ds peaks at 2.549 for sigma>=10 across 16 sampled
  configurations; this is an exploratory pilot number, not reproduction.
- 128 N3~10,000 configurations pass geometry checks. MCMC takes 401.6 seconds;
  simulation plus independent export validation takes 717.7 seconds.
  Mean N3 over measurement sweeps=10004.2023; volume ESS=108.85,
  peak-slice ESS=15.98. The slow observable prevents an equilibrium screen pass.
- On one 2,786-tetrahedron pilot geometry, exact propagation at 256 specified
  starts for 128 steps takes 0.684 s. Hutchinson with 256 probes takes 0.856 s
  and has maximum relative estimated SE 2.04% over sigma=9..64. 500,000 walks
  take 3.747 s with maximum observed relative error 5.10% on that interval.
  Exact propagation is selected for the current moderate-size measurements.

- The continuation 99188cc153094acfc0b4 was extended to 320 snapshots without
  repeating old sweeps. Across 16,000 measurement sweeps, peak-slice ESS=14.84
  and split-half z=2.18; N0 split-half z=2.26. It fails the equilibrium screen.
- Saved measurements on 64 configurations from that continuation (512 starts,
  sigma=0..256) give an exploratory Ds peak=2.78654. Maximum relative return
  sampling SE is 1.74%; block-bootstrap bands are not certified equilibrium CIs.
- Exact all-site returns through sigma=26 on eight of those geometries show
  512-start sampling variance is 3.22–6.67 times the exact between-geometry
  variance at the five checked times. This motivates exact UV computation.
  The geometries are nonthermalized; this is a numerical precision result.
- A dedicated equilibration stage 4a40078dbf0e6b9a5f5c inherits the complete
  checkpoint and RNG state. Its 20,000 burn and 25,600 measurement sweeps completed; all 128 saved
  geometries validated. N3 ESS=1509.36, split-z=0.679; peak-slice ESS=18.27,
  split-z=0.873. The effective-sample screen fails. A continuation to 384 total
  configurations is running, preserving previous work.

These runtimes are local measurements, not guarantees for production scale.
Pilot curves and raw return data are under results/. Registry files identify
the exact binary, input hashes, seeds and parameters for each chain.

FINITE SIZE: production scaling not computed.
COUPLING DEPENDENCE: not computed.
TOPOLOGY, MATCHING, PERMUTATION, MECHANISM: not computed; prerequisite gates.

Further baseline measurement:32 of the dedicated equilibration stage's saved
geometries,512 starts,256 steps, give an exploratory Ds peak2.79320 and maximum
relative return sampling SE1.679%. Autocorrelation screen remains unmet at
128 configurations; this is not a reproduction pass. Exact all-site short-time
measurement is running to eliminate starting-point sampling uncertainty.

Diffusion-rate baseline sensitivity on32 saved geometries, obtained from exact
binomial mixtures of the existing rho=.8 return sequences: rho=.2,.4,.6,.8
has peak Ds=2.82296,2.81274,2.80283,2.79320, respectively. The corresponding
rho*sigma_peak values are62.2,63.6,64.8,66.4. Maximum omitted binomial mass
is1.81e-34. RMS differences from rho=.8 over scaled time8..80 are0.0622,0.0404,
0.0198,0. These are paired rate sensitivities on a not-yet-certified ensemble,
not independent confirmation of equilibrium or exact continuum scaling.

Extended convergence check:384 configurations of4a400... and128 independent
configurations of8b3e... all pass geometry validation. Peak spatial-volume ESS
is29.07 and21.52, respectively. On equal25,600-sweep prefixes, rank/folded
splitRhat is1.01929 for peak spatial volume, exceeding1.01; splitESS is also
insufficient. Mean volume and vertex counts agree closely. Both trajectories
are being extended from checkpoints. Convergence remains unestablished.

Independent baseline spectra:32 geometries per chain,512 starts per geometry,
give peaks2.79320 and2.79799. Over sigma9..64 the maximum absolute Ds difference
is0.00556 and maximum relative P difference0.254%. These are descriptive
agreements; slow-mode convergence remains unestablished. The independent
chain's diffusion-rate scaling gives similar rescaled peak times63.0–66.4.

N30000/T64 pilot completed: all128 geometries validate. MeanN3=30021.22;
volume ESS=1782.86, but peak spatial-volume ESS=4.33 with estimated tau=2954
sweeps. Convergence is not established. A checkpoint continuation with saved
spacing2400 sweeps is running; the earlier measurements are retained.

Controlled volume pilot (T64,k0=1,rho=.8): mean condensate volumes9002 and29127
have Ds peaks2.79320 and2.94356 at diffusion times83 and129. Short-time Ds15
is2.52228 and2.53403. This supports the qualitative finite-volume trend, but
neither ensemble has passed slow-mode convergence. Two sizes do not establish
an asymptotic scaling law. Tables and rendered figure: finite_size_pilot.*.

Independent chain through384 now passes all single-chain screens: peak
spatial-volume ESS52.73, split-z1.447. All384 geometries validate. However,
the equal-length cross-chain comparison gives peak-volume Rhat1.033 and
insufficient split-chain ESS; convergence remains unestablished. Both10k
chains are continuing to768 saved configurations.

First chain through768:153600 measurement sweeps now pass all single-chain
screens, including peak spatial-volume ESS73.01 and split-z0.481. Geometry
validation is pending. Measurements spanning the full trajectory are running,
with matching old return files reused. Cross-chain convergence for the longer
matched records has not yet been assessed.

All768 first-chain geometries are validated. A64-geometry spectral sample
spanning the full trajectory gives peakDs2.79022, maximum relative return
samplingSE1.816%. Earlier saved returns were reused. This supports stability
of the baseline spectrum with longer sampling, while the matched long-chain
comparison is still pending. The predeclaredk0=1.5 comparison is running.

First fixed-volume coupling pilot: k0=.5 vs1 atN30000,T64,rho=.8 gives
Ds15=2.56959 vs2.53403 and Ds25=2.69342 vs2.64883 (16 geometries each).
PeakDs=2.95475 vs2.94356. Mean condensate volumes differ by0.57%; these are
not exactly fixed-condensate-volume data. The decrease at higher coupling
is descriptive evidence only, pending convergence and the remaining grid.
# Matched 768-snapshot baseline comparison

The first N10000 baseline now has1536 validated snapshots and307200
measurement sweeps. All its per-chain screens pass. Peak-slice tau773.83835,
ESS198.49107,split-z0.36617. This does not certify cross-chain convergence;
the independent1536 run remains active. Source:
`results/tables/4a40078dbf0e6b9a5f5c_through1536_diagnostics.json`.
The128-configuration spectral measurement spanning this trajectory is running.

The k0=.5 long continuation has128 validated snapshots spanning153600
measurement sweeps. Peak-slice tau2569.38242,ESS29.89045,split-z1.69722:
shape ESS remains below50. N0/N3/N31 screens pass. The stage is extending
to256 snapshots without discarding these data. Source:
`results/tables/1c43898e12fc22400dec_through128_diagnostics.json`.

The three-volume pilot comparison is complete. At mean condensate volumes
9002.375,29126.5625,59177.0625, peakDs values are2.79319873,2.94356034,3.04922218
at sigma83,129,191. Ds(15) stays near2.52–2.53. Largest-volume maximum return
SE is1.8054%. The PDF was rendered and visually verified. All three are
initial pilot datasets; no equilibrium certification or asymptotic scaling
claim is made. Sources: `results/tables/finite_size_pilot_three_volumes.*`
and `results/figures/finite_size_pilot_three_volumes.pdf`.

The N60000,k0=1,T64 pilot has128 validated geometries. Its peak-slice
autocorrelation time is3108.68452 sweeps,ESS4.11750,split-z2.01234, failing
sampling and drift screens. N0/N3/N31 screens pass. Pilot spectra are running.
Source: `results/tables/f045a528fac6359e9df4_through128_diagnostics.json`.

The initial five-point coupling scan is complete. Atk0=2.5,peakDs=2.91173118,
Ds(15)=2.39052069,Ds(25)=2.49874777. Maximum relative return SE is2.0905%.
Short-timeDs decreases across all fivek0 values; all ensembles remain pilots
with failed shape ESS checks. See `results/figures/coupling_pilot.pdf` and
`results/tables/coupling_pilot.*`. The rendered PDF passed visual inspection.

The k0=2.5,N30000,T64 pilot has128 validated geometries. Peak-slice
autocorrelation time579.13442 sweeps,ESS22.10195,split-z0.94476: the shape
ESS fails, while N0/N3/N31 screens pass. Spectrum measurement is in progress.
Source: `results/tables/4f7a75be6ed25248ce1e_through128_diagnostics.json`.

The k0=2 pilot spectrum (16 configurations,512 starts each,rho=.8) gives
peakDs2.95889762,Ds(15)=2.44484283,andDs(25)=2.56027081. Four coupling points
(.5,1,1.5,2) now show decreasing short-timeDs at similar condensate volumes,
with intermediate-scale peaks near2.95. These remain nonconverged pilots.
Maximum relative return SE over9..64 is2.0781%, slightly above2%.
The fifth pointk0=2.5 is still running; no coupling-reproduction pass is claimed.

Saved k0=1.5 pilot spectra (16 configurations,512 starts each,rho=.8) give
peakDs2.94200850,Ds(15)=2.49594960,andDs(25)=2.60538756. The three available
couplings(.5,1,1.5) show decreasing short-timeDs at fixed total-volume target,
but all are nonconverged pilot ensembles. See `results/tables/coupling_pilot.*`.

The k0=2,N30000,T64 pilot has128 validated geometries. Its peak-slice
autocorrelation time is818.15444 sweeps,ESS15.64497,split-z2.12705; the
shape observable fails both sampling and drift screens. N0/N3/N31 screens
pass. No production-equilibrium inference follows from this pilot.
Source: `results/tables/029620366a1c017aaa4b_through128_diagnostics.json`.

The k0=1.5,N30000,T64 pilot has128 validated geometries. Its peak-slice
autocorrelation time is1301.96691 sweeps,ESS9.83128,split-z1.23488; volume
and vertex-number screens pass but the shape ESS fails. This pilot is not a
production equilibrium ensemble. Source:
`results/tables/d98f6ba3a813c6c7f098_through128_diagnostics.json`.

Both N10000 chains have768 validated snapshots. The common153600 post-burn
sweeps give peak-slice rank/folded split Rhat1.01217491 and minimum split
ESS29.07361, still failing the declared1.01/50 comparison screens. Full-chain
peak ESS values are73.00882 and117.01872. The independent chain's total-volume
split-z2.81397 also fails its per-chain screen. These checks do not certify
equilibrium. Source: `results/tables/chain_comparison_6fdc582a8fea.json`.
The full-length spectral comparison uses64 configurations per chain (every
12th of768),512 starts each. PeakDs values are2.79022348 and2.78819427.
Maximum absoluteDs difference over sigma9..64 is0.00577099; maximum relative
return difference is0.00337239. This agreement does not override the failed
convergence checks. Exact source hashes and curves are in
`results/tables/independent_baseline_spectral_comparison_total768_stride12.*`.
