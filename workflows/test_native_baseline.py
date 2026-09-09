#!/usr/bin/env python3
"""Run the native-baseline suite, including fresh C++ builds and restart tests."""
from pathlib import Path
import os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src')
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):env[k]='1'
launcher="import multiprocessing as mp,sys; mp.set_start_method('spawn'); import pytest; raise SystemExit(pytest.main(sys.argv[1:]))"
raise SystemExit(subprocess.call([sys.executable,'-c',launcher,'-q',str(ROOT/'tests/baseline_native'),*sys.argv[1:]],cwd=ROOT,env=env))
