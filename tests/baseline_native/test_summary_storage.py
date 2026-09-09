import numpy as np
import pytest
from cdt_baseline.summary_storage import reduce_roots,CompactRootCube
from cdt_baseline.statistics import root_jackknife,dimension
from cdt_baseline.analysis import _summarize_curves
from cdt_baseline.io import load_json

@pytest.mark.parametrize('R',[2,8,16,64])
def test_compact_statistics_equal_full_root_cube(R):
    rng=np.random.default_rng(510+R);cube=rng.uniform(.005,.2,(4,16,R,65));cube[...,0]=1
    pop=rng.integers(R,R+100,size=(4,16))
    values={(c,s):reduce_roots(cube[c,s],int(pop[c,s])) for c in range(4) for s in range(16)}
    small=CompactRootCube.from_summaries(values,4,16)
    assert np.array_equal(small.means,cube.mean(axis=2))
    assert np.allclose(small.root_error,root_jackknife(cube,pop),rtol=1e-13,atol=1e-14)
    assert np.array_equal(small.half_ds,dimension(cube[:,:,:max(2,R//2)].mean(axis=2)),equal_nan=True)
    if R>8:assert sum(a.nbytes for a in (small.means,small.half_ds,small.root_error))<cube.nbytes/2


def test_every_downstream_numeric_result_matches(root):
    rng=np.random.default_rng(55);C,S,R,L=4,16,8,49
    x=np.arange(L);cube=np.exp(-rng.uniform(.01,.08,(C,S,R,1))*x)
    pop=np.full((C,S),100);floor=np.zeros((C,S))
    cfg=load_json(root/'configs/baseline/smoke.json')
    reduced={(c,s):reduce_roots(cube[c,s],100) for c in range(C) for s in range(S)}
    a,ab=_summarize_curves(cube,pop,floor,cfg,'identity-check')
    b,bb=_summarize_curves(CompactRootCube.from_summaries(reduced,C,S),pop,floor,cfg,'identity-check')
    def equivalent(a,b):
        if isinstance(a,np.ndarray):assert np.allclose(a,b,rtol=1e-13,atol=1e-13,equal_nan=True)
        elif isinstance(a,dict):
            assert a.keys()==b.keys()
            for k in a:equivalent(a[k],b[k])
        elif isinstance(a,list):
            assert len(a)==len(b)
            for x,y in zip(a,b):equivalent(x,y)
        elif isinstance(a,(float,np.floating)):assert a==pytest.approx(b,rel=1e-12,abs=1e-12,nan_ok=True)
        else:assert a==b
    equivalent(a,b);equivalent(ab,bb)

@pytest.mark.parametrize('case',['one_root','nonfinite','negative','small_population','missing'])
def test_invalid_compact_inputs(case):
    p=np.ones((8,20));pop=9
    if case=='one_root':p=p[:1]
    if case=='nonfinite':p[0,2]=np.nan
    if case=='negative':p[0,2]=-1
    if case=='small_population':pop=7
    with pytest.raises(ValueError):
        if case=='missing':CompactRootCube.from_summaries({},4,16)
        else:reduce_roots(p,pop)
