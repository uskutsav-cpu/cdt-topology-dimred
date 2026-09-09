from itertools import combinations
import numpy as np
import pytest
from cdt_mechanisms.persistence import *

@pytest.mark.parametrize('facets,expected',[
 ([(0,1),(1,2),(2,0)],[1,1]),
 ([(0,1,2)],[1,0,0]),
 (list(combinations(range(4),3)),[1,0,1]),
 ([(0,1,2,3)],[1,0,0,0]),
 ([(0,),(1,)],[2]),
 ([(0,1),(2,3)],[2,0])])
def test_known_betti(facets,expected):
    assert independent_betti(facets)==expected
    bars=persistent_homology(filtration_from_facets(facets))
    got=betti_curve(bars,[0],max_dimension=len(expected)-1)[0].tolist()
    assert got==expected

def test_triangle_born_then_filled():
    f=filtration_from_facets([(0,1),(1,2),(0,2),(0,1,2)],[0,0,1,4])
    bars=persistent_homology(f)
    h1=[b for b in bars if b.dimension==1 and b.death>b.birth]
    assert len(h1)==1 and h1[0].birth==1 and h1[0].death==4
    assert betti_curve(bars,[0,1,3,4])[:,1].tolist()==[0,1,1,0]

@pytest.mark.parametrize('bad',[
 {(0,1):0}, {(0,):1,(1,):0,(0,1):0}, {(0,):float('nan')},
 {(0,0):0}, {(-1,):0}, {(0.5,):0}, {}])
def test_bad_filtrations(bad):
    with pytest.raises(ValueError): persistent_homology(bad)

@pytest.mark.parametrize('seed',range(20))
def test_random_boundary_ranks_vs_barcode(seed):
    rng=np.random.default_rng(seed); cells=[c for c in combinations(range(7),4) if rng.random()<.2]
    if not cells: cells=[(0,1,2,3)]
    values=rng.integers(0,5,len(cells)); f=filtration_from_facets(cells,values)
    bars=persistent_homology(f)
    for threshold in range(5):
        facets=[s for s,v in f.items() if v<=threshold]
        if not facets:
            assert not betti_curve(bars,[threshold]).any(); continue
        expected=independent_betti(facets)
        got=betti_curve(bars,[threshold])[0,:len(expected)].tolist()
        assert got==expected

def test_horizon_censoring():
    cells=np.array([[0,1,2,3],[0,1,2,4]])
    result=geodesic_ball_persistence(cells,np.array([0,1]),0)
    assert not result['whole_geometry']
    assert result['betti'][0].tolist()==[1,0,0,0]
    assert any(not np.isfinite(b.death) for b in result['intervals'])

def test_budget_guard():
    with pytest.raises(ValueError,match='budget'):
        filtration_from_facets([(0,1,2,3)],budget=3)

def test_non_nested_betti_samples_not_accepted_as_persistence():
    # An invalid face order cannot be mistaken for a persistent filtration.
    f=filtration_from_facets([(0,1,2)])
    f[(0,1)]=5
    with pytest.raises(ValueError,match='monotone'): persistent_homology(f)
