"""Experimental incidence-carrier labels and microscopic dual distances.

This audits the existing 3D construction's fine-piece provenance. It defines a
RELATION from fine tetrahedra to touched coarse open cells, not a certified
continuous map or a validated quantum-gravity observable. Production gates must
remain closed until the mapping prescription is independently approved.
"""
from __future__ import annotations

from collections import defaultdict, deque
from itertools import combinations
from numbers import Integral

import numpy as np

from topology.stratification import canonical_stratification


MAPPING_DEFINITION = (
    'EXPERIMENTAL incidence-carrier relation v1: a fine tetrahedron touches each '
    'coarse region-vertex represented by its vertex labels, each interface-edge '
    'whose barycentric fine triangle lies in it, each junction-face whose fine '
    'segment lies in it, and its four-colour coarse tetrahedron if present. '
    'Singular means any touched open coarse cell has canonical dimension < 3. '
    'This is not a certified continuous preimage or physics-validated mapping.'
)


def dual_neighbors(complex_):
    tets=complex_.groups.get(3,())
    if not tets or any(len(s)!=4 for s in complex_.facets):
        raise ValueError('pure nonempty tetrahedral complex required')
    incidence=defaultdict(list)
    for i,t in enumerate(tets):
        for j in range(4):
            incidence[t[:j]+t[j+1:]].append((i,j))
    neighbors=np.full((len(tets),4),-1,dtype=np.int64)
    for entries in incidence.values():
        if len(entries)!=2:
            raise ValueError('every fine face must have exactly two incident tetrahedra')
        (a,i),(b,j)=entries
        neighbors[a,i]=b;neighbors[b,j]=a
    return neighbors


def singular_distances(neighbors,singular):
    """Shortest unweighted microscopic dual distance; -1 means unreachable.

    An empty source set is allowed and returns -1 everywhere, not fake zeros.
    """
    a=np.asarray(neighbors);sources=np.asarray(singular)
    if (a.ndim!=2 or not len(a) or a.dtype.kind not in 'iu' or a.min()<0 or a.max()>=len(a)
            or sources.dtype!=np.bool_ or sources.shape!=(len(a),)):
        raise ValueError('integer adjacency and boolean source array required')
    # Require reciprocal adjacency, not necessarily a simple graph.
    edges={(i,int(j)) for i,row in enumerate(a) for j in row}
    if any((j,i) not in edges for i,j in edges):
        raise ValueError('microscopic adjacency must be undirected')
    distance=np.full(len(a),-1,dtype=np.int64)
    queue=deque(map(int,np.flatnonzero(sources)))
    distance[sources]=0
    while queue:
        i=queue.popleft()
        for j in a[i]:
            if distance[j]<0:
                distance[j]=distance[i]+1
                queue.append(int(j))
    return distance


def _cell_dimensions(coarse,stratification):
    skeleton=coarse.skeleton
    n0,n1,n2=len(skeleton.vertices),len(skeleton.edges),len(skeleton.faces)
    cells=([(0,v) for v in skeleton.vertices]+[(1,i) for i in range(n1)]
           +[(2,i) for i in range(n2)]+[(3,i) for i in range(len(coarse.tetrahedra))])
    dimensions={c:set() for c in cells}
    for flag,label in stratification.simplex_dimension.items():
        # IDs are ordered by coarse cell dimension. Every flag's largest ID is
        # its unique maximal cell; its open simplex lies in that cell's interior.
        carrier=max(flag)
        if carrier>=len(cells):
            raise ValueError('subdivision cell IDs do not match coarse complex')
        dimensions[cells[carrier]].add(label)
    if any(not values for values in dimensions.values()):
        raise ValueError('missing coarse cell interior in stratification')
    return dimensions


def _components(components,pieces,expected_count):
    if len(components)!=expected_count:
        raise ValueError('component count does not match coarse cell count')
    flattened=[]
    for component in components:
        if not component:
            raise ValueError('empty provenance component')
        for i in component:
            if isinstance(i,bool) or not isinstance(i,Integral) or not 0<=i<len(pieces):
                raise ValueError('invalid piece ID')
            flattened.append(int(i))
    if sorted(flattened)!=list(range(len(pieces))):
        raise ValueError('provenance components must partition all pieces exactly once')


