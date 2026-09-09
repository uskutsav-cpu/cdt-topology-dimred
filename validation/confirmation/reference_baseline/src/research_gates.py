"""Fail-closed production preconditions, distinct from synthetic software tests."""
import hashlib
import json
from pathlib import Path

REQUIRED_GATES = ('baseline_reproduction', 'effective_topology_2d_reproduction',
                  'coarsegrain_3d_validation', 'microscopic_mapping_validation')


class GateClosedError(RuntimeError):
    pass


def require_production_gates(root, gate_file):
    root = Path(root).resolve()
    records = json.loads(Path(gate_file).read_text())
    validated = {}
    for gate in REQUIRED_GATES:
        record = records.get(gate, {})
        if record.get('status') != 'PASS' or not record.get('evidence'):
            raise GateClosedError(f'{gate}: not passed with evidence; synthetic tests do not open this gate')
        for source in record['evidence']:
            path = (root / source['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise GateClosedError(f'{gate}: evidence missing or outside repository')
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != source.get('sha256'):
                raise GateClosedError(f'{gate}: evidence hash mismatch')
        validated[gate] = record
    return validated
