"""Operational event-log helpers."""

from __future__ import annotations

import json
from pathlib import Path

from .paths import EVENT_LOG


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, default=str, separators=(",", ":")) + "\n")


def append_event(row: dict) -> None:
    append_jsonl(EVENT_LOG, row)

def load_events(*, since: str | None = None) -> list[dict]:
    return _load_path(EVENT_LOG, since=since)


def _load_path(path: Path, *, since: str | None = None) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since and row.get("ts", "") < since:
                continue
            rows.append(row)
    return rows
