# Integral homology and recursive canonical labels

## Implemented scope

The new `topology.integral` and `topology.stratification` modules extend the
existing abstract simplicial-complex API. The canonical labeling algorithm is
the iterative generic-locus construction of Asai and Shah, Algorithm 4.13 and
Section 5 of arXiv:1808.06568v3. The input dimension is at most three. This
implements the labels and connected stratum components, not the localized
exit-path infinity-category. It does not certify a particular 3D CDT
coarse-graining prescription.

Reference: https://arxiv.org/html/1808.06568v3

## Exact homology without change-of-basis matrices

For a finite free integral chain complex with d_k d_(k+1)=0, the exact sequence

    0 -> H_k -> C_k / im(d_(k+1)) -> im(d_k) -> 0

splits because im(d_k) is free abelian. Consequently the torsion invariant
factors of H_k are precisely the nonunit Smith diagonal entries of d_(k+1).
The free rank is dim(C_k) - rank(d_k) - rank(d_(k+1)). No floating-point rank
threshold or modular substitution is used. The matrices and every d*d product
are checked over the integers. SymPy supplies Smith normal forms over ZZ:
https://docs.sympy.org/latest/modules/matrices/normalforms.html

The default reference budget caps each dense Smith matrix at 250,000 entries
and a chain complex at 20,000 generators. These are workload safeguards, not
bounds on intermediate coefficient growth or a hard operating-system memory
limit. The exact backend is intended for moderate global complexes and local
validation. Production-size global Smith computations require another backend.

## Local chain maps, not only local ranks

For a nonempty simplex s, the relative chain basis is the set of cofaces of s:
C(K,costar(s)). Boundary terms that no longer contain s become zero. For s <= t,
the chain map to C(K,costar(t)) is the quotient projection dropping generators
not containing t. The implementation explicitly checks the chain-map equation.

For F:C->D, Cone(F)_k=D_k direct-sum C_(k-1) and

    d_cone = [ d_D   F ]
             [  0  -d_C].

The induced homology maps are isomorphisms exactly when this cone is acyclic.
Cone homology is computed over Z, including torsion. The cone can reach degree
four even for three-dimensional input. A regression test uses multiplication
by two on Z: source and target homology groups agree, but the cone contains
Z/2 and the map is correctly rejected. Composition of local projections is
also tested exactly.

A second local-homology implementation uses the shifted reduced homology of
the simplex link, including reduced H_-1 of the void link. It agrees with the
relative-chain computation on every simplex in the saved fixture study.

## Recursive generic-locus algorithm

At each stage of dimension n, process cells in decreasing simplex dimension.
A cell is generic only if all immediate cofaces have already been accepted and
its local integral homology is one Z in degree n and zero elsewhere. Accepting
an upward-closed set ensures its removal leaves a subcomplex. Recompute local
homology in that remainder and repeat. This recursive condition is essential:
a bare table of original local Betti vectors is not the canonical algorithm.

Two independently implemented membership backends are available:

* `method='integral'`: exact local Smith calculations at each eligible cell.
* `method='combinatorial'`: low-dimensional sphere-link recognition, under the
  same generic-coface recursion. S^0 has two points; S^1 is a connected cycle;
  S^2 is a connected closed combinatorial surface with Euler characteristic 2.
  Every vertex link of the candidate surface is checked to be a cycle.

For accepted strata, `audit_incidence=True` independently constructs mapping
cones on covering incidences and checks integral acyclicity. The audit is
bounded and fails rather than returning a partial certificate as complete.
Canonical labeling and its tests do not mean every homology-manifold test in
arbitrary dimensions would establish a topological manifold.

## Executed evidence

The saved continuation study checks eight fixtures, 128 random small abstract
complexes, and every local/link pair in those fixtures. The two labeling
backends agree. It recognizes the pinched vertex of a wedge of two S^3s and
the boundary of a 3-ball. The real projective plane has global H_1=Z/2 but is
correctly locally regular: nonorientability is not a singularity.

The tests also check subdivision-carrier invariance, mixed-dimensional
components, integer input validation, matrix budgets, invalid differentials,
invalid chain maps, and nonisomorphic maps with identical source/target groups.
