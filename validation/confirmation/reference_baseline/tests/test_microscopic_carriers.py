from copy import deepcopy
import numpy as np
import pytest
from topology.synthetic import sphere,torus,ball
from coarsegrain.dual3d import coarsegrain_manifold3d
from coarsegrain.microscopic import dual_neighbors,singular_distances,map_incidence_carriers


@pytest.mark.parametrize('fine',[sphere(3),torus(3,3)])
def test_identity_relation_everywhere_regular(fine):
    labels={v:v for v in fine.vertices}
    coarse,provenance=coarsegrain_manifold3d(fine,labels)
    result=map_incidence_carriers(fine,labels,coarse,provenance)
    assert result['regular'].all()
    assert not result['singular'].any()
    assert not result['ambiguous'].any()
    assert (result['distance_to_singular']==-1).all()
    assert not result['production_eligible']
    assert not result['measurement_eligible_synthetically']
    assert all(len(c)==15 for c in result['carriers'])


def test_provenance_tampering_rejected():
    fine=sphere(3);labels={v:v for v in fine.vertices}
    coarse,p=coarsegrain_manifold3d(fine,labels)
    q=deepcopy(p);q['interface_components'][0].append(q['interface_components'][0][0])
    with pytest.raises(ValueError,match='partition'):
        map_incidence_carriers(fine,labels,coarse,q)
    q=deepcopy(p);q['fine_simplex_by_barycenter_id'][0]=[999]
    with pytest.raises(ValueError,match='does not match'):
        map_incidence_carriers(fine,labels,coarse,q)
    q=deepcopy(p);q['junction_edges']=q['junction_edges'][:-1]
    with pytest.raises(ValueError,match='piece audit'):
        map_incidence_carriers(fine,labels,coarse,q)


def test_collapsed_dimension_is_all_singular_not_mislabeled_regular():
    fine=sphere(3);labels={v:0 for v in fine.vertices}
    coarse,p=coarsegrain_manifold3d(fine,labels)
    r=map_incidence_carriers(fine,labels,coarse,p)
    assert r['singular'].all() and not r['regular'].any()
    assert (r['distance_to_singular']==0).all()
    assert not r['measurement_eligible_synthetically']


def test_microscopic_distances():
    n=7;a=np.array([[(i-1)%n,(i+1)%n] for i in range(n)])
    s=np.zeros(n,bool);s[0]=True
    np.testing.assert_array_equal(singular_distances(a,s),[0,1,2,3,3,2,1])
    assert (singular_distances(a,np.zeros(n,bool))==-1).all()
    with pytest.raises(ValueError):singular_distances(a,s.astype(int))
    with pytest.raises(ValueError):singular_distances(a.astype(float),s)
    a[1,0]=3
    with pytest.raises(ValueError):singular_distances(a,s)


def test_geometry_and_label_validation():
    with pytest.raises(ValueError):dual_neighbors(ball(3))
    f=sphere(3);labels={v:v for v in f.vertices};coarse,p=coarsegrain_manifold3d(f,labels)
    bad=dict(labels);bad.pop(0)
    with pytest.raises(ValueError):map_incidence_carriers(f,bad,coarse,p)
    bad=dict(labels);bad[0]=True
    with pytest.raises(ValueError):map_incidence_carriers(f,bad,coarse,p)
