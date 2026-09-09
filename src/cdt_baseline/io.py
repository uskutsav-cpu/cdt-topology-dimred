"""Strict provenance and process-safe storage for Linux/macOS."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import fcntl
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone


def sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def blob_sha(path: Path | str) -> str:
    data = Path(path).read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path | str):
    def reject(value):
        raise ValueError(f'non-finite JSON value: {value}')
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError(f'duplicate JSON key: {k}')
            out[k] = v
        return out
    return json.loads(Path(path).read_text(), parse_constant=reject, object_pairs_hook=unique)


def atomic_bytes(path: Path | str, data: bytes):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('refusing symlink output')
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        # Persist the directory entry where the filesystem supports this operation.
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def atomic_json(path: Path | str, value: object):
    atomic_bytes(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b'\n')


def immutable_json(path: Path | str, value: object):
    path = Path(path)
    if path.exists():
        if load_json(path) != value:
            raise ValueError(f'immutable record differs: {path}')
        return
    atomic_json(path, value)


def inside(root: Path | str, relative: str, *, require_file=True) -> Path:
    root = Path(root).resolve()
    raw = Path(relative)
    if raw.is_absolute() or '..' in raw.parts:
        raise ValueError('path must be relative and confined to its root')
    path = root / raw
    current = root
    for part in raw.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'symlink forbidden in evidence path: {relative}')
    if not path.resolve().is_relative_to(root):
        raise ValueError('path escaped root')
    if require_file and not path.is_file():
        raise FileNotFoundError(path)
    return path


@contextmanager
def lock(path: Path | str):
    """Never unlink lock inodes. Pass the yielded FD to children to lock orphans too."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f'already locked: {path}') from exc
        yield fd
    finally:
        # close rather than LOCK_UN: a surviving child may share this description.
        os.close(fd)


def inventory(root: Path, *, exclude=()) -> dict[str, str]:
    return {str(p.relative_to(root)): sha256(p) for p in sorted(root.rglob('*'))
            if p.is_file() and p.name not in exclude and not p.name.endswith('.lock')}


def verify_inventory(root: Path, entries: dict[str, str]):
    if not entries:
        raise ValueError('empty evidence inventory')
    for relative, expected in entries.items():
        path = inside(root, relative)
        if sha256(path) != expected:
            raise ValueError(f'evidence hash mismatch: {relative}')
