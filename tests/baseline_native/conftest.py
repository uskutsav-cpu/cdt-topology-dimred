from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))

@pytest.fixture(scope='session')
def root():return ROOT

@pytest.fixture(scope='session')
def build(root):
    from cdt_baseline.native import build_native
    return build_native(root,capacity=200000)

@pytest.fixture(scope='session')
def native_seed(tmp_path_factory):
    from cdt_baseline.initial import write_seed
    p=tmp_path_factory.mktemp('initial')/'initial_T8.dat';write_seed(8,p);return p

@pytest.fixture
def parameters():
    return dict(seed=719,k0=1.,k3=1.16,target=300,tune=0,burn=20,samples=4,attempts=1000,check_every_move=0,sample_stride=3)

@pytest.fixture(scope='session')
def validator(root):
    from cdt_baseline.measure import compile_validator
    return root/compile_validator(root)['binary']
