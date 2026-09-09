from itertools import combinations
import numpy as np
import pytest
from cdt_mechanisms.triangulations import *
from cdt_mechanisms.persistence import independent_betti
from cdt_mechanisms.fem import *

@pytest.mark.parametrize('n',[5,6,9,14])
@pytest.mark.parametrize('T',[3,4,5])
def test_valid_cdt_product(n,T):
    g=product_cdt(bipyramid(n),T); a=audit_cdt(g)
    assert a['N0']==n*T and a['N3']==3*(2*n-4)*T
    assert a['all_vertex_links_S2'] and a['dual_regular_degree']==4
    assert independent_betti(g.tetra)==[1,1,1,1]

@pytest.mark.parametrize('mode',['random','chain','balanced'])
@pytest.mark.parametrize('n',[5,8,13])
def test_stacked_sphere_necks(mode,n):
    f=stacked_sphere(n,mode=mode,seed=2)
    assert sphere_audit(f)['chi']==2
    assert necks(f)['separating_triangle_count']==n-4
    assert necks(bipyramid(max(n,6)))['separating_triangle_count']==0

@pytest.mark.parametrize('seed',range(8))
def test_reversible_surgery(seed):
    before=stacked_sphere(14,seed=seed)
    after,ledger=random_flips(before,30,seed=seed+91)
    assert undo_flips(after,ledger)==before
    ga=product_cdt(before,3); gb=product_cdt(after,3)
    aa=audit_cdt(ga); ab=audit_cdt(gb)
    assert [aa[k] for k in ('N0','N1','N2','N3')]==[ab[k] for k in ('N0','N1','N2','N3')]
    assert np.array_equal(aa['spatial_volume'],ab['spatial_volume'])

def test_invalid_flip_refused():
    f=tuple(combinations(range(4),3))
    with pytest.raises(ValueError): edge_flip(f,(0,1))

def test_io_roundtrip_and_no_overwrite(tmp_path):
    g=product_cdt(bipyramid(7),3); p=tmp_path/'geometry.dat'
    write_geometry(g,p); restored=read_geometry(p)
    assert geometry_digest(g)==geometry_digest(restored)
    audit_cdt(restored)
    with pytest.raises(FileExistsError): write_geometry(g,p)

@pytest.mark.parametrize('kind',['truncated','float','wrong_sentinel','bad_neighbor','bad_time'])
def test_corrupt_geometry_rejected(kind,tmp_path):
    g=product_cdt(bipyramid(6),3); p=tmp_path/'g.dat'; write_geometry(g,p)
    if kind=='bad_neighbor':
        g.neighbors[0,0]=g.neighbors[0,1]
        with pytest.raises(ValueError): audit_cdt(g)
    elif kind=='bad_time':
        g.time[0]=10
        with pytest.raises(ValueError): audit_cdt(g)
    else:
        tokens=p.read_text().split()
        if kind=='truncated': tokens=tokens[:-5]
        elif kind=='float': tokens[4]='1.1'
        else: tokens[-1]='99999'
        p.write_text(' '.join(tokens))
        with pytest.raises(ValueError): read_geometry(p)

def test_regular_tetra_element():
    lengths=np.ones((4,4))-np.eye(4); k,m,v,coords=local_element(lengths)
    assert np.isclose(v,np.sqrt(2)/12)
    np.testing.assert_allclose(k.sum(axis=1),0,atol=1e-14)
    np.testing.assert_allclose(np.sum(m),v)
    assert np.linalg.eigvalsh(m).min()>0
    assert np.linalg.matrix_rank(k)==3
    np.testing.assert_allclose(np.linalg.norm(coords[:,None]-coords[None,:],axis=2),lengths,atol=1e-14)

@pytest.mark.parametrize('seed',range(8))
def test_affine_fem_patch(seed):
    rng=np.random.default_rng(seed); xyz=rng.normal(size=(4,3))
    lengths=np.linalg.norm(xyz[:,None]-xyz[None,:],axis=2)
    k,m,v,_=local_element(lengths)
    grad=rng.normal(size=3); values=xyz@grad+1.3
    assert np.isclose(values@k@values,v*(grad@grad),rtol=1e-8,atol=1e-9)
    assert np.isclose(np.ones(4)@m@np.ones(4),v)

def test_invalid_intrinsic_metric():
    length=np.ones((4,4))-np.eye(4); length[0,1]=length[1,0]=5
    with pytest.raises(ValueError): local_element(length)
    with pytest.raises(ValueError): metric_mesh([[0,1,2,3]],{(0,1):1})

def test_fem_refinement_patch_and_ritz():
    g=product_cdt(bipyramid(6),3); mesh=metric_mesh(g.tetra); coarse=assemble(mesh)
    fine,pro=midpoint_refinement(mesh); f=assemble(fine); audit=refinement_audit(coarse,f,pro)
    assert audit['stiffness_galerkin_error']<1e-10
    a=full_spectrum(coarse); b=full_spectrum(f)
    assert a['zero_modes']==b['zero_modes']==1
    assert np.max(b['eigenvalues'][:len(a['eigenvalues'])]-a['eigenvalues'])<1e-8
    assert len(fine.tetra)==8*len(mesh.tetra)

def test_fem_scale_covariance():
    g=product_cdt(bipyramid(5),3); mesh=metric_mesh(g.tetra); base=full_spectrum(assemble(mesh))
    scaled=metric_mesh(mesh.tetra,{e:2*l for e,l in mesh.edge_lengths.items()})
    b=full_spectrum(assemble(scaled))
    np.testing.assert_allclose(b['eigenvalues'],base['eigenvalues']/4,atol=1e-10)
    assert np.isclose(b['volume'],base['volume']*8)

def test_fem_permutation_invariance():
    g=product_cdt(bipyramid(6),3); a=full_spectrum(assemble(metric_mesh(g.tetra)))
    b=full_spectrum(assemble(metric_mesh(g.tetra[:,[2,0,3,1]])))
    np.testing.assert_allclose(a['eigenvalues'],b['eigenvalues'],atol=1e-10)

def test_short_time_low_mode_guard():
    mesh=metric_mesh(product_cdt(bipyramid(6),3).tetra)
    with pytest.raises(ValueError,match='short-time'): full_spectrum(assemble(mesh),dense_limit=2)

def test_lumped_mass_not_silently_same():
    mesh=metric_mesh(product_cdt(bipyramid(6),3).tetra)
    a=full_spectrum(assemble(mesh)); b=full_spectrum(assemble(mesh,lumped=True))
    assert np.isclose(a['volume'],b['volume']) and not np.allclose(a['eigenvalues'],b['eigenvalues'])
