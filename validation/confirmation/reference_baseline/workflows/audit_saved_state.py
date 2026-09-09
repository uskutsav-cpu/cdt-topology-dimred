"""Report saved evidence once; --only-changes suppresses identical output."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from saved_state import audit_saved_state
from runtime_safety import atomic_json


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--only-changes', type=Path, help='cached summary; no polling loop is started')
    args = ap.parse_args()
    result = audit_saved_state(args.root)
    if args.output:
        atomic_json(args.output, result)
    if args.only_changes:
        if args.only_changes.exists() and json.loads(args.only_changes.read_text()) == result:
            return
        atomic_json(args.only_changes, result)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
