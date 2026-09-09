"""Run the explicitly scoped Python continuation suite, not legacy C++ tests."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
TESTS=[
 'tests/test_topology_foundations.py','tests/test_coarsegrain_foundations.py',
 'tests/test_conditioned_analysis.py','tests/test_runtime_foundations.py',
 'tests/test_conditioned_workflow.py','tests/test_integral_topology.py',
 'tests/test_conditioned_stochastic.py','tests/test_microscopic_carriers.py',
 'tests/test_controls_hierarchy.py','tests/test_fast_workflow.py',
]


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--junitxml')
    args=ap.parse_args(argv)
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+env.get('PYTHONPATH','')
    cmd=[sys.executable,'-m','pytest','-q',*TESTS]
    if args.junitxml:cmd.extend(['--junitxml',args.junitxml])
    return subprocess.run(cmd,cwd=ROOT,env=env).returncode


if __name__=='__main__':raise SystemExit(main())
