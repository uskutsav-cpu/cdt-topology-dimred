"""Verify saved artifacts against their hashes and optionally current source."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from evidence_io import verify_bundle


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory',type=Path)
    ap.add_argument('--check-source',action='store_true')
    args=ap.parse_args(argv)
    result=verify_bundle(args.directory,source_root=ROOT if args.check_source else None)
    print(json.dumps({'status':'VERIFIED','artifact_count':len(result['artifacts']),
                      'source_checked':args.check_source,'physics_validation':False}))


if __name__=='__main__':main()
