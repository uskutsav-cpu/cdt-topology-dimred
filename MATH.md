# Mathematical contract

Status: the simulation, geometry and spectral sections below are implemented.
Later topology/statistics sections specify the required contract; they are not
claims that the corresponding algorithms or experiments are complete.

## Ensemble and moves

The Euclidean action is S_E(T)=-k0 N0(T)+k3 N3(T). For labelled triangulations
the simulation paper uses pi_l(T) proportional to exp(-S_E)/N0!. Geometric
observables do not depend on the bookkeeping labels. A proposal q(T,T') is
accepted with min(1, pi_l(T')q(T',T)/(pi_l(T)q(T,T'))). Rejected proposals
leave the configuration unchanged; omitting rejection time biases the chain.

For (2,6), (6,2), (4,4), (2,3), (3,2), respectively, (Delta N0,Delta N3) is
(1,4), (-1,-4), (0,0), (0,1), (0,-1). With uniform selection of a (3,1)
tetrahedron for insertion and a vertex for deletion, the action/proposal
factors in current counts are:

    add:    N31/(N0+1) exp(k0-4 k3)
    delete: N0/(N31-2) exp(-k0+4 k3)
    flip:   1
    shift:  exp(-k3)
    inverse shift: exp(k3)

Invalid local configurations are rejected. Up/down choices and inverse
move-family proposal frequencies are symmetric in this driver. The first two
expressions follow equations 26–27 of the simulation paper. They differ from
the pinned implementation: see DECISIONS.md and workflows/build.py.

The soft volume term is S_fix=epsilon(V-V_target)^2, V=N3, epsilon=4e-5.
Its exact multiplier for any proposal with volume change d is

    exp[-epsilon((V+d-V_target)^2-(V-V_target)^2)]
  = exp[-epsilon(2 d (V-V_target)+d^2)].

The d^2 term is positive inside the action difference for both directions.
Evaluating the reverse factor at V+d must give the reciprocal of the forward
factor at V. This algebra detects the reverse-sign errors in the release.
At a fixed volume this term is constant; at finite epsilon the measurement
ensemble has a narrow distribution of volumes, which must be reported.
Tuning is adaptive and is excluded from equilibrium measurement. Burn-in and
measurement use a frozen k3. One sweep is a stated number of attempted moves.

## Simplices, topology and geometry validation

A tetrahedron is an ordered list of four distinct vertex IDs with a neighbor
opposite each vertex. The unordered vertex set identifies a tetrahedron only
in the strict simplicial ensemble. Every face has exactly two incident
tetrahedra in the closed spacetime. Adjacency must agree with shared faces.

Time is periodic modulo T. Each tetrahedron has vertices in adjacent slices
with multiplicities (3,1), (2,2), or (1,3). Spatial slices are triangulated S2;
the closed spacetime topology is S2 x S1, not S3. Thus chi(spacetime)=0 and
chi(slice)=2. N31 equals the total count of spatial triangles. For spherical
slices N0=N31/2+2T, providing a redundant observable consistency check.

For a finite simplicial complex, C_k is the free group on its k-simplices and
the oriented boundary deletes each vertex in turn with alternating signs.
Boundary squared is zero. H_k=ker boundary_k / image boundary_(k+1), and
beta_k is its free rank. Euler–Poincare gives sum(-1)^k N_k=sum(-1)^k beta_k.
With field coefficients, ranks are simpler to compute but torsion is lost.
The project requests integral local homology; a mod-2 calculation is not a
silent substitute for canonical integral stratification.

The link of simplex a contains simplices b disjoint from a such that a union b
is a simplex. For x in the interior of a p-simplex, local homology obeys
H_i(K,K minus x)=reduced H_(i-p-1)(link(a)). At a regular interior point of
a 3-manifold this is Z in degree 3 and zero otherwise. Boundary points have
different local groups and must be handled explicitly in ball controls.

The implemented raw-geometry check verifies each vertex link is a connected,
closed triangulated 2-manifold with Euler characteristic 2. It also verifies
that the links of its vertices are connected cycles. These properties imply
the original vertex link is S2 by surface classification. This is a raw
manifold check, not an implementation of the Asai–Shah stratification.

## Microscopic diffusion

For dual adjacency A of a closed strict triangulation, every row has degree 4.
M=(1-rho)I+(rho/4)A with 0<rho<=1 is symmetric, nonnegative and stochastic.
Our implementation also accepts undirected regular graphs of degree d for
synthetic lattice tests, replacing 4 by d. Probability is conserved.
K(s,s0;sigma)=(M^sigma)_(s,s0). Sigma is an integer diffusion step, not a
spacetime time-slice coordinate. Laziness suppresses bipartite/parity effects.

For a set C of microscopic starts, the walk still evolves on the full graph:

    P_C(sigma)=|C|^-1 sum_(s in C) (M^sigma)_(s,s)
             =|C|^-1 Tr(Pi_C M^sigma).

Exact propagation of basis vectors computes diagonal returns for chosen
starts without random-walk noise; sampling starts still has sampling error.
The independent walker implementation samples starts uniformly and records
the return indicator at every step. Its conditional standard error, for
independent walkers with random uniform starts, is sqrt(P(1-P)/W).

Rademacher probes z with zero entries outside C satisfy E[zz^T]=Pi_C.
Thus E[z^T M^sigma z]/|C|=P_C(sigma). The program retains individual probe
curves, permitting uncertainty propagation. Unbiased return estimation does
not make a nonlinear derivative estimator unbiased. Negative/noisy return
estimates are invalid inputs to logarithmic differentiation and are flagged.

Ds=-2 d(log P)/d(log sigma). The literature finite difference used here is

    Ds(sigma)=-sigma [P(sigma+1)-P(sigma-1)]/P(sigma).

Sigma=0 and the final point lack this central difference and are NaN. The
secondary local-polynomial estimator fits log P against log(sigma/sigma0)
and returns minus twice the linear coefficient. Its window is a declared
analysis choice. Curves at very small sigma may exhibit lattice oscillation;
large sigma approaches the finite-volume stationary return 1/N3 and Ds=0.

Cooperman's ensemble estimator averages Ds(T) over configurations. The brief's
primary estimator differentiates the ensemble mean P. Differentiation and
averaging these nonlinear expressions do not commute. Both are exported.

## Planned effective topology contract

Separated vertex seeds induce a graph-distance Voronoi partition. A recorded
tie rule must preserve connected cells, and delta=1 must give the identity.
The 3D coarse dual must retain each connected interface component separately:
cell regions map to vertices, pair interfaces to edges, triple junctions to
faces and quadruple junctions to 3-cells. Cell labels alone do not encode
interface multiplicity or attaching maps. A simple graph nerve is insufficient.

For a regular CW complex, the order complex of the face poset gives its
barycentric subdivision: vertices correspond to cells and chains to simplices.
For nonregular attaching maps, including a loop with both endpoints identified,
the bare face poset can lose topology. For example, one vertex and one loop
edge produce an interval as the ordinary order complex, not a circle. Therefore
the brief's blanket subdivision statement requires a regularity proof or an
incidence-category/attaching-map construction. This remains a research gate.

The canonical stratification is not determined by Betti numbers alone: the
local homology sheaf and its incidence maps must be locally constant on each
stratum, with recursive treatment of the remainder. In particular, a pointwise
test of local ranks is not by itself the cited canonical algorithm.

The required microscopic preimage map must record all intersected coarse cells
and strata. A primary singular start intersects a nonregular coarse stratum;
regular starts map entirely into regular structure. Ambiguity, boundaries and
empty classes must be explicit. d_Q is multi-source shortest dual-graph distance
to the singular preimage, not distance on the coarse dual.

## Planned inference contract

The primary effect is A(delta)=mean_(sigma in U)[Ds_R-Ds_Q]. U and the primary
delta range must be frozen from baseline/pilot criteria before production.
The directional hypothesis is A>0; the null is A=0. Report raw returns as well
as both derivatives, class counts, effect sizes, intervals and all failures.

A bootstrap draw resamples independent configurations, then coarse seed
realizations where needed, then diffusion uncertainty. Each draw recomputes
class return means, derivatives and A. Dependent MCMC samples require adequate
spacing or a block bootstrap, not an independence assumption. A 95% percentile
interval is the 2.5th to 97.5th percentile of the resulting effect distribution.
The implemented preliminary autocorrelation uses an initial-positive paired
sequence, tau_int=1/2+sum rho_lag and ESS=n/(2 tau_int); short chains can
underestimate tau. Diagnostic screens do not prove equilibrium.

Within-configuration permutations preserve class counts (and, for adjusted
tests, matching strata). A one-sided Monte Carlo p-value is
(1+number of A_perm >= A_observed)/(1+number of permutations). Exchangeability
must be justified; spatially correlated labels can invalidate a naive shuffle.
Geometry matching and configuration-grouped cross-validation are required
supporting analyses, not substitutes for the primary effect.

Within a single configuration partition, P_all=f_R P_R+f_Q P_Q exactly.
For an equally weighted configuration ensemble with varying fractions, use
mean_j[f_Rj P_Rj+f_Qj P_Qj], not mean(f_R)*mean(P_R). A site-weighted ensemble
has a different definition. In differential form, Ds_all=w_R(sigma) Ds_R +
w_Q(sigma) Ds_Q with w_C=f_C P_C/P_all. The relevant weights depend on return
probabilities, not just site abundance. Even a small f_Q can matter if P_Q/P_R
is very large; rarity alone cannot rule out a contribution.

## Sources

[Simulation, equations 23–30](https://arxiv.org/abs/2310.16744);
[spectral scaling, equations 3.6–3.12](https://arxiv.org/abs/1711.02685);
[effective topology](https://arxiv.org/abs/2510.05695);
[canonical stratification](https://arxiv.org/abs/1808.06568).
