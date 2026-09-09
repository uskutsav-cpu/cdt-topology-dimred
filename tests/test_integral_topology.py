from itertools import combinations
import numpy as np
import pytest
from sympy import ImmutableSparseMatrix
from topology import SimplicialComplex
from topology.synthetic import sphere, ball, pinched_spheres, torus
from topology.integral import (AbelianGroup, ExactBudget, IntegralChainComplex, ChainMap,
                               IntegralLocalSystem, integral_homology, local_homology_via_link)
from topology.stratification import canonical_stratification


def projective_plane():
    return SimplicialComplex([(0,1,2),(0,1,3),(0,2,4),(0,3,5),(0,4,5),
                              (1,2,5),(1,3,4),(1,4,5),(2,3,4),(2,3,5)])


@pytest.mark.parametrize('k,free,torsion', [
    (sphere(1), (1,1), ((),())), (sphere(2), (1,0,1), ((),(),())),
    (sphere(3), (1,0,0,1), ((),(),(),())), (ball(3), (1,0,0,0), ((),(),(),())),
    (torus(2,3), (1,2,1), ((),(),())), (projective_plane(), (1,0,0), ((),(2,),())),
    (pinched_spheres(3), (1,0,0,2), ((),(),(),()))])
def test_integral_known_groups(k, free, torsion):
    groups = integral_homology(k)
    assert tuple(h.free_rank for h in groups) == free
    assert tuple(h.torsion for h in groups) == torsion
    assert sum((-1)**i*h.free_rank for i,h in enumerate(groups)) == k.euler


@pytest.mark.parametrize('k', [sphere(1), sphere(2), sphere(3), ball(3),
                              pinched_spheres(3), projective_plane()])
def test_integral_local_two_formulas(k):
    local = IntegralLocalSystem(k)
    for s in k.simplices:
        assert local.homology(s) == local_homology_via_link(k,s)


@pytest.mark.parametrize('factor', [0,1,-1,2,-3,12])
def test_equal_ranks_do_not_imply_map_isomorphism(factor):
    chain = IntegralChainComplex([1])
    f = ChainMap(chain,chain,{0:[[factor]]})
    assert f.source.homology == f.target.homology
    assert f.is_homology_isomorphism == (abs(factor) == 1)
    if abs(factor) > 1:
        assert f.cone.homology[0].torsion == (abs(factor),)
    if factor == 0:
        assert f.cone.homology == (AbelianGroup(1),AbelianGroup(1))


def test_chain_relation_and_map_relation_rejected():
    with pytest.raises(ValueError,match='boundary squared'):
        IntegralChainComplex([1,1,1],{1:[[2]],2:[[3]]})
    chain = IntegralChainComplex([1,1],{1:[[2]]})
    with pytest.raises(ValueError,match='not a chain map'):
        ChainMap(chain,chain,{0:[[1]],1:[[3]]})


def test_torsion_in_nonzero_degree_without_basis_transforms():
    c = IntegralChainComplex([1,3,2],{1:[[1,0,0]],2:[[0,0],[2,0],[0,6]]})
    assert c.homology == (AbelianGroup(),AbelianGroup(0,(2,6)),AbelianGroup())
    # A unimodular coordinate change mixes the kernel; torsion is unchanged.
    c2=IntegralChainComplex([1,3,2],{1:[[1,1,0]],2:[[-2,0],[2,0],[0,6]]})
    assert c2.homology == c.homology


@pytest.mark.parametrize('bad', [1.0, np.nan, 1.5])
def test_inexact_coefficients_rejected(bad):
    with pytest.raises(ValueError,match='exact integers'):
        IntegralChainComplex([1,1],{1:[[bad]]})


def test_empty_shapes_budgets_and_degree_validation():
    assert IntegralChainComplex([]).homology == ()
    assert integral_homology(SimplicialComplex()) == ()
    assert IntegralChainComplex([0,2]).homology == (AbelianGroup(),AbelianGroup(2))
    with pytest.raises(MemoryError):
        IntegralChainComplex([20,20],budget=ExactBudget(max_matrix_entries=10))
    with pytest.raises(MemoryError):
        IntegralChainComplex([5],budget=ExactBudget(max_generators=4))
    with pytest.raises(ValueError):
        IntegralChainComplex([1],{1:[[1]]})
    with pytest.raises(ValueError):
        IntegralChainComplex([True])
    with pytest.raises(ValueError):
        AbelianGroup(0,(4,6))


