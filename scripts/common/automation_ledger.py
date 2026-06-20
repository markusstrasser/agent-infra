"""Automation-write ledger — the missing writer-class in Stop-hook attribution.

`stop-uncommitted-warn.sh` attributes uncommitted files by reading per-session
Edit/Write ledgers (own + peer). Files written by LOCAL AUTOMATION (launchd jobs,
fm.py, digest/sensor generators) go through neither the Edit/Write tool nor a
session ledger, so they fall through to "unattributable → most likely YOURS"
(2026-06-20: agent-failure-modes.md + a sensor digest both mis-flagged on an
interactive session that never touched them).

This is the symmetric fix: a generator calls `register(path)` when it writes a
tracked file; the Stop hook reads a recent window of this shared ledger and
excludes those paths from session attribution. "Tools document themselves"
(epistemic principle 7) — self-maintaining, no manifest to drift.

Append-only JSONL at ~/.claude/automation-write-ledger.jsonl, one record per
write: {"path": <abs>, "writer": <name>, "ts": <epoch float>}. The hook honors a
recency window so a one-time automation write doesn't permanently shadow a path a
human later edits by hand.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

LEDGER = Path.home() / ".claude" / "automation-write-ledger.jsonl"


def register(path: str | Path, writer: str = "automation") -> None:
    """Record that automation `writer` wrote `path`. Best-effort; never raises
    (a ledger write must never break the generator that calls it)."""
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        rec = {"path": str(Path(path).resolve()), "writer": writer, "ts": time.time()}
        with open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        pass
