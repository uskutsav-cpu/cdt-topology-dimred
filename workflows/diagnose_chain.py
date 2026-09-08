"""Summarize a completed chain after verifying its diagnostic-file hash."""
from pathlib import Path
import argparse, hashlib, io, json, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from diagnostics import summary

parser = argparse.ArgumentParser()
parser.add_argument('job')
args = parser.parse_args()
manifest = json.loads((ROOT / 'results/manifests' / f'{args.job}.json').read_text())
if manifest['status'] != 'complete':
    raise RuntimeError('wait for the existing chain driver to complete')
cfg = manifest['parameters']
path = ROOT / 'data/raw' / manifest['configuration_id'] / 'diagnostics.csv'
cutoff = cfg['tune'] + cfg['burn'] + cfg['samples'] * cfg.get('sample_stride', 1)
lines = path.read_bytes().splitlines(keepends=True)
prefix = [lines[0]]
for line in lines[1:]:
    if int(line.split(b',', 1)[0]) > cutoff:
        break
    prefix.append(line)
payload = b''.join(prefix)
digest = hashlib.sha256(payload).hexdigest()
assert digest == manifest['output_hashes'][str(path.relative_to(ROOT))]
data = np.genfromtxt(io.StringIO(payload.decode()), names=True, delimiter=',', dtype=None, encoding='utf8')
_, indices = np.unique(data['sweep'], return_index=True)
data = data[np.sort(indices)]
data = data[data['phase'] == 'measure']
assert len(data) == cfg['samples'] * cfg.get('sample_stride', 1)
record = {'job': manifest['configuration_id'], 'measurement_sweeps': len(data),
          'input_sha256': digest,
          'diagnostics': {key: summary(data[key]) for key in ['N0', 'N3', 'N31', 'peak_slice']}}
out = ROOT / 'results/tables' / f"{manifest['configuration_id']}_through{cfg['samples']}_diagnostics.json"
if out.exists():
    assert json.loads(out.read_text()) == record
else:
    out.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
