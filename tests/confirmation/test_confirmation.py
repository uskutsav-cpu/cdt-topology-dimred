from itertools import combinations
from pathlib import Path
import json
import numpy as np
import pytest
from scipy import sparse
from cdt_mechanisms.persistence import filtration_from_facets,persistent_homology,betti_curve,Interval
from cdt_mechanisms.graph import from_neighbors,distances
from cdt_mechanisms.diffusion import transition,exact_diffusion
from cdt_mechanisms.triangulations import bipyramid,product_cdt,Triangulation,random_flips,undo_flips
from cdt_mechanisms.inference import matched_pairs
from cdt_confirmation.fields import prime,persistence_prime,signature,independent_betti,features,rooted,rank_prime
from cdt_confirmation.walks import propagate
from cdt_confirmation.provenance import stage,verify,identity,write_json
from cdt_confirmation.statistics import correlation_test,holm,within_with_null,paired_effect
from cdt_confirmation.measurement import legacy_validate,neck_features
from cdt_confirmation.analysis import _matching

@pytest.mark.parametrize('p',[2,3,5,11,65521])
def test_delayed_disk(p):
    f=filtration_from_facets([(0,1),(1,2),(0,2),(0,1,2)],[0,0,0,2])
    bars=persistence_prime(f,p)
    assert (1,0.,2.) in signature(bars)
    for t,expected in [(0,[1,1,0,0]),(1,[1,1,0,0]),(2,[1,0,0,0])]:
        assert independent_betti(f,t,p)==expected
        assert betti_curve(bars,[t])[0].tolist()==expected

@pytest.mark.parametrize('p',[2,3,5,11])
def test_projective_plane_torsion(p):
    # Six-vertex closed triangulation with Euler characteristic 1.
    facets=[(1,2,3),(1,2,4),(1,3,5),(1,4,6),(1,5,6),
            (2,3,6),(2,4,5),(2,5,6),(3,4,5),(3,4,6)]
    f=filtration_from_facets(facets)
    expected=[1,1,1,0] if p==2 else [1,0,0,0]
    assert independent_betti(f,0,p)==expected
    assert betti_curve(persistence_prime(f,p),[0])[0].tolist()==expected

@pytest.mark.parametrize('seed',range(24))
def test_random_boundary_rank_and_bit_backend(seed):
    rng=np.random.default_rng(seed);facets=[s for s in combinations(range(6),3) if rng.random()<.3]+[(0,)]
    f=filtration_from_facets(facets,rng.integers(0,4,size=len(facets)))
    assert signature(persistence_prime(f,2))==signature(persistent_homology(f))
    for p in [2,3,5]:
        bars=persistence_prime(f,p)
        for t in [0,1,2,3]:assert independent_betti(f,t,p)==betti_curve(bars,[t])[0].tolist()

@pytest.mark.parametrize('bad',[True,False,0,1,4,9,15,-3,2.0,65522,'3'])
def test_bad_field(bad):
    with pytest.raises(ValueError):prime(bad)

@pytest.mark.parametrize('p',[2,3,5,11])
def test_boundary_orientation_and_relabeling(p):
    facets=list(combinations(range(4),3));f=filtration_from_facets(facets)
    assert independent_betti(f,0,p)==[1,0,1,0]
    relabel={0:5,1:2,2:9,3:0};ff={tuple(sorted(relabel[v] for v in s)):t for s,t in f.items()}
    assert signature(persistence_prime(f,p))==signature(persistence_prime(ff,p))
    assert rank_prime(np.array([[1,2],[2,4]]),p)==1

def cycle(n):
    a=np.zeros((n,n))
    for i in range(n):a[i,(i+1)%n]=a[(i+1)%n,i]=1
    return sparse.csr_matrix(a)

@pytest.mark.parametrize('n',[5,8,15])
@pytest.mark.parametrize('rho',[.3,.5,.8])
def test_exact_walk_against_matrix_powers(n,rho):
    a=cycle(n);roots=np.arange(n);result=propagate(a,roots,12,moving_probability=rho,batch_size=3)
    p=transition(a,rho).toarray();m=np.eye(n);d=distances(a,roots)
    for t in range(13):
        np.testing.assert_allclose(result['returns'][:,t],m.diagonal(),atol=1e-13)
        np.testing.assert_allclose(result['msd'][:,t],np.sum(m*d*d,axis=1),atol=1e-13)
        assert np.isclose(result['distance_distribution'][t].sum(),1)
        m=m@p
    old=exact_diffusion(a,roots,12,moving_probability=rho)
    np.testing.assert_allclose(result['returns'],old.returns,atol=1e-13)
    assert result['full_root_census'] and result['mass_error']<1e-12

def test_lifetime_censoring_no_padding():
    bars=[Interval(1,2,5,(0,1),None),Interval(1,4,np.inf,(1,2),None),Interval(1,3,3,(1,3),None)]
    f=features(bars,8,20)
    assert f['H1_finite_count']==1 and f['H1_censored_count']==1
    assert f['H1_finite_total_persistence']==3 and f['H1_observed_persistence']==7
    assert features([],8,10)['H1_finite_mean_lifetime'] is None

