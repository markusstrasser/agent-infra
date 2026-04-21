"""Single-writer lock for agentlogs index runs.

The launchd indexer and any manual `agentlogs index` invocation share one
database. SQLite WAL handles concurrent readers, but prolonged writer
contention (BEGIN IMMEDIATE) surfaces as random operational errors. An
fcntl.flock on a sidecar lock file is the cleanest serialization: second
writer blocks for up to `timeout_s` and then exits cleanly, rather than
racing and failing mid-transaction.
"""

from __future__ import annotations

import contextlib
import errno
import fcntl
import os
import time
from pathlib import Path


class IndexerLockBusy(RuntimeError):
    """Another indexer holds the lock and we timed out waiting."""


@contextlib.contextmanager
def indexer_lock(lock_path: Path, timeout_s: float = 30.0):
    """Acquire an exclusive fcntl.flock on `lock_path`.

    Blocks up to `timeout_s` seconds. Raises IndexerLockBusy if another
    process still holds it. The lock is released on context exit (even on
    exception) and the file descriptor is closed.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if exc.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                    raise
                if time.monotonic() >= deadline:
                    raise IndexerLockBusy(
                        f"indexer lock {lock_path} held by another process"
                    ) from None
                time.sleep(0.5)
        os.write(fd, f"{os.getpid()}\n".encode())
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
