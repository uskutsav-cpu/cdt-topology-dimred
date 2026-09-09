import pytest
from topology import SimplicialComplex, prime_field
from topology.synthetic import sphere, ball, torus, pinched_spheres


@pytest.mark.parametrize('p', [2, 11])
@pytest.mark.parametrize('factory,expected', [
    (lambda: sphere(1), (1, 1)), (lambda: sphere(2), (1, 0, 1)),
    (lambda: sphere(3), (1, 0, 0, 1)), (lambda: ball(), (1, 0, 0, 0)),
    (lambda: torus(2, 4), (1, 2, 1)), (lambda: torus(3, 3), (1, 3, 3, 1)),
    (lambda: pinched_spheres(3), (1, 0, 0, 2))])
def test_known_homology(factory, expected, p):
    k = factory()
    assert k.betti(p) == expected
    assert k.check_boundary_squared(p)
    assert k.euler == sum((-1) ** i * b for i, b in enumerate(expected))


@pytest.mark.parametrize('p', [2, 11])
@pytest.mark.parametrize('k', [sphere(3), ball(), pinched_spheres(3), torus(2, 4)])
def test_local_homology_two_independent_formulas(k, p):
    for s in k.simplices:
        assert k.local_betti(s, p) == k.local_betti_via_link(s, p)


def test_boundary_is_not_an_interior_homology_match():
    assert ball().local_betti((0,)) == (0, 0, 0, 0)
    assert sphere(3).local_betti((0,)) == (0, 0, 0, 1)
    assert pinched_spheres(3).local_betti((0,)) == (0, 1, 0, 2)


@pytest.mark.parametrize('k', [sphere(2), sphere(3), ball(), pinched_spheres(3)])
def test_barycentric_homology(k):
    sub = k.barycentric_subdivision()
    assert sub.betti(2) == k.betti(2)
    assert sub.betti(11) == k.betti(11)


def test_coefficients_matter_projective_plane():
    k = SimplicialComplex([(0,1,2),(0,1,3),(0,2,4),(0,3,5),(0,4,5),
                           (1,2,5),(1,3,4),(1,4,5),(2,3,4),(2,3,5)])
    assert k.betti(2) == (1, 1, 1)
    assert k.betti(11) == (1, 0, 0)


@pytest.mark.parametrize('p', [0, 1, 4, 9, 2.5, True])
def test_reject_nonfields(p):
    with pytest.raises(ValueError):
        prime_field(p)


@pytest.mark.parametrize('cells', [[(0,0,1)], [(0,1),(1,0)], [(0.5,1)], [()], [range(5)]])
def test_reject_ambiguous_cells(cells):
    with pytest.raises(ValueError):
        SimplicialComplex(cells)


def test_face_limit_and_unknown_local_cell():
    with pytest.raises(MemoryError):
        SimplicialComplex([(0,1,2,3)], max_faces=10)
    with pytest.raises(ValueError):
        sphere(2).local_betti((999,))


def test_link_accepts_single_use_iterator():
    k = sphere(3)
    assert k.link(iter([0])).betti() == (1,0,1)


def test_void_link_still_checks_coefficient_field():
    k = ball()
    with pytest.raises(ValueError):
        k.local_betti_via_link((0,1,2,3),p=4)
