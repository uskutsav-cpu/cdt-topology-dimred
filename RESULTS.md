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
