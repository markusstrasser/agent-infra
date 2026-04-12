"""Append-only JSONL event ledger with content-hash dedup.

The ledger is a JSONL file at a caller-provided path. Each line is a
serialized VerificationEvent. Dedup by event_id — appending the same
semantic event twice is a no-op.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from claim_bench.types import VerificationEvent


class LedgerReader:
    """Read-only view of an event ledger."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def read_events(
        self,
        claim_id: str | None = None,
        since: datetime | None = None,
    ) -> list[VerificationEvent]:
        """Read events, optionally filtered by claim_id and/or since timestamp."""
        if not self._path.exists():
            return []
        events: list[VerificationEvent] = []
        for line in self._path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            evt = VerificationEvent.from_dict(json.loads(line))
            if claim_id is not None and evt.claim_id != claim_id:
                continue
            if since is not None and evt.observed_at < since:
                continue
            events.append(evt)
        return events

    def event_exists(self, event_id: str) -> bool:
        """Check whether an event with this ID already exists."""
        if not self._path.exists():
            return False
        for line in self._path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("event_id") == event_id:
                return True
        return False

    def all_event_ids(self) -> set[str]:
        """Return all event IDs in the ledger."""
        if not self._path.exists():
            return set()
        ids: set[str] = set()
        for line in self._path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if "event_id" in d:
                ids.add(d["event_id"])
        return ids


class Ledger(LedgerReader):
    """Read-write event ledger with append-only semantics."""

    def append_event(self, event: VerificationEvent) -> bool:
        """Append an event to the ledger. Returns True if appended, False if dedup'd."""
        if self.event_exists(event.event_id):
            return False
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a") as f:
            f.write(json.dumps(event.to_dict(), separators=(",", ":"), default=str) + "\n")
        return True