def test_local_chain_functor_composition_and_unknown_cells():
    local=IntegralLocalSystem(sphere(3))
    ab=local.incidence((0,),(0,1));bc=local.incidence((0,1),(0,1,2));ac=local.incidence((0,),(0,1,2))
    for k in range(4):
        assert bc.matrix(k)*ab.matrix(k)==ac.matrix(k)
    with pytest.raises(ValueError):
        local.incidence((0,1),(0,2))
    with pytest.raises(ValueError):
        local.homology((999,))


@pytest.mark.parametrize('k', [sphere(1),sphere(2),sphere(3),ball(1),ball(2),ball(3),
                              pinched_spheres(2),pinched_spheres(3),projective_plane(),
                              SimplicialComplex([(0,),(1,2)])])
def test_recursive_backends_and_incidence_certificates(k):
    ref=canonical_stratification(k,method='integral',audit_incidence=True)
    fast=canonical_stratification(k)
    assert ref.simplex_dimension==fast.simplex_dimension
    assert ref.simplex_component==fast.simplex_component
    assert set(ref.simplex_dimension)==set(k.simplices)
    assert all(c['is_integral_homology_isomorphism'] for c in ref.incidence_certificates)


@pytest.mark.parametrize('d',[1,2,3])
def test_ball_boundary_and_wedge(d):
    k=ball(d); r=canonical_stratification(k)
    assert r.simplex_dimension[k.facets[0]]==d
    assert all(r.simplex_dimension[s]==d-1 for s in k.simplices if s!=k.facets[0])
    w=pinched_spheres(d); r=canonical_stratification(w)
    assert r.simplex_dimension[(0,)]==0
    assert all(label==d for s,label in r.simplex_dimension.items() if s!=(0,))


def test_nonorientability_is_not_a_local_singularity():
    k=projective_plane()
    assert integral_homology(k)[1].torsion==(2,)
    assert set(canonical_stratification(k).simplex_dimension.values())=={2}


@pytest.mark.parametrize('seed',range(30))
def test_random_complex_fast_reference_agree(seed):
    rng=np.random.default_rng(seed)
    cells=[]
    for d in range(1,5):
        cells.extend(s for s in combinations(range(6),d) if rng.random()<0.16)
    k=SimplicialComplex(cells)
    a=canonical_stratification(k,method='integral')
    b=canonical_stratification(k)
    assert a.simplex_dimension==b.simplex_dimension
    # Universal coefficient theorem cross-check over two fields.
    h=integral_homology(k)
    for p in (2,11):
        expected=[]
        for i,g in enumerate(h):
            torsion_here=sum(t%p==0 for t in g.torsion)
            torsion_below=sum(t%p==0 for t in h[i-1].torsion) if i else 0
            expected.append(g.free_rank+torsion_here+torsion_below)
        assert tuple(expected)==k.betti(p)


@pytest.mark.parametrize('k',[ball(2),ball(3),pinched_spheres(2),pinched_spheres(3),projective_plane()])
def test_subdivision_labels_pull_back_from_maximal_carrier(k):
    sub=k.barycentric_subdivision()
    original=canonical_stratification(k)
    refined=canonical_stratification(sub)
    for flag,label in refined.simplex_dimension.items():
        carrier=max((k.simplices[i] for i in flag),key=len)
        assert label==original.simplex_dimension[carrier]


def test_no_partial_certificate_on_audit_budget_exhaustion():
    with pytest.raises(MemoryError,match='audit budget'):
        canonical_stratification(sphere(2),audit_incidence=True,max_audit_maps=1)
    assert canonical_stratification(SimplicialComplex()).stages==[]
    with pytest.raises(ValueError):
        canonical_stratification(sphere(1),method='ranks_only')
