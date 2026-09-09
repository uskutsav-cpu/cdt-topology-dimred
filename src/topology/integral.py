"""Exact integral chain homology and local incidence-map certificates.

The reference backend uses Smith normal forms over ZZ, not floating ranks or
mod-p substitutes. Dense-work budgets deliberately limit its use to validation
and moderate local complexes. See docs/INTEGRAL_METHODS.md for the splitting
argument that avoids computing unimodular changes of basis.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from numbers import Integral
from typing import Mapping, Sequence

from sympy import ImmutableSparseMatrix, Matrix, MatrixBase, ZZ
from sympy.matrices.normalforms import smith_normal_form

from topology import SimplicialComplex, _simplex, boundary_columns


def integer(value, name="integer", minimum=0):
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


@dataclass(frozen=True)
class ExactBudget:
    max_generators: int = 20000
    max_matrix_entries: int = 250000

    def __post_init__(self):
        integer(self.max_generators, "max_generators", 1)
        integer(self.max_matrix_entries, "max_matrix_entries", 1)

    def check(self, rows, cols):
        if rows * cols > self.max_matrix_entries:
            raise MemoryError(f"exact matrix budget exceeded: {rows} x {cols}")


@dataclass(frozen=True)
class AbelianGroup:
    """Z^free_rank plus cyclic groups with positive invariant factors > 1."""
    free_rank: int = 0
    torsion: tuple[int, ...] = ()

    def __post_init__(self):
        integer(self.free_rank, "free_rank")
        torsion = tuple(integer(x, "torsion invariant", 2) for x in self.torsion)
        if any(b % a for a, b in zip(torsion, torsion[1:])):
            raise ValueError("torsion factors must form a divisibility chain")
        object.__setattr__(self, "torsion", torsion)

    @property
    def is_zero(self):
        return self.free_rank == 0 and not self.torsion

    def as_dict(self):
        return {"free_rank": self.free_rank, "torsion": list(self.torsion)}

    def __str__(self):
        terms = (["Z" if self.free_rank == 1 else f"Z^{self.free_rank}"]
                 if self.free_rank else [])
        terms.extend(f"Z/{x}" for x in self.torsion)
        return " + ".join(terms) or "0"


def _exact_matrix(value, rows, cols, budget):
    budget.check(rows, cols)
    if isinstance(value, MatrixBase):
        mat = value
    elif hasattr(value, "tolist"):
        mat = Matrix(value.tolist())
    else:
        mat = Matrix(value)
    if mat.shape != (rows, cols):
        raise ValueError(f"expected matrix shape {(rows, cols)}, got {mat.shape}")
    if any(x.is_Integer is not True for x in mat):
        raise ValueError("matrix coefficients must be exact integers (no floats)")
    return ImmutableSparseMatrix(mat)


def _smith(matrix, budget):
    rows, cols = matrix.shape
    budget.check(rows, cols)
    if not rows or not cols or not matrix.todok():
        return ()
    diagonal = smith_normal_form(Matrix(matrix), domain=ZZ)
    values = tuple(abs(int(diagonal[i, i])) for i in range(min(rows, cols))
                   if diagonal[i, i] != 0)
    if any(b % a for a, b in zip(values, values[1:])):
        raise ArithmeticError("invalid Smith divisibility chain")
    return values


class IntegralChainComplex:
    """A finite free nonnegative-degree chain complex with immutable matrices.

    dimensions[k] is rank C_k; boundaries[k] has shape (C_{k-1}, C_k).
    Omitted matrices are zero. Every boundary product is checked exactly.
    """
    def __init__(self, dimensions: Sequence[int], boundaries: Mapping[int, object] | None = None,
                 *, budget: ExactBudget | None = None):
        self.budget = budget or ExactBudget()
        self.dimensions = tuple(integer(n, "chain rank") for n in dimensions)
        if sum(self.dimensions) > self.budget.max_generators:
            raise MemoryError("exact generator budget exceeded")
        boundaries = dict(boundaries or {})
        for k in boundaries:
            integer(k, "boundary degree", 1)
            if k >= len(self.dimensions):
                raise ValueError("boundary degree outside chain complex")
        mats = []
        for k, cols in enumerate(self.dimensions):
            rows = self.dimensions[k - 1] if k else 0
            self.budget.check(rows, cols)
            value = boundaries.get(k, ImmutableSparseMatrix(rows, cols, {}))
            mats.append(_exact_matrix(value, rows, cols, self.budget))
        self.boundaries = tuple(mats)
        for k in range(2, len(mats)):
            if (mats[k - 1] * mats[k]).todok():
                raise ValueError(f"boundary squared is nonzero in degree {k}")

    def rank(self, k):
        return self.dimensions[k] if 0 <= k < len(self.dimensions) else 0

    def boundary(self, k):
        if 0 <= k < len(self.boundaries):
            return self.boundaries[k]
        return ImmutableSparseMatrix(self.rank(k - 1), self.rank(k), {})

    @cached_property
    def smith_diagonals(self):
        return tuple(_smith(a, self.budget) for a in self.boundaries)

    @cached_property
    def homology(self):
        result = []
        for k, n in enumerate(self.dimensions):
            before = self.smith_diagonals[k]
            after = self.smith_diagonals[k + 1] if k + 1 < len(self.dimensions) else ()
            free = n - len(before) - len(after)
            if free < 0:
                raise ArithmeticError("negative homology rank")
            result.append(AbelianGroup(free, tuple(x for x in after if x > 1)))
        return tuple(result)

    @property
    def is_acyclic(self):
        return all(h.is_zero for h in self.homology)


def chain_from_groups(groups, dimension, *, budget=None):
    budget = budget or ExactBudget()
    dimensions = tuple(len(groups.get(k, ())) for k in range(dimension + 1))
    if sum(dimensions) > budget.max_generators:
        raise MemoryError("exact generator budget exceeded")
    boundaries = {}
    for k in range(1, dimension + 1):
        rows, cols = dimensions[k - 1], dimensions[k]
        budget.check(rows, cols)
        entries = {(i, j): a for j, col in enumerate(boundary_columns(groups, k))
                   for i, a in col.items()}
        boundaries[k] = ImmutableSparseMatrix(rows, cols, entries)
    return IntegralChainComplex(dimensions, boundaries, budget=budget)


def integral_homology(complex_: SimplicialComplex, *, budget=None):
    return chain_from_groups(complex_.groups, complex_.dimension, budget=budget).homology


def local_homology_via_link(complex_: SimplicialComplex, simplex, *, budget=None):
    simplex = _simplex(simplex)
    link = complex_.link(simplex)  # validates membership even for the void link
    output = [AbelianGroup() for _ in range(complex_.dimension + 1)]
    if not link.simplices:
        output[len(simplex) - 1] = AbelianGroup(1)
    else:
        groups = list(integral_homology(link, budget=budget))
        groups[0] = AbelianGroup(groups[0].free_rank - 1, groups[0].torsion)
        for k, group in enumerate(groups):
            output[k + len(simplex)] = group
    return tuple(output)


class ChainMap:
    """Exact chain map and mapping-cone test of induced integral isomorphisms."""
    def __init__(self, source: IntegralChainComplex, target: IntegralChainComplex,
                 matrices: Mapping[int, object], *, budget=None):
        self.source, self.target = source, target
        self.budget = budget or source.budget
        top = max(len(source.dimensions), len(target.dimensions))
        for k in matrices:
            integer(k, "map degree")
            if k >= top:
                raise ValueError("map degree outside chain complexes")
        output = []
        for k in range(top):
            rows, cols = target.rank(k), source.rank(k)
            value = matrices.get(k, ImmutableSparseMatrix(rows, cols, {}))
            output.append(_exact_matrix(value, rows, cols, self.budget))
        self.matrices = tuple(output)
        for k in range(1, top):
            if (target.boundary(k) * self.matrix(k)
                    - self.matrix(k - 1) * source.boundary(k)).todok():
                raise ValueError(f"not a chain map in degree {k}")

    def matrix(self, k):
        if 0 <= k < len(self.matrices):
            return self.matrices[k]
        return ImmutableSparseMatrix(self.target.rank(k), self.source.rank(k), {})

    @cached_property
    def cone(self):
        top = max(len(self.target.dimensions), len(self.source.dimensions) + 1)
        dims = tuple(self.target.rank(k) + self.source.rank(k - 1) for k in range(top))
        boundaries = {}
        for k in range(1, top):
            rows, cols = dims[k - 1], dims[k]
            self.budget.check(rows, cols)
            entries = dict(self.target.boundary(k).todok())
            col_offset, row_offset = self.target.rank(k), self.target.rank(k - 1)
            for (i, j), a in self.matrix(k - 1).todok().items():
                entries[i, j + col_offset] = a
            for (i, j), a in self.source.boundary(k - 1).todok().items():
                entries[i + row_offset, j + col_offset] = -a
            boundaries[k] = ImmutableSparseMatrix(rows, cols, entries)
        return IntegralChainComplex(dims, boundaries, budget=self.budget)

    @property
    def is_homology_isomorphism(self):
        return self.cone.is_acyclic

    def certificate(self):
        return {"is_integral_homology_isomorphism": self.is_homology_isomorphism,
                "cone_homology": [h.as_dict() for h in self.cone.homology],
                "source_homology": [h.as_dict() for h in self.source.homology],
                "target_homology": [h.as_dict() for h in self.target.homology]}


class IntegralLocalSystem:
    """C(K,costar(s)) and the face-to-coface quotient chain projections."""
    def __init__(self, complex_: SimplicialComplex, *, budget=None):
        self.complex = complex_
        self.budget = budget or ExactBudget()
        self._groups, self._chains = {}, {}

    def groups(self, simplex):
        s = _simplex(simplex)
        if s not in self._groups:
            cofaces = self.complex.cofaces(s)
            self._groups[s] = {k: tuple(t for t in cofaces if len(t) == k + 1)
                               for k in range(self.complex.dimension + 1)}
        return self._groups[s]

    def chain(self, simplex):
        s = _simplex(simplex)
        if s not in self._chains:
            self._chains[s] = chain_from_groups(self.groups(s), self.complex.dimension,
                                               budget=self.budget)
        return self._chains[s]

    def homology(self, simplex):
        return self.chain(simplex).homology

    def incidence(self, face, coface):
        s, t = _simplex(face), _simplex(coface)
        if not set(s).issubset(t):
            raise ValueError("incidence requires face <= coface")
        source, target = self.chain(s), self.chain(t)
        source_groups, target_groups = self.groups(s), self.groups(t)
        matrices = {}
        for k in range(self.complex.dimension + 1):
            columns = {simplex: j for j, simplex in enumerate(source_groups[k])}
            matrices[k] = ImmutableSparseMatrix(target.rank(k), source.rank(k),
                {(i, columns[cell]): 1 for i, cell in enumerate(target_groups[k])})
        return ChainMap(source, target, matrices, budget=self.budget)
