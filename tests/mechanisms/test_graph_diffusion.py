import numpy as np
import networkx as nx
import pytest
from scipy import sparse
from cdt_mechanisms.graph import adjacency,from_neighbors,cut,digest,distances
from cdt_mechanisms.diffusion import transition,exact_diffusion,spectral_dimension,log_slope,fit_walk_dimension,heat_trace_dimension
from cdt_mechanisms.bottlenecks import local_features,fiedler_sweep,wired_annulus_separator

def adj(g): return nx.to_scipy_sparse_array(g,format='csr',dtype=float)

@pytest.mark.parametrize('bad',[
 np.ones((2,3)),np.array([[0,1],[0,0]]),np.array([[0,-1],[-1,0]]),
 np.array([[1,1],[1,0]]),np.array([[0,np.nan],[np.nan,0]]),
 np.zeros((3,3)),np.array([[0,1,0,0],[1,0,0,0],[0,0,0,1],[0,0,1,0]])])
def test_bad_graphs(bad):
    with pytest.raises(ValueError): adjacency(bad)

@pytest.mark.parametrize('neighbors',[[[1,1],[0,0]],[[1,2],[0,0]],[[1.],[0.]],[[0],[1]]])
def test_bad_neighbors(neighbors):
    with pytest.raises(ValueError): from_neighbors(neighbors)

@pytest.mark.parametrize('n',[4,7,12,19])
@pytest.mark.parametrize('q',[.25,.5,1.])
def test_exact_against_dense(n,q):
    a=adj(nx.cycle_graph(n)); p=transition(a,q).toarray()
    r=exact_diffusion(a,[0,n//2],16,moving_probability=q,batch_size=1)
    dense=np.eye(n); d=distances(a,[0,n//2])
    for step in range(17):
        for k,root in enumerate(r.roots):
            assert np.isclose(r.returns[k,step],dense[root,root],atol=1e-13)
            assert np.isclose(r.mean_square_distance[k,step],dense[root]@(d[k]**2),atol=1e-12)
        dense=dense@p
    assert r.mass_error<1e-12

@pytest.mark.parametrize('q',[0,-.2,1.1,float('nan')])
def test_bad_q(q):
    with pytest.raises(ValueError): transition(adj(nx.path_graph(4)),q)

@pytest.mark.parametrize('roots',[[0,0],[-1],[4],[],[1.2]])
def test_bad_roots(roots):
    with pytest.raises(ValueError): exact_diffusion(adj(nx.path_graph(4)),roots,10)

def test_weighted_stationary():
    a=adj(nx.path_graph(5)); a.data=np.arange(len(a.data))+1. # then symmetrize
    a=(a+a.T)/2
    r=exact_diffusion(a,[0,2],500)
    np.testing.assert_allclose(r.returns[:,-1],r.stationary_return,rtol=1e-8)
    assert not spectral_dimension(r)['pre_mix'][:,-3].any()

def test_no_restricted_operator():
    a=adj(nx.path_graph(15)); r=exact_diffusion(a,[7],40)
    local=exact_diffusion(adj(nx.path_graph(3)),[1],40)
    assert abs(r.returns[0,-1]-local.returns[0,-1])>.1

def test_cut_undefined_for_full_or_empty():
    a=adj(nx.cycle_graph(10))
    assert np.isnan(cut(a,np.arange(10)).conductance)
    assert np.isnan(cut(a,np.array([],dtype=int)).conductance)
    c=cut(a,[0,1,2,3,4]); assert c.boundary_weight==2 and c.conductance==.2

@pytest.mark.parametrize('power',[.5,1,1.5,2,3])
def test_log_power_exact(power):
    x=np.geomspace(1,100,25); y=x**(-power/2)
    np.testing.assert_allclose(-2*log_slope(x,y)[2:-2],power,atol=1e-11)
    assert np.isnan(log_slope(x,y)[0])

def test_log_zero_invalid_not_clipped():
    x=np.arange(15); y=np.ones(15); y[7]=0
    result=log_slope(x,y)
    assert np.isnan(result[5:10]).all()

def test_cycle_walk_dimension():
    r=exact_diffusion(adj(nx.cycle_graph(256)),[0],64)
    fit=fit_walk_dimension(r,4,32)
    assert abs(fit['walk_dimension']-2)<1e-8
    np.testing.assert_allclose(r.mean_square_distance[0],.5*r.sigma,atol=1e-10)

def test_work_budget():
    with pytest.raises(ValueError,match='budget'):
        exact_diffusion(adj(nx.cycle_graph(30)),list(range(20)),100,max_work=100)

@pytest.mark.parametrize('n',[6,9,16,23])
def test_cheeger_bruteforce_small(n):
    a=adj(nx.cycle_graph(n)); result=fiedler_sweep(a)
    expected=1/(n//2)
    assert result['cheeger_lower_bound']<=expected+1e-12
    assert expected<=result['cheeger_upper_bound']+1e-12
    assert abs(result['sweep_conductance']-expected)<1e-10

def test_fiedler_sparse_path():
    a=adj(nx.cycle_graph(150)); result=fiedler_sweep(a)
    assert abs(result['sweep_conductance']-1/75)<1e-10
    assert not result['exact_cheeger']

def test_separator_certificate():
    a=adj(nx.barbell_graph(7,5)); result=wired_annulus_separator(a,0,1,3)
    assert result['cut_weight']==1
    assert cut(a,result['witness_vertices']).boundary_weight==1
    with pytest.raises(ValueError): wired_annulus_separator(a,0,1,100)

def test_local_cycles_are_graph_not_manifold():
    a=adj(nx.complete_graph(4)); f=local_features(a,[0],[1])[0]
    assert f['graph_cycle_rank']==3 and f['saturated_ball']
    assert np.isnan(f['conductance'])

def test_tree_proxy_zero_cycle_rank():
    a=adj(nx.balanced_tree(2,5)); f=local_features(a,[0],[2,3])
    assert all(row['graph_cycle_rank']==0 for row in f)
    assert f[1]['spanning_annular_branches']>=2

def test_graph_hash_weight_sensitive():
    a=adj(nx.path_graph(5)); assert digest(a)==digest(a.tocoo())
    assert digest(a)!=digest(a*2)

def test_heat_trace_derivative():
    vals=np.array([0.,1.,2.,3.]); times=np.geomspace(.01,10,100)
    r=heat_trace_dimension(vals,times)
    numerical=-2*log_slope(times,r['return_trace'])
    np.testing.assert_allclose(numerical[2:-2],r['ds'][2:-2],atol=.01)
    assert heat_trace_dimension(vals,[1000.])['ds'][0]==0
