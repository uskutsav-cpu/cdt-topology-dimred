"""Single-writer entry point that preserves the original driver's job hashes.

Usage: python workflows/run_chain_safe.py CONFIG [--resume] [--extend-job ID]
The original run_chain.py is left unchanged so completed-job cache keys and
same-binary checkpoint contracts do not change just to add locking.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from runtime_safety import job_lock


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_job(root, config, extend_job=None):
    root = Path(root)
    if extend_job is not None:
        if len(extend_job) != 20 or any(c not in '0123456789abcdef' for c in extend_job):
            raise ValueError('invalid job id')
        return extend_job
    cfg = json.loads(Path(config).read_text())
    cfg.setdefault('sample_stride', 1)
    contract = {'parameters': cfg, 'binary_sha256': sha(root / 'build/simulator/cdt-run'),
                'input_sha256': sha(root / cfg['input']),
                'driver_sha256': sha(root / 'workflows/run_chain.py')}
    if cfg.get('initial_checkpoint'):
        contract['initial_checkpoint_sha256'] = sha(root / cfg['initial_checkpoint'])
    return hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()[:20]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--extend-job')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    job = resolve_job(ROOT, args.config, args.extend_job)
    driver = ROOT / 'workflows/run_chain.py'
    forwarded = [str(driver), args.config]
    if args.resume:
        forwarded.append('--resume')
    if args.extend_job:
        forwarded.extend(['--extend-job', args.extend_job])
    if args.dry_run:
        print(json.dumps({'job': job, 'argv': forwarded, 'will_run': False}))
        return
    with job_lock(ROOT / 'results/locks' / (job + '.lock'), metadata={'job': job}):
        if resolve_job(ROOT, args.config, args.extend_job) != job:
            raise RuntimeError('job inputs changed while acquiring lock')
        old_argv = sys.argv
        try:
            sys.argv = forwarded
            runpy.run_path(str(driver), run_name='__main__')
        finally:
            sys.argv = old_argv


if __name__ == '__main__':
    main()
