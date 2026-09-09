"""Immutable, hash-verified, independently resumable stages with POSIX advisory locks."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import hashlib, json, os, platform, tempfile, fcntl
import numpy as np
from cdt_mechanisms.evidence import canonical, jsonable, sha256, environment


def write_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:
        json.dump(jsonable(value),f,indent=2,sort_keys=True,allow_nan=False); f.write('\n');f.flush();os.fsync(f.fileno())


def source_hashes():
    src=Path(__file__).resolve().parents[1]
    return {p.relative_to(src).as_posix():sha256(p) for name in ['cdt_confirmation','cdt_mechanisms']
            for p in sorted((src/name).glob('*.py'))}


def identity(config,inputs=None,*,sources=None):
    return dict(config=config,inputs=inputs or {},source=sources if sources is not None else source_hashes(),environment=environment())


def verify(path,expected=None):
    root=Path(path)
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob('*')): raise ValueError('symlink stage forbidden')
    p=root/'manifest.json'
    if not p.is_file(): raise ValueError('incomplete stage')
    m=json.loads(p.read_text())
    if m.get('schema')!='cdt-confirmation-stage-v1' or m.get('complete') is not True: raise ValueError('invalid manifest')
    if expected is not None and m['identity']!=jsonable(expected): raise ValueError('identity mismatch')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'manifest.json'}
    if not m.get('artifacts') or actual!=set(m['artifacts']): raise ValueError('artifact set mismatch')
    for rel,digest in m['artifacts'].items():
        p=root/rel
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()) or sha256(p)!=digest: raise ValueError('corrupt artifact: '+rel)
    return m


@contextmanager
def lock(path):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a+') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(f,fcntl.LOCK_UN)


def stage(output,ident,producer):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    tag=hashlib.sha256(canonical(ident)).hexdigest()[:20];target=output/tag
    with lock(output/(tag+'.lock')):
        if target.exists(): verify(target,ident);return target,True
        with tempfile.TemporaryDirectory(prefix='.partial-',dir=output) as tmp:
            root=Path(tmp);producer(root)
            artifacts={p.relative_to(root).as_posix():sha256(p) for p in sorted(root.rglob('*')) if p.is_file()}
            if not artifacts: raise ValueError('producer emitted no evidence')
            write_json(root/'manifest.json',dict(schema='cdt-confirmation-stage-v1',complete=True,
                identity=ident,artifacts=artifacts,production_gates_changed=False))
            verify(root,ident);os.rename(root,target)
    return target,False