def map_incidence_carriers(fine,vertex_labels,coarse,provenance,*,max_faces=500000):
    """Build candidate masks with an independently reconstructed flag audit.

    No returns, diffusion times, or outcomes are accepted as inputs. All cells
    touched by a fine tetrahedron are retained, not only a nearest coarse cell.
    Mixed interior strata are marked ambiguous rather than silently resolved.
    """
    if set(vertex_labels)!=set(fine.vertices):
        raise ValueError('labels must cover exactly the fine vertices')
    if any(isinstance(v,bool) or not isinstance(v,Integral) for v in vertex_labels.values()):
        raise ValueError('region labels must be integers')
    labels={v:int(c) for v,c in vertex_labels.items()}
    tets=fine.groups.get(3,())
    neighbors=dual_neighbors(fine)
    fine_by_id=tuple(tuple(s) for s in provenance['fine_simplex_by_barycenter_id'])
    if fine_by_id!=fine.simplices:
        raise ValueError('fine-simplex provenance does not match the geometry')
    ids={s:i for i,s in enumerate(fine.simplices)}
    tet_index={s:i for i,s in enumerate(tets)}
    expected_interfaces=set();expected_junctions=set()
    for t in tets:
        for f in combinations(t,3):
            if len({labels[v] for v in f})==3:
                expected_junctions.add(tuple(sorted((ids[f],ids[t]))))
            for e in combinations(f,2):
                if labels[e[0]]!=labels[e[1]]:
                    expected_interfaces.add(tuple(sorted((ids[e],ids[f],ids[t]))))
    interfaces=[tuple(p) for p in provenance['interface_triangles']]
    junctions=[tuple(p) for p in provenance['junction_edges']]
    if len(set(interfaces))!=len(interfaces) or set(interfaces)!=expected_interfaces:
        raise ValueError('interface fine-piece audit failed')
    if len(set(junctions))!=len(junctions) or set(junctions)!=expected_junctions:
        raise ValueError('junction fine-piece audit failed')
    ic=provenance['interface_components'];jc=provenance['junction_components']
    _components(ic,interfaces,len(coarse.skeleton.edges))
    _components(jc,junctions,len(coarse.skeleton.faces))
    carriers=[{(0,labels[v]) for v in t} for t in tets]
    for edge,component in enumerate(ic):
        color_pair=tuple(sorted(coarse.skeleton.edges[edge]))
        for i in component:
            edge_id,_,tet_id=interfaces[i]
            if tuple(sorted(labels[v] for v in fine_by_id[edge_id]))!=color_pair:
                raise ValueError('interface colors do not match coarse edge')
            carriers[tet_index[fine_by_id[tet_id]]].add((1,edge))
    for face,component in enumerate(jc):
        color_triple=tuple(sorted(coarse.face_vertices(face)))
        for i in component:
            face_id,tet_id=junctions[i]
            if tuple(sorted(labels[v] for v in fine_by_id[face_id]))!=color_triple:
                raise ValueError('junction colors do not match coarse face')
            carriers[tet_index[fine_by_id[tet_id]]].add((2,face))
    tet_origins=[tuple(t) for t in provenance['fine_tetrahedron_by_dual_tetrahedron']]
    if (len(tet_origins)!=len(coarse.tetrahedra) or len(set(tet_origins))!=len(tet_origins)
            or set(tet_origins)!={t for t in tets if len({labels[v] for v in t})==4}):
        raise ValueError('four-colour tetrahedron provenance audit failed')
    for index,t in enumerate(tet_origins):
        coarse_vertices=set().union(*(set(coarse.face_vertices(f)) for f in coarse.tetrahedra[index]))
        if {labels[v] for v in t}!=coarse_vertices:
            raise ValueError('coarse tetrahedron colors mismatch')
        carriers[tet_index[t]].add((3,index))
    sub=coarse.subdivision(max_faces=max_faces)
    stratification=canonical_stratification(sub)
    cell_dimensions=_cell_dimensions(coarse,stratification)
    singular=np.zeros(len(tets),bool);ambiguous=singular.copy()
    for i,cells in enumerate(carriers):
        if not cells or any(cell not in cell_dimensions for cell in cells):
            raise ValueError('missing or unknown coarse carrier')
        ambiguous[i]=any(len(cell_dimensions[c])!=1 for c in cells)
        singular[i]=any(any(d<3 for d in cell_dimensions[c]) for c in cells)
    # Ambiguous carriers are excluded from BOTH scientific classes.
    singular &= ~ambiguous
    regular=~(singular|ambiguous)
    return {'method_status':'EXPERIMENTAL_NOT_PHYSICS_VALIDATED',
            'mapping_definition':MAPPING_DEFINITION,'continuous_map_certified':False,
            'fine_tetrahedra':np.asarray(tets,dtype=np.int64),'neighbors':neighbors,
            'regular':regular,'singular':singular,'ambiguous':ambiguous,
            'start_mask':~ambiguous,'distance_to_singular':singular_distances(neighbors,singular),
            'carriers':[[list(c) for c in sorted(cells)] for cells in carriers],
            'coarse_cell_stratum_dimensions':[
                {'cell':list(cell),'dimensions':sorted(dims)} for cell,dims in sorted(cell_dimensions.items())],
            'stratification':stratification.as_dict(),
            'class_counts':{'regular':int(regular.sum()),'singular':int(singular.sum()),
                            'ambiguous':int(ambiguous.sum())},
            'measurement_eligible_synthetically':bool(regular.any() and singular.any()),
            'production_eligible':False}
