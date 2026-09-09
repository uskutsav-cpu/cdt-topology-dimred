#!/usr/bin/env python3
"""Verify selected evidence stages, every artifact hash, and executing source snapshots."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from cdt_confirmation.provenance import verify
from cdt_mechanisms.evidence import sha256

def verify_selected(root=ROOT):
    root=Path(root)
    selection=json.loads((root/'docs/confirmation/FINAL_RUNS.json').read_text())
    stages=set()
    for key,rel in selection.items():
        if not key.endswith('_root'):stages.add((root/rel).parent)
    idx=json.loads((root/selection['primary_root']/'index.json').read_text())
    stages.update(root/selection['primary_root']/r['path'] for r in idx['records'])
    for name in ['finite_size','operators']:
        summary=json.loads((root/selection[name+'_analysis']).read_text())
        stages.update(root/selection[name+'_root']/r['path'] for r in summary['records'])
    stages.update(p.parent for p in (root/selection['operators_root']/'reference').glob('*/manifest.json'))
    artifact_count=0;total_bytes=0
    for path in sorted(stages):
        m=verify(path)
        for rel,digest in m['identity']['source'].items():
            if sha256(root/'src'/rel)!=digest:raise ValueError('source no longer matches evidence: '+rel)
        artifact_count+=len(m['artifacts'])
        total_bytes+=sum((path/rel).stat().st_size for rel in m['artifacts'])
    return dict(stages_verified=len(stages),artifacts_verified=artifact_count,artifact_bytes=total_bytes,
                source_snapshots_match=True,physical_CDT_result=False,production_gates_changed=False)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--output',type=Path);args=ap.parse_args();result=verify_selected(args.root)
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