@pytest.mark.parametrize('seed',range(4))
def test_legacy_validity_reversal_and_root_relabeling(seed):
    initial=bipyramid(8);faces,ledger=random_flips(initial,12,seed=seed)
    assert undo_flips(faces,ledger)==initial
    g=product_cdt(faces,3);assert legacy_validate(g)['report']['all_vertex_links_S2']
    a=from_neighbors(g.neighbors);d=distances(a,[0])[0]
    original=rooted(g.tetra,d,4,fields=[2,3,5])
    p=np.random.default_rng(seed).permutation(len(g.tetra));inverse=np.argsort(p)
    gg=Triangulation(g.time,g.tetra[p],inverse[g.neighbors[p]],True)
    legacy_validate(gg);dd=distances(from_neighbors(gg.neighbors),[int(inverse[0])])[0]
    permuted=rooted(gg.tetra,dd,4,fields=[2,3,5])
    for field in [2,3,5]:assert signature(original['fields'][field]['bars'])==signature(permuted['fields'][field]['bars'])

@pytest.mark.parametrize('fault',['bytes','extra','missing','nested_manifest','symlink'])
def test_corruption_rejected(tmp_path,fault):
    ident=identity({'seed':1},sources={})
    out,reused=stage(tmp_path,ident,lambda p:write_json(p/'a.json',{'hello':1}))
    assert not reused;assert verify(out)['complete']
    if fault=='bytes':(out/'a.json').write_text('broken')
    elif fault=='extra':(out/'b').write_text('extra')
    elif fault=='missing':(out/'a.json').unlink()
    elif fault=='nested_manifest':(out/'nested').mkdir();(out/'nested/manifest.json').write_text('{}')
    else:(out/'link').symlink_to(out/'a.json')
    with pytest.raises(ValueError):verify(out)

def test_atomic_failure_resume_identity(tmp_path):
    ident=identity({'seed':1},sources={});count=[]
    def fail(p):write_json(p/'a.json',{});raise RuntimeError('interrupted')
    with pytest.raises(RuntimeError):stage(tmp_path,ident,fail)
    assert not list(tmp_path.glob('*/manifest.json'))
    def good(p):count.append(1);write_json(p/'a.json',{})
    p,reused=stage(tmp_path,ident,good);q,reused2=stage(tmp_path,ident,good)
    assert p==q and not reused and reused2 and len(count)==1
    with pytest.raises(ValueError):verify(p,identity({'seed':2},sources={}))

@pytest.mark.parametrize('direction',['negative','positive','two-sided'])
def test_known_correlation_reproducible(direction):
    x=np.arange(32,dtype=float);y=-x+np.random.default_rng(4).normal(size=32)
    a=correlation_test(x,y,direction=direction,permutations=199,bootstraps=299,seed=1)
    b=correlation_test(x,y,direction=direction,permutations=199,bootstraps=299,seed=1)
    assert a['pearson_r']<-.98;np.testing.assert_array_equal(a['null_distribution'],b['null_distribution'])
    assert a['permutation_p']>.9 if direction=='positive' else a['permutation_p']<=.01
    assert a['slope_ci95'][1]<0

@pytest.mark.parametrize('seed',range(6))
def test_cluster_known_effect_and_destroyed_null(seed):
    rng=np.random.default_rng(seed);cfg=np.repeat(np.arange(16),24);c=rng.normal(size=(len(cfg),2))
    x=.5*c[:,0]+rng.normal(size=len(cfg));y=-.8*x+.6*c[:,0]+rng.normal(size=16)[cfg]+rng.normal(scale=.1,size=len(cfg))
    result=within_with_null(x,y,c,cfg,cfg,seed=seed,permutations=199)
    assert abs(result['estimate']['coefficient']+.8)<.03
    assert result['estimate']['ci95'][1]<0 and result['wild_cluster_score_p']<=.02
    assert abs(result['label_destroyed_estimate']['coefficient'])<.2

def test_matching_orientation_and_effect():
    items=[]
    for seed in range(4):
        rows=[]
        for j in range(8):
            z=j//4
            rows.append(dict(H1_finite_total_persistence=float(z*4),ball_vertices_r4=20+j%4,
                ball_vertices_r8=40+j%4,curvature_proxy=j%4,tetra_type=1,time_slice=0,Ds_32=float(z*2)))
        items.append({'rows':rows,'summary':{'seed':seed}})
    result=_matching(items)
    assert result['paired_geometry_effect']['mean_difference']==2
    assert result['retained_fraction']==1

def test_holm_and_constant_refusal():
    np.testing.assert_allclose(holm([.01,.03,.2]),[.03,.06,.2])
    with pytest.raises(ValueError):correlation_test(np.ones(10),np.arange(10))
    with pytest.raises(ValueError):holm([-.1])
    assert paired_effect([1,2,3,4],repetitions=199)['mean_difference']==2.5

@pytest.mark.parametrize('case',range(5))
def test_malformed_filtration_and_budgets(case):
    f=filtration_from_facets([(0,1,2)])
    if case==0:
        del f[(0,)];fn=lambda:persistence_prime(f,3)
    elif case==1:fn=lambda:persistence_prime(f,3,budget=2)
    elif case==2:fn=lambda:propagate(cycle(6),[0],8,max_work=1)
    elif case==3:fn=lambda:rooted(np.array([[0,1,2,3]]),[0],2,fields=[2,2])
    else:fn=lambda:independent_betti(f,0,3,max_entries=1)
    with pytest.raises(ValueError):fn()
