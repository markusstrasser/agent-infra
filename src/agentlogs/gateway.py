"""Single write-gateway for agentlogs.db mutations.

All INSERT/UPDATE/DELETE paths should route through `write_gateway` so the
fcntl single-writer lock is structural, not per-caller habit.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from .db import DEFAULT_DB_PATH, connect
from .locks import IndexerLockBusy, indexer_lock
from .paths import AGENTLOGS_LOCK


@contextlib.contextmanager
def write_gateway(
    db_path: Path | str | None = None,
    *,
    timeout_s: float = 30.0,
    no_lock: bool = False,
):
    """Yield a connected DB inside the exclusive indexer lock (unless no_lock)."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH

    @contextlib.contextmanager
    def _connected():
        db = connect(path)
        try:
            yield db
        finally:
            db.close()

    if no_lock:
        with _connected() as db:
            yield db
        return

    with indexer_lock(AGENTLOGS_LOCK, timeout_s=timeout_s):
        with _connected() as db:
            yield db


__all__ = ["write_gateway", "IndexerLockBusy"]
