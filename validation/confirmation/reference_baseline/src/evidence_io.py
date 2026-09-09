"""Small immutable-artifact helpers shared by continuation workflows."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
import numpy as np


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()


def atomic_npz(path,**arrays):
    """Publish a complete NPZ without overwriting an existing result."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.'+path.name+'.',delete=False) as f:
            temp=Path(f.name)
            np.savez_compressed(f,**arrays)
            f.flush();os.fsync(f.fileno())
        os.link(temp,path)  # atomic create-only publication; no accidental replace
    finally:
        if temp is not None:temp.unlink(missing_ok=True)


def source_hashes(root,paths):
    root=Path(root).resolve()
    result={}
    for path in paths:
        path=Path(path).resolve()
        if not path.is_relative_to(root):raise ValueError('source outside project')
        result[str(path.relative_to(root))]=sha256(path)
    return result


def verify_bundle(directory,*,expected_contract=None,source_root=None):
    directory=Path(directory).resolve()
    manifest=json.loads((directory/'manifest.json').read_text())
    if expected_contract is not None and manifest['contract']!=expected_contract:
        raise RuntimeError('existing bundle contract differs')
    for name,digest in manifest['artifacts'].items():
        p=(directory/name).resolve()
        if not p.is_relative_to(directory) or not p.is_file() or sha256(p)!=digest:
            raise RuntimeError(f'artifact verification failed: {name}')
    if source_root is not None:
        root=Path(source_root).resolve()
        for name,digest in manifest['contract']['sources'].items():
            p=(root/name).resolve()
            if not p.is_relative_to(root) or not p.is_file() or sha256(p)!=digest:
                raise RuntimeError(f'source verification failed: {name}')
    return manifest
