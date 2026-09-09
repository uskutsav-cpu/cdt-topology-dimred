"""Exact finite-field homology on genuine abstract simplicial complexes.

This is a reference/test backend, NOT the integral Asai--Shah canonical
stratification algorithm. Equal local Betti vectors do not establish a stratum
or prove that a neighborhood is a topological manifold.
"""
from collections import defaultdict
from itertools import combinations, permutations
from math import isqrt
from numbers import Integral


def prime_field(p):
    if isinstance(p, bool) or not isinstance(p, Integral) or p < 2:
        raise ValueError('coefficient modulus must be prime')
    p = int(p)
    if any(p % d == 0 for d in range(2, isqrt(p) + 1)):
        raise ValueError('coefficient modulus must be prime')
    return p


def rank_columns(columns, p=2):
    """Exact rank of sparse columns {row: coefficient} over F_p."""
    p = prime_field(p)
    pivots = {}
    if p == 2:
        for col in columns:
            bits = 0
            for i, a in col.items():
                if a % 2:
                    bits ^= 1 << i
            while bits:
                j = bits.bit_length() - 1
                if j not in pivots:
                    pivots[j] = bits
                    break
                bits ^= pivots[j]
    else:
        for col in columns:
            c = {i: a % p for i, a in col.items() if a % p}
            while c:
                j = max(c)
                if j not in pivots:
                    inv = pow(c[j], -1, p)
                    pivots[j] = {i: a * inv % p for i, a in c.items()}
                    break
                scale = c[j]
                for i, a in pivots[j].items():
                    value = (c.get(i, 0) - scale * a) % p
                    if value:
                        c[i] = value
                    else:
                        c.pop(i, None)
    return len(pivots)


def _simplex(vertices):
    vertices = tuple(vertices)
    if any(isinstance(v, bool) or not isinstance(v, Integral) for v in vertices):
        raise ValueError('vertex IDs must be integers')
    if len(set(vertices)) != len(vertices):
        raise ValueError('repeated vertices: not an abstract simplex')
    return tuple(sorted(map(int, vertices)))


def boundary_columns(groups, k):
    """Oriented quotient boundary; missing faces are zero in a relative complex."""
    rows = {s: i for i, s in enumerate(groups.get(k - 1, ())) }
    for s in groups.get(k, ()):
        col = {}
        if k:
            for j in range(len(s)):
                face = s[:j] + s[j + 1:]
                if face in rows:
                    col[rows[face]] = (-1) ** j
        yield col


def _betti(groups, dimension, p):
    ranks = {k: rank_columns(boundary_columns(groups, k), p)
             for k in range(1, dimension + 1)}
    return tuple(len(groups.get(k, ())) - ranks.get(k, 0) - ranks.get(k + 1, 0)
                 for k in range(dimension + 1))


class SimplicialComplex:
    """Face closure of simplices; duplicate input cells are rejected, not merged.

    Parallel cells/pillows must first be represented by explicit incidence data.
    A configurable face limit prevents unbounded reference-backend allocation.
    """
    def __init__(self, simplices=(), *, max_faces=500000):
        if not isinstance(max_faces, Integral) or max_faces < 1:
            raise ValueError('max_faces must be a positive integer')
        cells, seen = set(), set()
        for row in simplices:
            s = _simplex(row)
            if not s:
                raise ValueError('empty input simplex is not a cell')
            if s in seen:
                raise ValueError('duplicate input simplex; possible lost cell multiplicity')
            seen.add(s)
            if len(s) > 4:
                raise ValueError('reference backend supports dimension <= 3')
            for n in range(1, len(s) + 1):
                cells.update(combinations(s, n))
                if len(cells) > max_faces:
                    raise MemoryError('face limit exceeded; select a scalable backend')
        self.simplices = tuple(sorted(cells, key=lambda s: (len(s), s)))
        self._set = frozenset(cells)
        self.groups = {k: tuple(s for s in self.simplices if len(s) == k + 1)
                       for k in range(max(map(len, cells), default=0))}
        self.dimension = max(self.groups, default=-1)
        nonmaximal = {s[:i] + s[i + 1:] for s in cells for i in range(len(s))}
        self.facets = tuple(s for s in self.simplices if s not in nonmaximal)
        self.vertices = tuple(s[0] for s in self.groups.get(0, ()))
        self._vertex_cofaces = defaultdict(set)
        for s in self.simplices:
            for v in s:
                self._vertex_cofaces[v].add(s)

    def betti(self, p=2):
        return _betti(self.groups, self.dimension, prime_field(p))

    @property
    def euler(self):
        return sum((-1) ** k * len(s) for k, s in self.groups.items())

    def cofaces(self, simplex):
        s = _simplex(simplex)
        if not s or s not in self._set:
            raise ValueError('simplex must be a nonempty cell of this complex')
        pool = min((self._vertex_cofaces[v] for v in s), key=len)
        return tuple(sorted((t for t in pool if set(s).issubset(t)),
                            key=lambda t: (len(t), t)))

    def link(self, simplex):
        cell = _simplex(simplex)
        s = frozenset(cell)
        faces = {tuple(v for v in t if v not in s) for t in self.cofaces(cell)}
        faces.discard(())
        return SimplicialComplex(sorted(faces))

    def local_betti(self, simplex, p=2):
        """H_i(K, costar_K(simplex); F_p), i=0,...,dim K.

        This is the point-local homology at the interior of the simplex.
        The costar consists of all cells NOT containing the simplex, and is
        a subcomplex. Quotient boundaries therefore retain only cofaces.
        """
        groups = defaultdict(list)
        for s in self.cofaces(simplex):
            groups[len(s) - 1].append(s)
        return _betti(groups, self.dimension, prime_field(p))

    def local_betti_via_link(self, simplex, p=2):
        """Independent shifted reduced-link formula, including the void link."""
        p = prime_field(p)
        s = _simplex(simplex)
        link = self.link(s)
        out = [0] * (self.dimension + 1)
        if not link.simplices:
            out[len(s) - 1] = 1  # reduced H_{-1}(void)=F_p
        else:
            reduced = list(link.betti(p))
            reduced[0] -= 1
            for j, value in enumerate(reduced):
                out[j + len(s)] = value
        return tuple(out)

    def adjacency(self):
        graph = {v: set() for v in self.vertices}
        for a, b in self.groups.get(1, ()):
            graph[a].add(b)
            graph[b].add(a)
        return {v: tuple(sorted(n)) for v, n in graph.items()}

    def barycentric_subdivision(self, *, max_faces=500000):
        """Valid for THIS abstract complex, not arbitrary looped CW complexes."""
        ids = {s: i for i, s in enumerate(self.simplices)}
        facets = []
        for s in self.facets:
            for order in permutations(s):
                facets.append(tuple(ids[tuple(sorted(order[:i]))]
                                    for i in range(1, len(s) + 1)))
        return SimplicialComplex(facets, max_faces=max_faces)

    def check_boundary_squared(self, p=2):
        p = prime_field(p)
        for k in range(2, self.dimension + 1):
            lower = list(boundary_columns(self.groups, k - 1))
            for col in boundary_columns(self.groups, k):
                result = defaultdict(int)
                for j, a in col.items():
                    for i, b in lower[j].items():
                        result[i] += a * b
                if any(v % p for v in result.values()):
                    return False
        return True
