# Implemented methods and scientific limits — 2026-09-08

This is an implementation contract, not a manuscript or a physics result.
The existing simulator, acceptance patches, raw data, and historical results
are unchanged. Production gates remain closed.

## Exact topology reference backend

`src/topology` constructs genuine abstract simplicial complexes of dimension
at most three and computes homology over a specified prime field. Boundary
matrices use oriented incidences; ranks use exact modular elimination (bitsets
for F2). Duplicate input cells are rejected rather than silently merging
possible parallel cells. A face budget limits reference-backend allocation.

For a nonempty simplex s, `local_betti` computes
H_i(K, costar_K(s); F_p), the homology local to its interior. The independent
implementation `local_betti_via_link` uses reduced H_(i-dim(s)-1)(link(s); F_p),
including reduced H_-1 of the void link. Both agree on every simplex of the
saved synthetic validation fixtures over F2 and F11. Sphere, ball, torus,
pinched-sphere, boundary-squared-zero, and subdivision tests are included.
A projective-plane test checks that field choice can change the answer.

**This is not integral canonical stratification.** Equal local Betti vectors
alone do not establish local constancy of a homology sheaf, its incidence
maps, or a topological-manifold neighborhood. Asai–Shah's algorithm involves
an iterative canonical stratification and the integral local homology sheaf;
that full algorithm is not implemented here. Reference:
https://arxiv.org/abs/1808.06568

## Seed sampling and connected Voronoi regions

`src/coarsegrain/voronoi.py` implements graph-distance annulus Poisson sampling
and a simultaneous layerwise Voronoi assignment. Tests require inter-seed
distance >= delta, nearest-seed distance < delta, complete coverage, and a
parent path inside each cell. Ties choose uniformly among reachable
previous-layer cell labels, with a recorded random seed. This explicit rule
must be compared with any author-supplied implementation before claiming
bitwise or distributional reproduction of its tie handling.

The reference for the sampling/Voronoi/dual sequence is sections 4.1–4.3 of
van der Duin et al., *Quantum Gravity and Effective Topology*:
https://arxiv.org/html/2510.05695v1
The paper demonstrates its method on 2D CDT and EDT. Passing the geometric
fixtures below is not reproduction of those quantum-gravity ensembles.

## Incidence-preserving 2D dual

`src/coarsegrain/dual2d.py` follows distinct connected boundary segments,
not just unordered pairs of region names. Segments give dual edges; triple
points give dual triangles. Parallel edges and repeated triangular cells
retain separate IDs. Boundary matrices and flag subdivisions provide two
independent homology calculations.

An explicit two-band torus control produces two parallel edges between the
same two coarse vertices. It has b1=1; replacing that pair by one edge would
incorrectly give b1=0. A two-triangle pillow checks repeated-face handling.
Only embedded regular cell closures are accepted: loops/nonregular attaching
maps are rejected instead of being converted with an invalid face-poset rule.
The CDT/EDT ensemble measurements and their published Betti curves remain
unreproduced.

## Experimental 3D candidate, not a validated prescription

`src/coarsegrain/dual3d.py` extends the explicit PL incidence construction:
interfaces consist of barycentric flags (fine edge, fine face, tetrahedron),
triple junctions of (fine face, tetrahedron) flags, and four-color tetrahedra
supply dual 3-cells. Connected interface and junction components retain their
own IDs. Cell closures are checked before subdivision; no arbitrary looped
CW complex is treated as an abstract face poset.

The full fine-piece/component provenance and interface/junction F2 homology
are returned. This exposes an important limitation: a connected interface or
junction can be noncontractible, and replacing it by one dual cell is a
substantive coarse-graining choice. The code records that choice; it does not
prove that it preserves topology or is the correct quantum-gravity observable.
Direct and subdivided homology agree on the accepted cell complexes. Delta=1
recovers the synthetic S3/T3 invariants. Delta>1 changes on a toy torus are
method diagnostics, **not evidence about quantum spacetime**.

Required before production: compare alternative definitions and author
methods, test controlled neck-width/refinement behavior and seed sensitivity,
validate singular local incidence maps, and define an independently checked
preimage onto microscopic tetrahedra. Neither that mapping nor full canonical
stratification is completed by this update.

## Conditioned diffusion and the mixture identity

`src/conditioned.py` keeps the original symmetric stochastic microscopic
operator fixed. Masks partition a declared starting-site population; they
never confine walks to a region. Exact probability propagation is streamed in
blocks to bound memory. For class c, P_c is the average diagonal return over
its starts, f_c is its fraction of that population, and

    P_all(sigma) = sum_c f_c P_c(sigma)
    w_c(sigma) = f_c P_c(sigma) / P_all(sigma)
    D_all(sigma) = sum_c w_c(sigma) D_c(sigma).

The last identity holds for the shared linear central-difference derivative
used by the existing spectral module. **Site fractions alone are not the
spectral-dimension mixture weights.** A synthetic 1%-of-sites example is
included only to illustrate this distinction. No causal interpretation follows
from the identity or from a difference between conditional curves.

Memory is O(N * block_size), but exact all-start time remains
O(steps * nnz(M) * number_of_starts). This is a reference implementation, not
a promise of fast all-site production on large geometries.

## Uncertainty and production gates

`src/uncertainty.py` implements paired circular-block bootstrap within each
independent chain, retaining class/time pairing. Block length is in stored
configurations, not sweeps, and must be selected from relevant autocorrelation
diagnostics and tested for sensitivity. It reports both dimension-of-mean
return and mean-of-per-configuration dimension; those estimands differ.
Intervals are pointwise and cannot certify equilibrium or causality.

`workflows/measure_conditioned.py` checks four evidence-backed production gates
before numerical work, verifies label/geometry association, limits estimated
work, and writes immutable hash-addressed provenance. Gate status PASS requires
repo-local evidence files and matching SHA256 hashes; a boolean assertion or a
synthetic test is insufficient. All four default gates are NOT_ESTABLISHED.

## Executed validation, with scope

102 new Python tests passed locally. The numerical validation ran six topology
fixtures over F2/F11, 16 sampled 2D constructions, and eight experimental 3D
constructions. Maximum return-mixture and dimension-mixture errors were
5.55e-17 and 3.33e-15, respectively. The saved report and test summary record
source hashes, seeds, environment, and exact scope in `results/methods/`.

The local environment was Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0, pytest
9.0.2. The repository's original dependency lock is unchanged. The added CI
job tests the new suite with its pinned numerical dependencies; a configured
CI workflow is not a claim that the hosted run has passed.

This execution used selected repository files and an unchanged, blob-verified
spectral dependency. It did not rerun the legacy C++ integration suite or the
user's long-running Mac simulations. No reproduction gate or primary positive/
negative physics result is issued.
