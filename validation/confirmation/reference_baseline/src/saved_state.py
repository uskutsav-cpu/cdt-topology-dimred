"""Read-only, one-shot summary of saved evidence; never claims a process is live."""
import hashlib
import json
import math
from pathlib import Path

BASELINE_JOBS = ('4a40078dbf0e6b9a5f5c', '8b3e5e63ecacfa361207')
REQUIRED_OBSERVABLES = ('N0', 'N3', 'N31', 'peak_slice')


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def comparison_screen(record):
    """Recheck saved numerical thresholds; do not turn these into certification."""
    problems = []
    jobs = record.get('jobs', [])
    if len(jobs) < 2 or len(jobs) != len(set(jobs)):
        problems.append('independent chain IDs missing or repeated')
    for name in REQUIRED_OBSERVABLES:
        obs = record.get('observables', {}).get(name, {})
        rhat = obs.get('rank_folded_split_rhat')
        ess = obs.get('minimum_split_single_chain_ess')
        if not _finite(rhat) or not 0 < rhat < 1.01:
            problems.append(f'{name}: Rhat does not pass <1.01')
        if not _finite(ess) or ess < 50:
            problems.append(f'{name}: minimum split ESS does not pass >=50')
        summaries = obs.get('full_chain_summaries', [])
        if len(summaries) != len(jobs):
            problems.append(f'{name}: full-chain summaries missing')
        for i, summary in enumerate(summaries):
            n_eff, z = summary.get('effective_samples'), summary.get('split_z')
            if (not _finite(n_eff) or n_eff < 50 or not _finite(z) or not 0 <= z < 2
                    or summary.get('screen_pass') is not True):
                problems.append(f'{name}: chain {i} does not pass stored per-chain screen')
    return {'configured_screens_pass': not problems, 'problems': problems,
            'equilibrium_certified': False,
            'warning': 'Saved diagnostics only; single-chain ESS is not multichain bulk/tail ESS.'}


def audit_saved_state(root, jobs=BASELINE_JOBS):
    root = Path(root)
    comparisons, errors = [], []
    for path in sorted((root / 'results/tables').glob('chain_comparison_*.json')):
        try:
            rec = json.loads(path.read_text())
            if not isinstance(rec, dict):
                raise ValueError('expected JSON object')
            sweeps = rec.get('common_prefix_sweeps')
            if set(rec.get('jobs', [])) == set(jobs) and _finite(sweeps) and sweeps > 0:
                comparisons.append((sweeps, str(path), rec))
        except (ValueError, TypeError, OSError) as exc:
            errors.append({'path': str(path.relative_to(root)), 'error': str(exc)})
    selected = None
    if comparisons:
        _, path, rec = max(comparisons, key=lambda t: (t[0], t[1]))
        path = Path(path)
        selected = {'path': str(path.relative_to(root)),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'common_prefix_sweeps': rec['common_prefix_sweeps'],
                    'peak_slice': rec.get('observables', {}).get('peak_slice'),
                    **comparison_screen(rec)}
    manifests = []
    for path in sorted((root / 'results/manifests').glob('*.json')):
        if '.through_' in path.name:
            continue
        try:
            rec = json.loads(path.read_text())
            if not isinstance(rec, dict):
                raise ValueError('expected JSON object')
            if rec.get('stage') == 'simulation':
                manifests.append({'job': rec.get('configuration_id', path.stem),
                                  'saved_status': rec.get('status', 'unknown'),
                                  'previous_completed_samples': rec.get('previous_revision', {}).get('completed_samples'),
                                  'target': rec.get('parameters', {}).get('target'),
                                  'k0': rec.get('parameters', {}).get('k0')})
        except (ValueError, TypeError, OSError) as exc:
            errors.append({'path': str(path.relative_to(root)), 'error': str(exc)})
    return {'baseline_comparison': selected, 'simulation_manifests': manifests,
            'read_errors': errors, 'live_process_status': 'NOT_OBSERVED',
            'raw_geometry_hashes_verified': False,
            'reproduction_gate_decided_by_this_audit': False,
            'note': 'A saved running flag is not evidence of a currently active worker.'}
