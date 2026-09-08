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
