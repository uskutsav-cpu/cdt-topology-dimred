"""POSIX single-writer locks and atomic metadata replacement (macOS/Linux)."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import socket
import tempfile


class JobLockedError(RuntimeError):
    pass


@contextmanager
def job_lock(path, *, metadata=None):
    """Fail immediately on a competing writer. Never unlink the lock inode.

    The OS releases the advisory lock after a crash. A stale metadata PID is
    informational, not grounds to bypass a held lock. All writers must opt in.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.seek(0)
            raise JobLockedError(f'job already has a writer: {path}; {handle.read()}') from exc
        try:
            record = {**(metadata or {}), 'pid': os.getpid(), 'host': socket.gethostname(),
                      'acquired_at': datetime.now(timezone.utc).isoformat()}
            handle.seek(0)
            handle.truncate()
            json.dump(record, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
            yield record
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_json(path, record):
    """Replace complete JSON atomically in the same directory; reject NaN/Inf."""
    text = json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + '\n'
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name + '.', delete=False) as handle:
            tmp = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
