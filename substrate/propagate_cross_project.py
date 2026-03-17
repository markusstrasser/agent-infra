#!/usr/bin/env python3
"""Cross-project staleness propagation.

Reads change logs from all project DBs. When an object is marked stale in one
project and has cross_project_refs pointing to it from another project, marks
the referencing objects stale in the target project's DB.

Usage:
    uv run python3 substrate/propagate_cross_project.py [--dry-run]

Designed to run via orchestrator tick or cron. Idempotent — safe to run
repeatedly. Tracks last-processed changelog ID per project in a state file.
"""

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_DIR = Path.home() / ".claude" / "knowledge"
STATE_FILE = DB_DIR / "propagation_state.json"
PROJECTS = ["intel", "selve", "genomics"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_db(project: str) -> sqlite3.Connection | None:
    path = DB_DIR / f"{project}.db"
    if not path.exists():
        return None
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def get_stale_changes(conn: sqlite3.Connection, since_id: int) -> list[dict]:
    """Get changelog entries for objects marked stale since a given ID."""
    rows = conn.execute(
        """SELECT id, object_id, object_type, timestamp, reason
           FROM changelog
           WHERE id > ? AND action = 'status_changed'
           AND new_value LIKE '%stale%'
           ORDER BY id""",
        (since_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def find_cross_refs(conn: sqlite3.Connection, remote_project: str,
                    remote_id: str) -> list[dict]:
    """Find local objects that reference a remote object."""
    rows = conn.execute(
        """SELECT local_id, local_type, relation
           FROM cross_project_refs
           WHERE remote_project = ? AND remote_id = ?""",
        (remote_project, remote_id),
    ).fetchall()
    return [dict(r) for r in rows]


def mark_stale_in_db(conn: sqlite3.Connection, object_id: str,
                     object_type: str, reason: str) -> bool:
    """Mark an object stale in a DB. Returns True if status actually changed."""
    table = {"assertion": "assertions", "evidence": "evidence", "artifact": "artifacts"}
    t = table.get(object_type)
    if not t:
        return False

    old = conn.execute(
        f"SELECT status FROM {t} WHERE id = ?", (object_id,)
    ).fetchone()
    if not old or old["status"] == "stale":
        return False

    now = _now()
    conn.execute(
        f"UPDATE {t} SET status = 'stale', updated_at = ? WHERE id = ?",
        (now, object_id),
    )
    conn.execute(
        """INSERT INTO changelog (object_id, object_type, action, old_value,
           new_value, reason, timestamp)
           VALUES (?, ?, 'status_changed', ?, ?, ?, ?)""",
        (object_id, object_type,
         json.dumps({"status": old["status"]}),
         json.dumps({"status": "stale"}),
         reason, now),
    )
    conn.commit()
    return True


def propagate(dry_run: bool = False) -> list[str]:
    """Run cross-project propagation. Returns log of actions taken."""
    state = load_state()
    actions = []

    for source_project in PROJECTS:
        source_conn = get_db(source_project)
        if not source_conn:
            continue

        last_id = state.get(f"{source_project}_last_changelog_id", 0)
        changes = get_stale_changes(source_conn, last_id)

        if not changes:
            source_conn.close()
            continue

        max_id = max(c["id"] for c in changes)

        for change in changes:
            # Check all other projects for cross-refs pointing to this object
            for target_project in PROJECTS:
                if target_project == source_project:
                    continue
                target_conn = get_db(target_project)
                if not target_conn:
                    continue

                refs = find_cross_refs(target_conn, source_project,
                                       change["object_id"])
                for ref in refs:
                    reason = (f"Cross-project propagation: {source_project}:"
                              f"{change['object_id']} marked stale"
                              f" ({change.get('reason', 'no reason')})")
                    if dry_run:
                        actions.append(
                            f"  [DRY RUN] Would mark {target_project}:{ref['local_id']} "
                            f"stale (depends on {source_project}:{change['object_id']})"
                        )
                    else:
                        changed = mark_stale_in_db(target_conn, ref["local_id"],
                                                   ref["local_type"], reason)
                        if changed:
                            actions.append(
                                f"  Marked {target_project}:{ref['local_id']} stale "
                                f"(depends on {source_project}:{change['object_id']})"
                            )

                target_conn.close()

        if not dry_run:
            state[f"{source_project}_last_changelog_id"] = max_id

        source_conn.close()

    if not dry_run:
        save_state(state)

    return actions


def main():
    parser = argparse.ArgumentParser(
        description="Cross-project staleness propagation"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be propagated without changing anything")
    args = parser.parse_args()

    print(f"Cross-project propagation ({'dry run' if args.dry_run else 'live'}):")
    print(f"  Projects: {', '.join(PROJECTS)}")
    print(f"  DB dir: {DB_DIR}")
    print()

    actions = propagate(dry_run=args.dry_run)

    if actions:
        for a in actions:
            print(a)
        print(f"\n{len(actions)} propagation(s).")
    else:
        print("  No cross-project propagations needed.")


if __name__ == "__main__":
    main()
