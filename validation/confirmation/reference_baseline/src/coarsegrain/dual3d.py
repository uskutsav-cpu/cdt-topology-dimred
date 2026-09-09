"""EXPERIMENTAL 3D extension: connected PL interface/junction components.

Not a literature-validated 3D effective-topology prescription. Connected
2D interfaces are collapsed to edges and connected 1D triple junctions to
triangles, regardless of their internal topology; that information is retained
in provenance. This choice needs physical/mathematical review before inference.
No CDT production result or canonical stratification is computed here.
"""
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from numbers import Integral
from topology import SimplicialComplex, rank_columns, prime_field
from .dual2d import CellComplex2D, _check_surface


@dataclass(frozen=True)
class CellComplex3D:
    skeleton: CellComplex2D
    tetrahedra: tuple

    def __post_init__(self):
        for tetra in self.tetrahedra:
            if (len(tetra) != 4 or len(set(tetra)) != 4
                    or any(not isinstance(f, Integral) or isinstance(f, bool) or not 0 <= f < len(self.skeleton.faces) for f in tetra)):
                raise ValueError('tetrahedron requires four distinct face IDs')
            edges = {e for f in tetra for e in self.skeleton.faces[f]}
            verts = {v for e in edges for v in self.skeleton.edges[e]}
            corners = [self.face_vertices(f) for f in tetra]
            if (len(verts) != 4 or len(edges) != 6
                    or set(corners) != set(combinations(sorted(verts), 3))
                    or {tuple(sorted(self.skeleton.edges[e])) for e in edges}
                    != set(combinations(sorted(verts), 2))):
                raise ValueError('tetrahedron closure is not an embedded simplex')

    def face_vertices(self, face):
        return tuple(sorted({v for e in self.skeleton.faces[face] for v in self.skeleton.edges[e]}))

    def betti(self, p=2):
        p = prime_field(p)
        b0, b1, b2 = self.skeleton.betti(p)
        d3 = []
        for tetra in self.tetrahedra:
            ids = {self.face_vertices(f): f for f in tetra}
            verts = sorted({v for s in ids for v in s})
            d3.append({ids[tuple(verts[:i] + verts[i + 1:])]: (-1) ** i for i in range(4)})
        r3 = rank_columns(d3, p)
        return b0, b1, b2 - r3, len(self.tetrahedra) - r3

    def subdivision(self, max_faces=500000):
        sk = self.skeleton
        vid = {v: i for i, v in enumerate(sk.vertices)}
        n0, n1, n2 = len(vid), len(sk.edges), len(sk.faces)
        cells = [(i,) for i in range(n0)]
        for e, endpoints in enumerate(sk.edges):
            cells.extend((vid[v], n0 + e) for v in endpoints)
        for f, edges in enumerate(sk.faces):
            for e in edges:
                cells.extend((vid[v], n0 + e, n0 + n1 + f) for v in sk.edges[e])
        for t, faces in enumerate(self.tetrahedra):
            for f in faces:
                for e in sk.faces[f]:
                    cells.extend((vid[v], n0 + e, n0 + n1 + f, n0 + n1 + n2 + t)
                                 for v in sk.edges[e])
        return SimplicialComplex(cells, max_faces=max_faces)

    def as_dict(self):
        return {**self.skeleton.as_dict(), 'tetrahedra': [list(t) for t in self.tetrahedra],
                'representation': 'regular_3d_incidence_complex',
                'method_status': 'EXPERIMENTAL_NOT_PHYSICS_VALIDATED'}


