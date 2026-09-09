#!/usr/bin/env python3
"""Create a NEW clean checkout of an already-pushed baseline-code branch.

Does not overlay uncommitted files, reset a checkout, or push anything. Environment
and result directories are outside the checkout, so generated files do not turn
source cleanliness into a false claim. --run is explicit and may use a large budget.
"""
from pathlib import Path
import argparse,json,os,re,subprocess,sys
from datetime import datetime,timezone
REPO='https://github.com/uskutsav-cpu/cdt-topology-dimred.git'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('destination',type=Path)
    ap.add_argument('--branch',default='native-baseline-review')
    ap.add_argument('--config',default='configs/baseline/production.json')
    ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--timeout-seconds',type=float,default=7200)
    ap.add_argument('--run',action='store_true')
    args=ap.parse_args();dest=args.destination.expanduser().absolute()
    if dest.exists() or dest.is_symlink():raise ValueError('destination exists; refusing to overwrite or clean it')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*',args.branch):raise ValueError('invalid branch name')
    config=Path(args.config)
    if config.is_absolute() or '..' in config.parts:raise ValueError('config must be inside the checkout')
    venv=dest.with_name(dest.name+'-venv');output=dest.with_name(dest.name+'-results')
    if venv.exists() or output.exists():raise ValueError('sibling environment/results paths already exist')
    subprocess.run(['git','clone','--recurse-submodules',f'--branch={args.branch}',REPO,str(dest)],check=True)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=dest,text=True).strip()
    dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=dest,text=True)
    if dirty:raise ValueError('new checkout is not clean; retained for inspection')
    if not (dest/'src/cdt_baseline/native.py').is_file():raise ValueError('selected branch does not contain the baseline update; push that branch first')
    receipt=dict(head=head,branch=args.branch,clean=True,created_at=datetime.now(timezone.utc).isoformat(),
                 submodules=subprocess.check_output(['git','submodule','status','--recursive'],cwd=dest,text=True),
                 cloning_method='git clone --recurse-submodules; no source overlay')
    (dest/'.git/baseline-clean-checkout.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2),flush=True)
    if not args.run:return 0
    subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
    python=venv/'bin/python'
    subprocess.run([str(python),'-m','pip','install','-r',str(dest/'environment/baseline-requirements.txt')],check=True)
    subprocess.run([str(python),str(dest/'workflows/test_native_baseline.py')],cwd=dest,check=True)
    return subprocess.call([str(python),str(dest/'workflows/baseline.py'),'all','--config',str(dest/config),
                            '--output',str(output),'--workers',str(args.workers),'--timeout-seconds',str(args.timeout_seconds)],cwd=dest)
if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:raise SystemExit(130)
