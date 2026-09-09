#!/usr/bin/env python3
"""Selected reproducible research workflows, with physical data kept separate.

This orchestrator never launches or relabels a physical CDT simulation. Native
physical readiness is audited via --mode physical-audit on the actual data clone.
"""
from pathlib import Path
import argparse,importlib.metadata,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
BASE='7086a739da6f3c0f56788e211c78424a0cf65c22'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=['verify','synthetic','physical-audit'],default='verify')
    ap.add_argument('--workers',type=int,default=2);ap.add_argument('--physical-repo',type=Path)
    ap.add_argument('--output-root',type=Path,default=ROOT/'results/confirmation')
    args=ap.parse_args()
    if not 1<=args.workers<=4:raise ValueError('workers must be 1..4')
    versions={p:importlib.metadata.version(p) for p in ['numpy','scipy','networkx','pytest','sympy','arviz']}
    repository={'checkout':False,'reference_commit':BASE}
    if (ROOT/'.git').exists():
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        if subprocess.call(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT)!=0:
            raise ValueError('checkout does not descend from the audited reference')
        repository.update(checkout=True,head=head)
    print(json.dumps(dict(environment=versions,repository=repository,mode=args.mode)),flush=True)
    if args.mode=='physical-audit':
        if args.physical_repo is None:raise ValueError('--physical-repo must point to the native clone containing raw files')
        commands=[['workflows/audit_physical_confirmation.py','--repo',str(args.physical_repo),'--output',str(args.output_root/'physical_audit')]]
    elif args.mode=='verify':
        commands=[['workflows/verify_confirmation_results.py'],['workflows/test_confirmation.py']]
    else:
        out=args.output_root
        commands=[['workflows/test_confirmation.py'],
          ['workflows/run_confirmation.py','--output',str(out/'census'),'--workers',str(args.workers)],
          ['workflows/run_confirmation.py','--output',str(out/'census'),'--analyze'],
          ['workflows/run_size_confirmation.py','--output',str(out/'finite_size'),'--workers',str(args.workers)],
          ['workflows/run_operator_confirmation.py','--output',str(out/'operators_final'),'--workers',str(args.workers)],
          ['workflows/run_diagnostic_calibration.py','--output',str(out/'diagnostic_calibration')],
          ['workflows/collect_confirmation_results.py','--run-root',str(out),'--output',str(out/'reports')]]
    env=os.environ.copy()
    for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:env[k]='1'
    for cmd in commands:
        result=subprocess.run([sys.executable,*cmd],cwd=ROOT,env=env)
        if result.returncode:return result.returncode
    print('Selected stages finished; physical reproduction gates are unchanged.',flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
