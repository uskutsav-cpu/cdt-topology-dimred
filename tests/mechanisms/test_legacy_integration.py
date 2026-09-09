"""Actual pinned repository validator, hash-checked against the GitHub blob."""
from pathlib import Path
import hashlib
import importlib.util
import sys
import numpy as np
import pytest
from cdt_mechanisms.triangulations import *

REFERENCE=Path(__file__).parent/'reference/geometry_7086a739.py'
spec=importlib.util.spec_from_file_location('cdt_mechanisms_legacy_geometry',REFERENCE)
legacy=importlib.util.module_from_spec(spec); sys.modules[spec.name]=legacy; spec.loader.exec_module(legacy)

def test_reference_is_exact_github_blob():
    body=REFERENCE.read_bytes()
    assert hashlib.sha1(f'blob {len(body)}\0'.encode()+body).hexdigest()=='c4205be18d7cb71b6ae722436319e966f6a117b5'

@pytest.mark.parametrize('seed',range(8))
def test_surgery_roundtrip_through_original_repo_validator(seed,tmp_path):
    faces,_=random_flips(stacked_sphere(12,seed=seed),30,seed=100+seed)
    g=product_cdt(faces,4); a=audit_cdt(g)
    path=tmp_path/'geometry.dat'; write_geometry(g,path)
    old=legacy.read_geometry(path); b=legacy.validate(old,links=True)
    for key in ('N0','N1','N2','N3','chi','time_extent','spatial_volume','tetra_types','all_vertex_links_S2'):
        assert a[key]==b[key]
    restored=tmp_path/'from_original.dat'; legacy.write_geometry(old,restored)
    assert path.read_bytes()==restored.read_bytes()
