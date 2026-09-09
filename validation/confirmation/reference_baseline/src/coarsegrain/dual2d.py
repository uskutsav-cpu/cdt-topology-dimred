"""Incidence-preserving 2D Voronoi dual, arXiv:2510.05695 section 4.3.

A dual edge is a connected boundary SEGMENT, not merely a color pair.
Parallel edges and repeated triangles (pillows) remain distinct cells.
Only regular triangular cells with distinct corners are supported here;
looped/nonregular attaching maps are rejected rather than silently collapsed.
"""
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from numbers import Integral
from topology import SimplicialComplex, rank_columns, prime_field
from .voronoi import distances


@dataclass(frozen=True)
class CellComplex2D:
    vertices: tuple
    edges: tuple
    faces: tuple

    def __post_init__(self):
        if (any(isinstance(v, bool) or not isinstance(v, Integral) for v in self.vertices)
                or len(set(self.vertices)) != len(self.vertices)):
            raise ValueError('distinct integer vertices required')
        known = set(self.vertices)
        for edge in self.edges:
            if len(edge) != 2 or edge[0] == edge[1] or not set(edge) <= known:
                raise ValueError('edges require two distinct existing endpoints; loops unsupported')
        for face in self.faces:
            if (len(face) != 3 or len(set(face)) != 3
                    or any(not isinstance(e, Integral) or not 0 <= e < len(self.edges) for e in face)):
                raise ValueError('face requires three distinct valid edge IDs')
            pairs = {tuple(sorted(self.edges[e])) for e in face}
            vs = {v for e in face for v in self.edges[e]}
            if len(vs) != 3 or pairs != set(combinations(sorted(vs), 2)):
                raise ValueError('face closure must be an embedded triangular disk')

    def betti(self, p=2):
        p = prime_field(p)
        vid = {v: i for i, v in enumerate(self.vertices)}
        d1 = [{vid[a]: -1, vid[b]: 1} for a, b in map(sorted, self.edges)]
        d2 = []
        for face in self.faces:
            a, b, c = sorted({v for e in face for v in self.edges[e]})
            ids = {tuple(sorted(self.edges[e])): e for e in face}
            d2.append({ids[(b, c)]: 1, ids[(a, c)]: -1, ids[(a, b)]: 1})
        r1, r2 = rank_columns(d1, p), rank_columns(d2, p)
        return (len(self.vertices) - r1, len(self.edges) - r1 - r2, len(self.faces) - r2)

    def subdivision(self):
        """Safe because __post_init__ checks embedded regular cell closures."""
        vid = {v: i for i, v in enumerate(self.vertices)}
        n0, n1 = len(vid), len(self.edges)
        facets = [(i,) for i in range(n0)]
        for i, edge in enumerate(self.edges):
            facets.extend((vid[v], n0 + i) for v in edge)
        for j, face in enumerate(self.faces):
            for i in face:
                facets.extend((vid[v], n0 + i, n0 + n1 + j) for v in self.edges[i])
        return SimplicialComplex(facets)

    def as_dict(self):
        return {'vertices': list(self.vertices), 'edges': [list(e) for e in self.edges],
                'faces': [list(f) for f in self.faces],
                'representation': 'regular_2d_incidence_complex',
                'preserves_cell_multiplicity': True}


def _check_surface(complex_):
    if complex_.dimension != 2 or any(len(s) != 3 for s in complex_.facets):
        raise ValueError('pure triangulated closed surface required')
    incident = defaultdict(list)
    for i, tri in enumerate(complex_.groups[2]):
        for edge in combinations(tri, 2):
            incident[edge].append(i)
    if any(len(v) != 2 for v in incident.values()):
        raise ValueError('each fine edge must have two incident triangles')
    for v in complex_.vertices:
        link = complex_.link((v,)).adjacency()
        if any(len(n) != 2 for n in link.values()) or len(distances(link, [min(link)])) != len(link):
            raise ValueError('fine vertex links must be connected circles')
    graph = complex_.adjacency()
    if len(distances(graph, [min(graph)])) != len(graph):
        raise ValueError('connected surface required')
    return incident, graph


def coarsegrain_surface(complex_, labels):
    """Return (dual, provenance) for a connected vertex coloring of a surface.

    The provenance records fine-edge components and each triple-point triangle.
    It is NOT a 3D dual or a completed CDT/EDT ensemble reproduction.
    """
    incident, graph = _check_surface(complex_)
    if set(labels) != set(complex_.vertices):
        raise ValueError('one label for every fine vertex is required')
    if any(isinstance(c, bool) or not isinstance(c, Integral) for c in labels.values()):
        raise ValueError('integer labels required')
    for color in set(labels.values()):
        members = {v for v in graph if labels[v] == color}
        subgraph = {v: tuple(u for u in graph[v] if u in members) for v in members}
        if len(distances(subgraph, [min(members)])) != len(members):
            raise ValueError('Voronoi color cells must be connected')
    boundary = sorted(e for e in incident if labels[e[0]] != labels[e[1]])
    parent = {e: e for e in boundary}
    def find(e):
        while parent[e] != e:
            parent[e] = parent[parent[e]]
            e = parent[e]
        return e
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)
    triples = []
    for tri in complex_.groups[2]:
        crossing = [e for e in combinations(tri, 2) if e in parent]
        if len(crossing) == 2:
            union(*crossing)  # interior of one pairwise interface
        elif len(crossing) == 3:
            triples.append((tri, crossing))  # do NOT merge across a triple point
        elif crossing:
            raise RuntimeError('impossible triangle coloring')
    components = defaultdict(list)
    for e in boundary:
        components[find(e)].append(e)
    groups = sorted(components.values(), key=lambda g: tuple(g))
    edge_id = {e: i for i, group in enumerate(groups) for e in group}
    dual_edges = []
    for group in groups:
        pairs = {tuple(sorted((labels[a], labels[b]))) for a, b in group}
        if len(pairs) != 1:
            raise RuntimeError('interface mixed distinct color pairs')
        dual_edges.append(next(iter(pairs)))
    faces = tuple(tuple(edge_id[e] for e in crossing) for _, crossing in triples)
    dual = CellComplex2D(tuple(sorted(set(labels.values()))), tuple(dual_edges), faces)
    provenance = {'fine_boundary_edges_by_dual_edge': [[list(e) for e in g] for g in groups],
                  'fine_triangle_by_dual_face': [list(t) for t, _ in triples],
                  'parallel_edge_excess': len(dual.edges) - len(set(dual.edges)),
                  'repeated_face_vertex_sets': len(dual.faces) - len({
                      tuple(sorted({v for e in f for v in dual.edges[e]})) for f in faces}),
                  'scope': '2D construction; ensemble reproduction not established'}
    return dual, provenance
