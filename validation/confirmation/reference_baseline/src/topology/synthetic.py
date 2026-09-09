"""Small exact fixtures. None is a sampled quantum-gravity ensemble."""
from itertools import combinations, permutations, product
from . import SimplicialComplex


def sphere(dimension):
    if dimension not in (1, 2, 3):
        raise ValueError('sphere dimension must be 1, 2, or 3')
    return SimplicialComplex(combinations(range(dimension + 2), dimension + 1))


def ball(dimension=3):
    if dimension not in (1, 2, 3):
        raise ValueError('ball dimension must be 1, 2, or 3')
    return SimplicialComplex([range(dimension + 1)])


def pinched_spheres(dimension=3):
    """Wedge of two spheres at vertex 0; not a manifold at that vertex."""
    first = sphere(dimension)
    offset = dimension + 1
    second = [tuple(0 if v == 0 else v + offset for v in s) for s in first.facets]
    return SimplicialComplex([*first.facets, *second])


def torus(dimension=2, side=4):
    """Periodic Freudenthal triangulation of a square/cubic grid."""
    if dimension not in (2, 3) or not isinstance(side, int) or side < 3:
        raise ValueError('torus requires dimension 2 or 3 and integer side >= 3')
    def vertex(q):
        return sum((q[i] % side) * side ** i for i in range(dimension))
    facets = []
    for q in product(range(side), repeat=dimension):
        for order in permutations(range(dimension)):
            x = list(q)
            s = [vertex(x)]
            for axis in order:
                x[axis] += 1
                s.append(vertex(x))
            facets.append(s)
    return SimplicialComplex(facets)
