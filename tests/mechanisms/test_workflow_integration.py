from pathlib import Path
import json
import numpy as np
import pytest
from cdt_mechanisms.study import measure_geometry,save_measurement,analyze_saved_ensemble
from cdt_mechanisms.evidence import sha256,verify_run,create_run
from cdt_mechanisms.triangulations import product_cdt,bipyramid,stacked_sphere,write_geometry
from cdt_mechanisms.diffusion import exact_diffusion
from cdt_mechanisms.graph import from_neighbors

def test_complete_measurement_against_all_start_trace(tmp_path):
    g=product_cdt(bipyramid(6),3)
    result=measure_geometry(g,n_roots=6,max_steps=32,radii=[1,2,3],topology_roots=2,topology_horizon=3)
    all_roots=exact_diffusion(from_neighbors(g.neighbors),np.arange(len(g.tetra)),32)
    np.testing.assert_allclose(result['operators']['full_discrete_trace']['returns'],all_roots.returns.mean(axis=0),atol=1e-14)
    assert result['global_betti']==[1,1,1,1]
    save_measurement(tmp_path,'sample',result)
    assert (tmp_path/'sample/persistence.json').exists()
    arr=np.load(tmp_path/'sample/diffusion.npz',allow_pickle=False)
    assert arr['returns'].shape==(6,33)

def test_ensemble_adapter_executes_without_promoting_physics(tmp_path):
    records=[]
    for seed in range(3):
        g=product_cdt(stacked_sphere(9,seed=seed),3)
        path=tmp_path/f'fixture_{seed}.dat'; write_geometry(g,path)
        records.append(dict(configuration_id=f'fixture-{seed}',chain_id=f'synthetic-seed-{seed}',
                      coupling=float(seed),geometry=path.name,geometry_sha256=sha256(path),sweep=0,
                      provenance='synthetic test fixture, not a CDT coupling run'))
    manifest=dict(schema='cdt-mechanisms-ensemble-v1',configurations=records)
    config=dict(n_roots=8,max_steps=24,radii=[1,2,3],seed=21,
                primary_radius=2,primary_sigma=8,topology_roots=1,topology_horizon=3)
    out=tmp_path/'analysis'; out.mkdir()
    analyze_saved_ensemble(out,manifest,tmp_path,config)
    report=json.loads((out/'ensemble_analysis.json').read_text())
    assert report['scientific_status']=='EXPLORATORY_ONLY'
    assert report['no_thermalization_or_baseline_gate_inferred'] and not report['production_gates_changed']
    assert len(report['configurations'])==3

def test_invalid_measurement_root_count():
    with pytest.raises(ValueError): measure_geometry(product_cdt(bipyramid(6),3),n_roots=1)
