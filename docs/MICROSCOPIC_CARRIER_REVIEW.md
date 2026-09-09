# Experimental microscopic carrier relation — review required

The new implementation audits and uses the existing 3D construction's fine
interface triangles, junction edges and four-colour tetrahedra. Region labels
supply touched coarse vertices. Each fine tetrahedron retains every touched
coarse open cell, including parallel interface components; it is not assigned
only one nearest coarse label.

Canonical strata are computed on the regular-cell flag subdivision. Every
subdivision simplex is classified by its maximal coarse-cell carrier. A coarse
open cell with more than one observed interior stratum dimension is ambiguous.
A fine tetrahedron touching any ambiguous carrier is excluded from both
comparison classes. Otherwise it is singular when any touched coarse cell has
canonical dimension below the intended ambient dimension three. A coarse dual
that collapses to a graph or point is not relabeled a regular three-manifold.
Distances use the unmodified microscopic tetrahedron-adjacency graph; -1 means
no singular source is reachable. Missing or empty classes are not zero effects.

This is an explicitly defined **incidence-carrier relation**, not a proof of a
continuous fine-to-coarse map and not a validated quantum-gravity observable.
It accepts no diffusion outcomes, so the implemented classification itself is
outcome-blind. Scientific adequacy of the definition is a separate question.

## What the executed toy study found

Across 18 constructions on small triangulated T^3 fixtures (side lengths 3 and
4; coarse scales 1,2,3), identity-scale cases recovered the expected topology
and all-regular labels. Only one construction contained both comparison
classes. Seventeen had an empty regular or singular class and therefore an
undefined conditioned contrast. The one nonempty comparison was a null up to
floating-point error on the homogeneous synthetic microscopic graph.

The coarsest constructions can collapse essentially all fine tetrahedra into
the singular preimage under this rule. This is a warning about scale, sampling,
collapse conventions and the proposed relation, not evidence for or against
quantum-gravity dimensional reduction. It is not acceptable to switch to an
alternative mapping after seeing which one gives a desired effect.

## Decisions that still need independent approval

Compare this relation with actual embeddings or a mathematically specified
map; check how interface and junction collapse handles noncontractible pieces;
validate controlled neck-width and refinement behavior over larger synthetic
families; assess seed sensitivity; and specify boundaries, ambiguity and the
allowed coarse-scale range before production. The 2D paper's CDT/EDT ensemble
reproduction is still required. The 3D extension cannot inherit that validation
by analogy alone.

Reference for the effective-topology construction and its 2D validation:
https://arxiv.org/html/2510.05695v1

No approval flag, production-gate PASS, or continuous-map certificate is set by
this module or by the saved study. The default gates remain NOT_ESTABLISHED.
