"""Recursive integral canonical labels for abstract complexes of dimension <=3.

Implements the upward-closed generic-locus iteration of Asai--Shah,
arXiv:1808.06568v3, Algorithm 4.13. Two independent membership backends:
exact Smith-normal-form local homology and combinatorial sphere links.
Optional mapping-cone audits explicitly check integral local incidence maps.
This is not an implementation of the localized exit-path infinity-category.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass

from topology import SimplicialComplex
from topology.integral import AbelianGroup, ExactBudget, IntegralLocalSystem


def _connected(adjacency):
    if not adjacency:
        return False
    seen = {next(iter(adjacency))}
    queue = deque(seen)
    while queue:
        for v in adjacency[queue.popleft()]:
            if v not in seen:
                seen.add(v)
                queue.append(v)
    return len(seen) == len(adjacency)


def _cycle(complex_):
    adjacency = complex_.adjacency()
    return (complex_.dimension == 1 and all(len(s) == 2 for s in complex_.facets)
            and _connected(adjacency) and all(len(a) == 2 for a in adjacency.values()))


def sphere_link(complex_, simplex, ambient_dimension):
    """Exact low-dimensional sphere recognition, not a Betti-only heuristic.

    For S2, require a connected closed combinatorial surface with chi=2.
    Surface classification then certifies S2 (and integral sphere homology).
    """
    codimension = ambient_dimension - len(simplex) + 1
    link = complex_.link(simplex)
    if codimension == 0:
        return not link.simplices
    if codimension == 1:
        return link.dimension == 0 and len(link.vertices) == 2
    if codimension == 2:
        return _cycle(link)
    if codimension != 3:
        raise ValueError("sphere-link fast path supports codimension <=3")
    if (link.dimension != 2 or any(len(s) != 3 for s in link.facets)
            or link.euler != 2 or not _connected(link.adjacency())):
        return False
    edge_counts = Counter(tuple(sorted((t[i], t[j]))) for t in link.groups[2]
                          for i, j in ((0, 1), (0, 2), (1, 2)))
    return (all(n == 2 for n in edge_counts.values())
            and all(_cycle(link.link((v,))) for v in link.vertices))


@dataclass
class Stratification:
    dimension: int
    simplex_dimension: dict
    simplex_component: dict
    stages: list
    method: str
    incidence_certificates: list

    def as_dict(self):
        cells = sorted(self.simplex_dimension, key=lambda s: (len(s), s))
        return {"schema": "cdt-integral-stratification-v1", "method": self.method,
                "ambient_dimension": self.dimension,
                "cells": [{"simplex": list(s), "stratum_dimension": self.simplex_dimension[s],
                           "component": self.simplex_component[s]} for s in cells],
                "stages": self.stages, "incidence_certificates": self.incidence_certificates,
                "physics_validation": "NOT_ESTABLISHED"}

    @property
    def singular_simplices(self):
        return tuple(s for s, d in self.simplex_dimension.items() if d < self.dimension)


def canonical_stratification(complex_: SimplicialComplex, *, method="combinatorial",
                             audit_incidence=False, budget: ExactBudget | None = None,
                             max_audit_maps=10000):
    if method not in ("integral", "combinatorial"):
        raise ValueError("method must be integral or combinatorial")
    if not isinstance(audit_incidence, bool):
        raise ValueError("audit_incidence must be boolean")
    if not isinstance(max_audit_maps, int) or isinstance(max_audit_maps, bool) or max_audit_maps < 0:
        raise ValueError("max_audit_maps must be a nonnegative integer")
    remaining = set(complex_.simplices)
    labels, components, stages, certificates = {}, {}, [], []
    next_component = 0
    while remaining:
        current = SimplicialComplex(sorted(remaining))
        d = current.dimension
        cofaces = defaultdict(list)
        for t in current.simplices:
            if len(t) > 1:
                for i in range(len(t)):
                    cofaces[t[:i] + t[i + 1:]].append(t)
        generic = set()
        local = IntegralLocalSystem(current, budget=budget)
        tested = skipped = 0
        for s in reversed(current.simplices):
            if any(t not in generic for t in cofaces[s]):
                skipped += 1
                continue
            tested += 1
            if method == "integral":
                expected = tuple(AbelianGroup(int(k == d)) for k in range(d + 1))
                good = local.homology(s) == expected
            else:
                good = sphere_link(current, s, d)
            if good:
                generic.add(s)
        if not generic or any(t not in generic for s in generic for t in cofaces[s]):
            raise ArithmeticError("generic locus must be nonempty and upward closed")
        adjacency = {s: set() for s in generic}
        audits_before = len(certificates)
        for s in sorted(generic, key=lambda a: (len(a), a)):
            for t in cofaces[s]:
                adjacency[s].add(t)
                adjacency[t].add(s)
                if audit_incidence:
                    if len(certificates) >= max_audit_maps:
                        raise MemoryError("incidence audit budget exceeded; no partial certificate issued")
                    certificate = local.incidence(s, t).certificate()
                    if not certificate["is_integral_homology_isomorphism"]:
                        raise ArithmeticError(f"nonconstant local system on proposed stratum: {s} -> {t}")
                    certificates.append({"stage_dimension": d, "face": list(s), "coface": list(t),
                                         **certificate})
        unseen = set(generic)
        stage_components = 0
        while unseen:
            start = min(unseen, key=lambda s: (len(s), s))
            unseen.remove(start)
            queue = deque([start])
            while queue:
                s = queue.popleft()
                labels[s], components[s] = d, next_component
                for t in adjacency[s]:
                    if t in unseen:
                        unseen.remove(t)
                        queue.append(t)
            next_component += 1
            stage_components += 1
        stages.append({"dimension": d, "remaining_cells": len(remaining),
                       "generic_cells": len(generic), "components": stage_components,
                       "local_tests": tested, "skipped_nongeneric_coface": skipped,
                       "integral_incidence_maps_audited": len(certificates) - audits_before})
        remaining -= generic
        if any(len(s) - 1 >= d for s in remaining):
            raise ArithmeticError("dimension did not decrease")
    # Poset monotonicity is a required output invariant.
    for s, label in labels.items():
        for i in range(len(s)):
            face = s[:i] + s[i + 1:]
            if face and labels[face] > label:
                raise ArithmeticError("stratum labels are not order preserving")
    return Stratification(complex_.dimension, labels, components, stages, method, certificates)
