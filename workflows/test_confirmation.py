#!/usr/bin/env python3
"""Run the selected scientific suites; explicitly not the full legacy C++ suite."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--without-baseline',action='store_true')
    ap.add_argument('--junitxml')
    args,extra=ap.parse_known_args()
    tests=['tests/mechanisms','tests/confirmation'];paths=[str(ROOT/'src')]
    if not args.without_baseline:
        ref=ROOT/'validation/confirmation/reference_baseline'
        audit=json.loads((ROOT/'validation/confirmation/baseline-source-audit.json').read_text())
        for item in audit['files']:
            p=ref/item['path'];b=p.read_bytes()
            actual=hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
            if actual!=item['expected']:raise RuntimeError(f'baseline snapshot differs: {p}')
        # Isolate the pinned compatibility fixture; do not claim to test newer core files.
        paths.insert(0,str(ref/'src'))
        tests.extend(str(p.relative_to(ROOT)) for p in sorted((ref/'tests').glob('test_*.py')))
    env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(paths)
    for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:env[key]='1'
    cmd=[sys.executable,'-m','pytest','-q',*tests]
    if args.junitxml:cmd.extend(['--junitxml',args.junitxml])
    cmd+=extra
    print('Selected suites only: mechanism, confirmation, and optional pinned Python compatibility fixture.',flush=True)
    return subprocess.call(cmd,cwd=ROOT,env=env)
if __name__=='__main__':raise SystemExit(main())
