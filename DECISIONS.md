# Scientific decisions

## 2026-09-07: audited simulator versus untouched upstream

Pinned JorenB/3d-cdt v1.0.1, commit 5720c0b98d809b35974d5c6fe067a828fe6b1267.
The original release builds unchanged. Its example directory lacks config.dat,
so its run.sh cannot run as supplied. The supplied initialization generator is used.

The source acceptance ratios disagree with Brunekreef–Görlich–Loll,
arXiv:2310.16744 equations 26–27. The source selects the add tetrahedron
uniformly from N31 and the deletion candidate uniformly from N0 vertices.
The paper gives N31/(N0+1) for add and N0/(N31-2) for delete at current counts.
The release instead uses N31/(N31+2) and N31/(N31-2). The research build
uses the paper's factors. This is a declared detailed-balance correction, not
an upstream-identical chain. No physics conclusions may rely on the release
without resolving this discrepancy. licenses and untouched source retained.

Three reverse volume-fixing expressions also use the wrong sign on the
constant term. We implement exp[-epsilon((V+dV-target)^2-(V-target)^2)],
epsilon=0.00004, for all moves. Tests check the reverse identity. Detailed
balance includes the proposal probabilities, not just Boltzmann factors.

Both independent random engines are seeded explicitly. Reproducibility is
required for the same compiler/standard-library/binary. std::default_random_engine
and unordered containers do not promise cross-platform bitwise equivalence.

The driver calls upstream attemptMove, with strictness=3 and volume switch=1.
It separates adaptive tuning, frozen-coupling burn-in and frozen-coupling
measurement. It uses fixed attempted-move intervals and the soft quadratic
volume constraint. It does not use first-hitting-time exact-volume sampling.
The upstream console ratios attempted/failed are replaced by raw attempted
and accepted counts. Debug mode checks each accepted move. Every retained
configuration receives independent face, link, foliation and Euler validation.

## Ensemble and spectral definitions

The requested primary observable differentiates ensemble-averaged return
probability. Cooperman equation 3.12 instead averages per-configuration Ds.
Both must be reported separately; they are generally unequal. No silent switch.
The historical k0 action is explicitly -k0*N0+k3*N3, matching the paper action,
but its footnote warns of a factor-two difference from an earlier reference.
Coupling calibration remains provisional pending phase/volume reproduction.

The condensate/stalk boundary rule is not specified numerically in the 2017
paper; it refers to other papers. Do not call an arbitrary threshold a
literature-compatible reproduction. Boundary diffusion handling must also be
recorded. For the eventual conditioned comparison, the operator stays fixed
and only starts are conditioned. These are distinct choices.

## Reproducibility and scope

Completed independent-chain jobs are hash-verified and skipped. Raw geometry
outputs are never overwritten. Same-binary checkpoint recovery now preserves
vertex/tetra pools and free lists, bag order, both RNGs, coupling and sweep.
Derived halfedge/triangle caches are rebuilt. Restart tests interrupt tuning
and measurement and reproduce all five final snapshots byte-for-byte.
Checkpoints are mutable recovery files, distinct from immutable configurations.
The two earlier pilot runs predate this checkpoint implementation.
Failed jobs can resume with --resume; a partially completed checkpoint interval
may replay bounded work, verifying existing geometry bytes before proceeding.
This format is local to the binary/architecture and is not a portable dataset.
Geometry-only warm starts are explicitly new trajectories with parent lineage.
No topology-conditioned computation is authorized by the scientific gates
until baseline spectral and 2D/3D topology reproduction passes.
