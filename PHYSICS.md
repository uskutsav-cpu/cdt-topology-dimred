# Physics notebook

This project tests an association in 2+1D causal dynamical triangulations.
It does not establish a mechanism by construction and does not assume a
continuum limit. The computational gates remain mandatory.

k0 multiplies minus the number of vertices in the Euclidean Regge action and
is proportional to the inverse bare Newton coupling. k3 multiplies the number
of tetrahedra and contains the cosmological coupling. These are bare lattice
parameters; interpreting them as directly measured continuum constants would
require renormalization and scale setting. The implementation and historical
paper both write S_E=-k0*N0+k3*N3, but a historical factor-two convention warning
requires care when importing parameter scans from earlier papers.

The ensemble has periodic time, spherical spatial slices and total topology
S2 x S1. Its tetrahedra respect a causal foliation before Wick rotation. The
numerical Monte Carlo weights are Euclidean; the spectral walker is a probe
of that Euclidean geometry, not a physical Lorentzian particle trajectory.

Volume fluctuates because the ergodic move set includes volume-changing moves.
A quadratic penalty controls fluctuations around a chosen target. k3 is tuned
before fixed-coupling burn-in and measurement. A narrow-volume ensemble and an
exact-volume ensemble are different finite simulations; the driver records
actual volumes and does not equate them silently. Finite-size analysis is
needed before interpreting a finite-volume spectral peak near 3.

The intended phase C has an extended condensate with a de Sitter-like spatial
volume profile. Phase membership must be demonstrated using geometry, profiles
and coupling behavior, rather than inferred from k0 alone. The first small
pilot is not certified as a thermalized phase-C ensemble. The standard 3D
model's phase-transition/continuum questions remain separate from this test.

The stalk is the near-minimal-volume portion outside the condensate in the
periodically foliated geometry. The historical spectral study removes it as a
numerical artifact. Its precise cutoff and boundary diffusion implementation
are not fully specified in that paper. The referenced transition-amplitude
paper fits a central cos-squared profile joined to a constant stalk (appendix
C, equations C.19–C.20). An implementation based on this fit must report the
fit, masks and sensitivity. A starts-only condensate mask and an excised graph
give different observables and must be compared explicitly.

Sigma measures diffusion steps; rho is the probability of leaving the current
simplex on a step. Neither is the CDT foliation time. The spectral dimension
is the logarithmic decay rate of return probability. On a regular infinite
d-dimensional lattice, above the lattice cutoff, P scales as sigma^(-d/2).
At the earliest steps parity/discreteness effects dominate; at late steps a
finite connected graph saturates and its spectral dimension falls toward zero.

The established literature reports intermediate-scale dimension near 3 and
short-scale reduction toward roughly 2 in 3D CDT, with finite-size and coupling
dependence. A branched-polymer interpretation is a conjecture, not an input to
the classification. The present hypothesis is that microscopic starts near
effective coarse nonregular topology have lower short-scale dimension than
regular starts. A null result, a confounded signal or an unstable coarse
definition must be reported honestly.

For the primary experiment, diffusion remains on the same microscopic CDT
geometry regardless of starting label. Confining a walk to a stratum changes
the diffusion operator and answers another question. Coarse-graining scale,
seed realization, tie-breaking and preimage conventions are algorithmic choices.
Their stability must be established before assigning physical significance.
Canonical strata need not map automatically to the informal labels 'branch',
'pinch' or 'sheet'; inspect the local topology and incidence structure.

The observed quantity is a conditional return distribution and its derivative.
It can indicate association, not causation. Coordination, time-slice location,
local volume growth, curvature proxies and bottlenecks are potential confounders.
Matching, permutation, grouped predictive comparison, alternative coarse
definitions, and finite-size/coupling scans test robustness.

Global returns decompose by class exactly when weights and ensemble averaging
are consistent. Singular site fraction alone is insufficient to quantify a
mechanism: contribution to return probability also depends on the ratio of
class return probabilities. Dimension is not the site-fraction average of class
dimensions. See MATH.md for the correct return-dependent weights.

References: [simulation](https://arxiv.org/abs/2310.16744),
[spectral scaling](https://arxiv.org/abs/1711.02685),
[stalk/profile treatment](https://arxiv.org/abs/1305.2932),
[effective topology](https://arxiv.org/abs/2510.05695).
