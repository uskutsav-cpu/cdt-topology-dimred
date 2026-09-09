import pytest
from topology.synthetic import sphere, torus, pinched_spheres
from coarsegrain.voronoi import poisson_seeds, voronoi, validate_partition, checked_graph
from coarsegrain.dual2d import CellComplex2D, coarsegrain_surface
from coarsegrain.dual3d import CellComplex3D, coarsegrain_manifold3d


def pad(values, n):
    return tuple(values) + (0,) * (n - len(values))


@pytest.mark.parametrize('dimension,side', [(2,5),(3,3)])
@pytest.mark.parametrize('delta', [1,2,3,10])
def test_sampler_voronoi_contract(dimension, side, delta):
    g = torus(dimension, side).adjacency()
    s = poisson_seeds(g, delta, 91)
    assert s == poisson_seeds(g, delta, 91)
    p = voronoi(g, s, 12)
    assert p == voronoi(g, s, 12)
    report = validate_partition(g, p, delta)
    assert report['connected_cells']
    assert report['coverage_radius'] < delta
    if delta == 1:
        assert len(s) == len(g)


@pytest.mark.parametrize('k', [sphere(2), torus(2,5)])
@pytest.mark.parametrize('p', [2,11])
def test_2d_identity_and_independent_boundaries(k, p):
    d, meta = coarsegrain_surface(k, {v:v for v in k.vertices})
    assert d.betti(p) == k.betti(p)
    assert pad(d.subdivision().betti(p), 3) == d.betti(p)
    assert meta['parallel_edge_excess'] == 0


def test_parallel_edges_are_not_merged():
    k = torus(2,4)
    d, meta = coarsegrain_surface(k, {v:int(v % 4 >= 2) for v in k.vertices})
    assert len(d.edges) == 2 and len(set(d.edges)) == 1
    assert d.betti() == (1, 1, 0)
    assert pad(d.subdivision().betti(), 3) == d.betti()
    assert meta['parallel_edge_excess'] == 1
    # Collapsing the two edges to a single graph edge would erase H_1.
    assert CellComplex2D(d.vertices, tuple(set(d.edges)), ()).betti() == (1, 0, 0)


def test_pillow_preserves_second_homology():
    d, meta = coarsegrain_surface(sphere(2), {0:0,1:1,2:2,3:0})
    assert len(d.vertices) == 3 and len(d.faces) == 2
    assert d.betti(2) == (1, 0, 1)
    assert d.betti(11) == (1, 0, 1)
    assert d.subdivision().betti() == (1, 0, 1)
    assert meta['repeated_face_vertex_sets'] == 1


@pytest.mark.parametrize('seed', list(range(6)))
def test_2d_coarse_dual_direct_vs_subdivision(seed):
    k = torus(2,5)
    s = poisson_seeds(k.adjacency(), 2, seed)
    p = voronoi(k.adjacency(), s, seed + 10)
    d, _ = coarsegrain_surface(k, p.labels)
    for field in (2, 11):
        assert d.betti(field) == pad(d.subdivision().betti(field), 3)


@pytest.mark.parametrize('k', [sphere(3), torus(3,3)])
def test_3d_identity(k):
    d, provenance = coarsegrain_manifold3d(k, {v:v for v in k.vertices})
    assert d.betti(2) == k.betti(2)
    assert d.subdivision().betti(2) == k.betti(2)
    assert d.betti(11) == k.betti(11)
    assert len(d.tetrahedra) == len(k.facets)
    assert provenance['method_status'] == 'EXPERIMENTAL_NOT_PHYSICS_VALIDATED'


@pytest.mark.parametrize('seed', [1,2,3])
def test_3d_candidate_chain_algebra(seed):
    k = torus(3,3)
    p = voronoi(k.adjacency(), poisson_seeds(k.adjacency(), 2, seed), seed + 10)
    d, meta = coarsegrain_manifold3d(k, p.labels)
    sub = d.subdivision()
    for field in (2,11):
        assert d.betti(field) == pad(sub.betti(field), 4)
        assert sub.check_boundary_squared(field)
    assert 'NOT asserted' in meta['collapse_warning']


def test_3d_pillow_preserves_cell_multiplicity():
    sk = CellComplex2D((0,1,2,3), ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)),
                      ((0,1,3),(0,2,4),(1,2,5),(3,4,5)))
    d = CellComplex3D(sk, ((0,1,2,3),(0,1,2,3)))
    for field in (2,11):
        assert d.betti(field) == (1,0,0,1)
        assert d.subdivision().betti(field) == (1,0,0,1)


def test_invalid_loop_and_nonmanifold_rejected():
    with pytest.raises(ValueError):
        CellComplex2D((0,), ((0,0),), ())
    with pytest.raises(ValueError):
        coarsegrain_manifold3d(pinched_spheres(3), {v:v for v in pinched_spheres(3).vertices})
    with pytest.raises(ValueError):
        CellComplex3D(CellComplex2D((0,), (), ()), ((0,0,0,0),))


@pytest.mark.parametrize('graph', [{}, {0:(1,),1:()}, {0:(0,)}, {0:(1,1),1:(0,)}])
def test_invalid_graph(graph):
    with pytest.raises(ValueError):
        checked_graph(graph)


def test_disconnected_seed_sampling_rejected():
    with pytest.raises(ValueError):
        poisson_seeds({0:(),1:()}, 2, 1)
