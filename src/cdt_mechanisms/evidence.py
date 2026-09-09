"""Atomic, input-addressed evidence with strict hashes and no invented PASS gates."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from dataclasses import is_dataclass,asdict
import hashlib
import json
import os
import platform
import tempfile
import numpy as np


def jsonable(value):
    if is_dataclass(value): return jsonable(asdict(value))
    if isinstance(value,dict): return {str(k):jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [jsonable(v) for v in value]
    if isinstance(value,np.ndarray): return jsonable(value.tolist())
    if isinstance(value,np.generic): return jsonable(value.item())
    if isinstance(value,float) and not np.isfinite(value): return None
    if isinstance(value,Path): return str(value)
    return value


def canonical(value) -> bytes:
    return json.dumps(jsonable(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha256(path) -> str:
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for part in iter(lambda:handle.read(1024*1024),b''): h.update(part)
    return h.hexdigest()


def source_manifest() -> dict:
    root=Path(__file__).resolve().parent
    return {p.name:sha256(p) for p in sorted(root.glob('*.py'))}


def environment() -> dict:
    import scipy,networkx
    return dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
                networkx=networkx.__version__,platform=platform.platform())


def write_json(path,value):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation. Existing results are never silently replaced.
    with p.open('x') as handle:
        json.dump(jsonable(value),handle,indent=2,sort_keys=True,allow_nan=False); handle.write('\n')


@contextmanager
def exclusive_lock(path):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(fd,'w') as handle: handle.write(str(os.getpid()))
        yield
    finally:
        p.unlink(missing_ok=True)


def verify_run(path,expected_identity=None) -> dict:
    root=Path(path)
    if root.is_symlink(): raise ValueError('evidence root must not be a symlink')
    manifest=root/'manifest.json'
    if not manifest.is_file(): raise ValueError("incomplete run: manifest absent")
    saved=json.loads(manifest.read_text())
    if saved.get('schema')!='cdt-mechanisms-evidence-v1' or saved.get('completed') is not True:
        raise ValueError("unrecognized or incomplete evidence")
    if expected_identity is not None and saved.get('identity')!=jsonable(expected_identity):
        raise ValueError("evidence identity does not match current inputs/source/environment")
    files=saved.get('artifacts')
    if not isinstance(files,dict) or not files: raise ValueError("empty artifact manifest")
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != manifest}
    if actual!=set(files): raise ValueError("artifact set differs from manifest")
    for rel,digest in files.items():
        p=root/rel
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()): raise ValueError("unsafe artifact path")
        if not p.is_file() or sha256(p)!=digest: raise ValueError(f"artifact hash mismatch: {rel}")
    return saved


def create_run(output_root,config,producer,*,external_inputs=None) -> tuple[Path,bool]:
    """Compute in a private temp directory, publish only after complete hashing.

    The identity includes package source, environment, configuration and declared
    input file hashes. Incomplete temp folders never count as completed runs.
    """
    output=Path(output_root); output.mkdir(parents=True,exist_ok=True)
    identity=dict(config=config,source=source_manifest(),environment=environment(),
                  external_inputs=external_inputs or {})
    run_id=hashlib.sha256(canonical(identity)).hexdigest()[:20]; target=output/run_id
    with exclusive_lock(output/(run_id+'.lock')):
        if target.exists(): verify_run(target,identity); return target,True
        with tempfile.TemporaryDirectory(prefix='.mechanisms-',dir=output) as temp:
            root=Path(temp); producer(root)
            artifacts={p.relative_to(root).as_posix():sha256(p) for p in sorted(root.rglob('*')) if p.is_file()}
            if not artifacts: raise ValueError("producer emitted no evidence")
            write_json(root/'manifest.json',dict(schema='cdt-mechanisms-evidence-v1',completed=True,
                       identity=identity,artifacts=artifacts,
                       scientific_status='SYNTHETIC_OR_EXPLORATORY_ONLY',production_gates_changed=False))
            verify_run(root,identity)
            os.rename(root,target)
        return target,False


def require_ensemble_manifest(value,*,root=None) -> dict:
    """Strict schema for the EXPLORATORY saved-geometry workflow.

    Self-reported thermalized=true never upgrades a result to a physics finding.
    This update has no authority to alter the existing repository gates.
    """
    if not isinstance(value,dict) or value.get('schema')!='cdt-mechanisms-ensemble-v1':
        raise ValueError("invalid ensemble schema")
    records=value.get('configurations')
    if not isinstance(records,list) or not records: raise ValueError("no configuration data")
    seen=set(); chain_coupling={}; base=Path(root or '.').resolve(); hashes={}
    for record in records:
        required={'configuration_id','chain_id','coupling','geometry','geometry_sha256','sweep'}
        if not isinstance(record,dict) or not required<=set(record): raise ValueError("missing configuration metadata")
        cid=record['configuration_id']; chain=record['chain_id']; coupling=record['coupling']
        if not isinstance(cid,str) or not cid or cid in seen or not isinstance(chain,str) or not chain:
            raise ValueError("invalid/duplicate configuration or chain ID")
        seen.add(cid)
        if not isinstance(coupling,(int,float)) or not np.isfinite(coupling): raise ValueError("invalid coupling")
        if chain in chain_coupling and chain_coupling[chain]!=coupling: raise ValueError("chain changes coupling")
        chain_coupling[chain]=coupling
        if not isinstance(record['sweep'],int) or record['sweep']<0: raise ValueError("invalid sweep")
        p=(base/record['geometry']).resolve()
        if not p.is_file() or sha256(p)!=record['geometry_sha256']: raise ValueError("missing or hash-mismatched geometry")
        if str(p) in hashes: raise ValueError("same geometry path appears twice")
        if record['geometry_sha256'] in hashes.values(): raise ValueError("duplicated geometry bytes are not independent configurations")
        hashes[str(p)]=record['geometry_sha256']
    return dict(configurations=len(records),chains=len(chain_coupling),
                coupling_levels=len(set(chain_coupling.values())),input_hashes=hashes,
                scientific_status='EXPLORATORY_ONLY',production_gates_changed=False)