def _components(items, keys, subfaces):
    """Codimension-one adjacency only; point contacts do not merge surfaces."""
    parent = list(range(len(items)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    lookup = {}
    for i, item in enumerate(items):
        for face in subfaces(item):
            key = (keys[i], face)
            if key in lookup:
                a, b = root(i), root(lookup[key])
                parent[max(a, b)] = min(a, b)
            else:
                lookup[key] = i
    groups = defaultdict(list)
    for i in range(len(items)):
        groups[root(i)].append(i)
    groups = sorted(groups.values(), key=lambda g: g[0])
    return groups, {i: g for g, group in enumerate(groups) for i in group}


def coarsegrain_manifold3d(complex_, labels):
    """Explicit candidate 3D dual with full interface provenance on small inputs.

    Starts from an independently checked closed combinatorial 3-manifold.
    No manifold recognition is inferred merely from a local Betti vector.
    """
    if complex_.dimension != 3 or any(len(s) != 4 for s in complex_.facets):
        raise ValueError('pure closed triangulated 3-manifold required')
    incidence = defaultdict(int)
    for tetra in complex_.facets:
        for face in combinations(tetra, 3):
            incidence[face] += 1
    if any(n != 2 for n in incidence.values()):
        raise ValueError('each fine face must have two incident tetrahedra')
    for v in complex_.vertices:
        link = complex_.link((v,))
        _check_surface(link)
        if link.euler != 2:
            raise ValueError('fine vertex link is not a 2-sphere')
    if set(labels) != set(complex_.vertices):
        raise ValueError('one label per vertex required')
    # Reuse the connected-cell contract without assuming the coarse dual is a manifold.
    from .voronoi import distances
    if any(isinstance(c, bool) or not isinstance(c, Integral) for c in labels.values()):
        raise ValueError('integer cell labels required')
    graph = complex_.adjacency()
    if len(distances(graph, [min(graph)])) != len(graph):
        raise ValueError('connected fine manifold required')
    for c in set(labels.values()):
        members = {v for v in graph if labels[v] == c}
        g = {v: tuple(u for u in graph[v] if u in members) for v in members}
        if len(distances(g, [min(g)])) != len(g):
            raise ValueError('disconnected Voronoi cell')
    ids = {s: i for i, s in enumerate(complex_.simplices)}
    tiles, pairs, junctions, triples, quad = [], [], [], [], []
    junction_lookup = {}
    for ti, tetra in enumerate(complex_.facets):
        for face in combinations(tetra, 3):
            colors = tuple(sorted({labels[v] for v in face}))
            if len(colors) == 3:
                junction_lookup[(ti, face)] = len(junctions)
                junctions.append(tuple(sorted((ids[face], ids[tetra]))))
                triples.append(colors)
            for edge in combinations(face, 2):
                pair = tuple(sorted((labels[edge[0]], labels[edge[1]])))
                if pair[0] != pair[1]:
                    tiles.append(tuple(sorted((ids[edge], ids[face], ids[tetra]))))
                    pairs.append(pair)
        if len({labels[v] for v in tetra}) == 4:
            quad.append((ti, tetra))
    surfaces, surface_id = _components(tiles, pairs, lambda s: combinations(s, 2))
    lines, line_id = _components(junctions, triples, lambda e: ((e[0],), (e[1],)))
    tile_edges = defaultdict(list)
    for i, tile in enumerate(tiles):
        for e in combinations(tile, 2):
            tile_edges[e].append(i)
    dual_edges = tuple(pairs[g[0]] for g in surfaces)
    dual_faces = []
    for group in lines:
        touched = {surface_id[i] for j in group for i in tile_edges[junctions[j]]}
        expected = set(combinations(triples[group[0]], 2))
        if len(touched) != 3 or {dual_edges[e] for e in touched} != expected:
            raise ValueError('junction meets incompatible interfaces; prescription needs refinement')
        dual_faces.append(tuple(sorted(touched)))
    tetras = []
    for ti, tetra in quad:
        tetras.append(tuple(line_id[junction_lookup[(ti, f)]] for f in combinations(tetra, 3)))
    result = CellComplex3D(CellComplex2D(tuple(sorted(set(labels.values()))), dual_edges,
                                      tuple(dual_faces)), tuple(tetras))
    # Retain topology of what is being collapsed, so information loss is explicit.
    interface_betti = [SimplicialComplex([tiles[i] for i in g]).betti() for g in surfaces]
    line_betti = [SimplicialComplex([junctions[i] for i in g]).betti() for g in lines]
    provenance = {
        'method_status': 'EXPERIMENTAL_NOT_PHYSICS_VALIDATED',
        'interface_connectivity': 'shared_edge_with_same_color_pair',
        'junction_connectivity': 'shared_vertex_with_same_color_triple',
        'fine_simplex_by_barycenter_id': [list(s) for s in complex_.simplices],
        'interface_triangles': [list(t) for t in tiles],
        'interface_components': surfaces,
        'junction_edges': [list(e) for e in junctions],
        'junction_components': lines,
        'interface_betti_F2': [list(b) for b in interface_betti],
        'junction_betti_F2': [list(b) for b in line_betti],
        'fine_tetrahedron_by_dual_tetrahedron': [list(t) for _, t in quad],
        'collapse_warning': 'Noncontractible interfaces/junctions are NOT asserted to be topology-preserving.'}
    return result, provenance
