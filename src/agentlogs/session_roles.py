"""Backfill sessions.session_role over previously indexed sessions (migration 011).

Each vendor's rule is the adapter's own function, so ingest and backfill cannot
disagree:
  claude  entrypoint stamps in the main transcript (on disk, or in an archive copy)
  codex   session_meta source/originator, kept in run_configs.metadata_json
  cursor  whether the CLI chat store exists beside the recorded transcript path
Only NULL rows are touched. A row whose evidence is gone stays NULL (undetermined):
consumers that want the operator's sessions filter session_role = 'operator', so an
unknown origin is left out rather than guessed.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .adapters import claude, codex, cursor
from .paths import PROJECTS_DIR


@dataclass
class RolePlan:
    roles: Counter = field(default_factory=Counter)  # (vendor, role) -> sessions
    undetermined: Counter = field(default_factory=Counter)  # (vendor, reason) -> sessions


def _claude_transcript(recorded: str | None, archive_root: Path | None) -> Path | None:
    if not recorded:
        return None
    path = Path(recorded)
    if path.exists():
        return path
    if archive_root is None:
        return None
    try:
        copy = archive_root / "claude" / path.relative_to(PROJECTS_DIR)
    except ValueError:
        return None
    return copy if copy.exists() else None


Run = tuple[str | None, str | None, str | None]  # (source path, metadata_json, transport)


def _role(vendor: str, vendor_session_id: str, runs: dict[str, Run],
          archive_root: Path | None) -> tuple[str | None, str]:
    """(role, reason-if-None) for one session; runs maps run_id -> Run."""
    if vendor == "claude":
        main = runs.get(f"claude:{vendor_session_id}")
        if main is None:
            return None, "main transcript not indexed"
        path = _claude_transcript(main[0], archive_root)
        if path is None:
            return None, "transcript gone"
        role = claude.session_role(path, vendor_session_id, claude.load_entrypoints(path))
        return role, "no entrypoint stamp"
    if vendor == "codex":
        main = runs.get(f"codex:{vendor_session_id}")
        meta = json.loads(main[1]) if main and main[1] else {}
        # runs.transport is the same stamp flattened at import; older rows lack the raw one
        source = meta["session_source"] if "session_source" in meta else (main[2] if main else None)
        role = codex.session_role(source, meta.get("originator"))
        return role, "no source stamp"
    if vendor == "cursor":
        recorded = next((path for path, _, _ in runs.values() if path), None)
        if recorded is None:
            return None, "transcript path unknown"
        return cursor.session_role(Path(recorded), vendor_session_id), ""
    return None, "vendor records no origin"


def _decide(db: sqlite3.Connection, archive_root: Path | None) -> tuple[list[tuple[str, int]], RolePlan]:
    sessions: dict[int, tuple[str, str]] = {}
    runs: dict[int, dict[str, Run]] = {}
    for pk, vendor, vsid, run_id, path, meta, transport in db.execute(
        """
        SELECT s.session_pk, s.vendor, s.vendor_session_id, r.run_id, src.path, rc.metadata_json,
               r.transport
        FROM sessions s
        LEFT JOIN runs r ON r.session_pk = s.session_pk
        LEFT JOIN sources src ON src.source_id = r.primary_source_id
        LEFT JOIN run_configs rc ON rc.run_id = r.run_id
        WHERE s.session_role IS NULL
        """
    ):
        sessions[pk] = (vendor, vsid or "")
        if run_id is not None:
            runs.setdefault(pk, {})[run_id] = (path, meta, transport)
    plan = RolePlan()
    updates: list[tuple[str, int]] = []
    for pk, (vendor, vsid) in sessions.items():
        role, reason = _role(vendor, vsid, runs.get(pk, {}), archive_root)
        if role is None:
            plan.undetermined[(vendor, reason)] += 1
            continue
        plan.roles[(vendor, role)] += 1
        updates.append((role, pk))
    return updates, plan


def plan_roles(db: sqlite3.Connection, archive_root: Path | None = None) -> RolePlan:
    return _decide(db, archive_root)[1]


def apply_roles(db: sqlite3.Connection, archive_root: Path | None = None) -> RolePlan:
    updates, plan = _decide(db, archive_root)
    if not updates:
        return plan
    db.execute("BEGIN IMMEDIATE")
    try:
        db.executemany(
            "UPDATE sessions SET session_role = ? WHERE session_pk = ? AND session_role IS NULL",
            updates,
        )
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    return plan
