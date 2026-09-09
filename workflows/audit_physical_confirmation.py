#!/usr/bin/env python3
"""Read-only native physical CDT readiness audit; no simulator or gate modifications."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from cdt_confirmation.physical import audit_repository
from cdt_confirmation.provenance import identity,stage,write_json
from cdt_mechanisms.evidence import sha256,canonical

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=ROOT)
    ap.add_argument('--output',type=Path,default=ROOT/'results/confirmation/physical_audit')
    ap.add_argument('--minimum-chains',type=int,default=4);ap.add_argument('--minimum-ess',type=float,default=400.)
    args=ap.parse_args();report=audit_repository(args.repo,minimum_chains=args.minimum_chains,minimum_ess=args.minimum_ess)
    inputs={str(p):sha256(p) for p in (args.repo/'results/manifests').glob('*.json')}
    config=dict(repo=str(args.repo.resolve()),minimum_chains=args.minimum_chains,minimum_ess=args.minimum_ess,
                missing_requirements=report['missing_requirements'],
                audit_result_sha256=hashlib.sha256(canonical(report)).hexdigest())
    out,reused=stage(args.output,identity(config,inputs),lambda p:write_json(p/'audit.json',report))
    print(json.dumps(dict(status=report['status'],report=str(out/'audit.json'),reused=reused)))
    raise SystemExit(0 if report['status']=='READY_FOR_BASELINE_REVIEW' else 2)
if __name__=='__main__':main()
