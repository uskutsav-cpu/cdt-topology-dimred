import numpy as np
import pytest
from cdt_mechanisms.fem import metric_mesh,assemble,midpoint_refinement,refinement_audit,full_spectrum
from cdt_mechanisms.triangulations import product_cdt,bipyramid
from cdt_mechanisms.diffusion import heat_trace_dimension
from cdt_confirmation.operators import low_modes,trace_bounds,calibrate_clock,dual_spectrum

@pytest.mark.parametrize('seed',range(12))
def test_omitted_tail_encloses_exact_finite_trace(seed):
    rng=np.random.default_rng(seed);w=np.r_[0,np.sort(rng.gamma(2,3,size=99))]
    t=np.geomspace(.01,10,40);truth=heat_trace_dimension(w,t)['ds']
    for k in [2,10,50,100]:
        spec=dict(eigenvalues=w[:k],n_modes=k,n_total=len(w),zero_modes=1,complete=k==len(w))
        bound=trace_bounds(spec,t)
        assert np.all(bound['ds_lower']<=truth+1e-12)
        assert np.all(bound['ds_upper']>=truth-1e-12)
        if k==len(w):np.testing.assert_allclose(bound['ds_truncated'],truth)

@pytest.mark.parametrize('side',[6,8,10])
def test_sparse_generalized_eigensolver_and_patch(side):
    g=product_cdt(bipyramid(side),3);mesh=metric_mesh(g.tetra);coarse=assemble(mesh)
    dense=full_spectrum(coarse);partial=low_modes(coarse,k=12,dense_limit=0)
    np.testing.assert_allclose(partial['eigenvalues'],dense['eigenvalues'][:12],rtol=1e-8,atol=1e-8)
    refined,p=midpoint_refinement(mesh);fine=assemble(refined);refinement_audit(coarse,fine,p)
    low=low_modes(fine,k=12,dense_limit=0)
    assert np.all(low['eigenvalues'][1:12]<=partial['eigenvalues'][1:12]+1e-8)
    assert low['residual']<1e-7

def test_fixed_clock_not_per_geometry_fit():
    dual=np.arange(20,dtype=float);fem=dual*17
    clock=calibrate_clock(dual,fem)
    assert clock['fem_eigenvalue_to_dual_ratio']==17
    assert not clock['unique_physical_clock_established']
    spectrum=dual_spectrum(product_cdt(bipyramid(6),3))
    assert spectrum['complete'] and spectrum['eigenvalues'][0]<1e-8

@pytest.mark.parametrize('case',range(4))
def test_bad_operator_contract(case):
    if case==0:fn=lambda:trace_bounds(dict(eigenvalues=[1,0],n_modes=2,n_total=3,complete=False,zero_modes=1),[1])
    elif case==1:fn=lambda:trace_bounds(dict(eigenvalues=[0,1],n_modes=2,n_total=3,complete=True,zero_modes=1),[1])
    elif case==2:fn=lambda:calibrate_clock([0,0,1],[0,1,2],1,3)
    else:fn=lambda:trace_bounds(dict(eigenvalues=[0,1],n_modes=2,n_total=2,complete=True,zero_modes=1),[0])
    with pytest.raises(ValueError):fn()
