#!/usr/bin/env python3
"""Operational state CLI over runlogs.db."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common.event_log import load_events
from common.paths import EVENT_LOG, RUNLOGS_DB
from session_store import open_session_store

REPO_ROOT = Path(__file__).resolve().parent.parent
VIEWS_DIR = REPO_ROOT / ".claude" / "views"
PROMPTS_DIR = REPO_ROOT / ".claude" / "prompts"
VALID_KINDS = {"goal", "finding", "improvement", "incident", "decision"}
VALID_STATUSES = {"proposed", "in_progress", "done", "rejected", "stale"}
VALID_SEVERITIES = {None, "low", "medium", "high"}
VALID_SAFETY_CLASSES = {
    None,
    "docs_config",
    "cache_cleanup",
    "generated_regen",
    "advisory_only",
    "escalate_only",
}


@dataclass
class CanaryResult:
    name: str
    ok: bool
    detail: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def get_db() -> sqlite3.Connection:
    return open_session_store(RUNLOGS_DB)


def render_views(db: sqlite3.Connection) -> dict[str, Path]:
    VIEWS_DIR.mkdir(parents=True, exist_ok=True)

    open_items = db.execute(
        "SELECT item_id, kind, severity, status, title, created_at FROM v_open_items LIMIT 50"
    ).fetchall()
    escalations = db.execute(
        "SELECT item_id, severity, title, created_at FROM v_escalations LIMIT 25"
    ).fetchall()
    recent_sessions = db.execute(
        """
        SELECT vendor_session_id AS uuid, project_slug AS project, started_at AS start_ts, first_message
        FROM sessions
        WHERE vendor = 'claude' AND client = 'claude-code' AND jsonl_path IS NOT NULL
        ORDER BY started_at DESC
        LIMIT 10
        """
    ).fetchall()
    prompt_names = sorted(p.name for p in PROMPTS_DIR.glob("*.md")) if PROMPTS_DIR.exists() else []
    goal_metrics = get_goal_metrics(db)
    canaries = run_canaries(db, persist=False)
    session_rows = db.execute(
        "SELECT COUNT(*) AS c FROM sessions WHERE vendor = 'claude' AND client = 'claude-code' AND jsonl_path IS NOT NULL"
    ).fetchone()["c"]

    board_lines = [
        f"# Board — {datetime.now().date().isoformat()}",
        "",
        "## Goal Snapshot",
    ]
    board_lines.extend(render_goal_snapshot(goal_metrics))

    board_lines.extend([
        "",
        "## Escalations",
    ])
    if escalations:
        for row in escalations:
            board_lines.append(
                f"- [{row['severity'] or 'unspecified'}] {row['title']} ({row['item_id']})"
            )
    else:
        board_lines.append("- none")

    board_lines.extend(["", "## Open Items"])
    if open_items:
        for row in open_items:
            board_lines.append(
                f"- [{row['kind']}] {row['title']} ({row['status']}, {row['item_id']})"
            )
    else:
        board_lines.append("- none")

    board_lines.extend(["", "## Recent Sessions"])
    for row in recent_sessions:
        board_lines.append(
            f"- {row['start_ts'][:10]} {row['project'] or '?'} {row['uuid'][:8]} {truncate(row['first_message'], 80)}"
        )

    board_lines.extend(["", "## Canary Status"])
    for result in canaries:
        prefix = "ok" if result.ok else "fail"
        board_lines.append(f"- {prefix}: {result.name} — {result.detail}")

    board_lines.extend(["", "## Prompt Surface"])
    if prompt_names:
        for name in prompt_names:
            board_lines.append(f"- {name}")
    else:
        board_lines.append("- none")

    improvements = _render_simple_list(
        "# Improvements",
        db.execute(
            "SELECT item_id, title, status FROM items WHERE kind = 'improvement' AND status != 'done' ORDER BY created_at DESC LIMIT 50"
        ).fetchall(),
    )
    incidents = _render_simple_list(
        "# Incidents",
        db.execute(
            "SELECT item_id, title, status FROM items WHERE kind = 'incident' AND status != 'done' ORDER BY created_at DESC LIMIT 50"
        ).fetchall(),
    )
    decisions = _render_simple_list(
        "# Decisions",
        db.execute(
            "SELECT item_id, title, status FROM items WHERE kind = 'decision' ORDER BY created_at DESC LIMIT 50"
        ).fetchall(),
    )
    capabilities_lines = [
        "# Capabilities",
        "",
        f"- prompts: {len(prompt_names)}",
        f"- event_log_present: {'yes' if EVENT_LOG.exists() else 'no'}",
        f"- session_rows: {session_rows}",
        f"- item_rows: {db.execute('SELECT COUNT(*) AS c FROM items').fetchone()['c']}",
        f"- maintenance_rate_30d: {goal_metrics['maintenance_rate']}",
        f"- maintenance_free_streak_days: {goal_metrics['maintenance_free_streak_days']}",
        f"- infra_commit_ratio_week: {goal_metrics['infra_commit_ratio']}",
    ]

    outputs = {
        "board": VIEWS_DIR / "board.md",
        "improvements": VIEWS_DIR / "improvements.md",
        "incidents": VIEWS_DIR / "incidents.md",
        "decisions": VIEWS_DIR / "decisions.md",
        "capabilities": VIEWS_DIR / "capabilities.md",
    }
    outputs["board"].write_text("\n".join(board_lines) + "\n", encoding="utf-8")
    outputs["improvements"].write_text(improvements, encoding="utf-8")
    outputs["incidents"].write_text(incidents, encoding="utf-8")
    outputs["decisions"].write_text(decisions, encoding="utf-8")
    outputs["capabilities"].write_text("\n".join(capabilities_lines) + "\n", encoding="utf-8")
    return outputs


def _render_simple_list(title: str, rows: list[sqlite3.Row]) -> str:
    lines = [title, ""]
    if not rows:
        lines.append("- none")
    else:
        for row in rows:
            lines.append(f"- {row['title']} ({row['status']}, {row['item_id']})")
    return "\n".join(lines) + "\n"


def truncate(text: str | None, limit: int) -> str:
    value = (text or "").replace("\n", " ").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def _validate_choice(name: str, value: str | None, allowed: set[str | None]) -> None:
    if value not in allowed:
        allowed_values = ", ".join(sorted(v for v in allowed if v is not None))
        raise SystemExit(f"Invalid {name}: {value!r}. Allowed: {allowed_values}")


def validate_item_args(args: argparse.Namespace) -> None:
    _validate_choice("kind", getattr(args, "kind", None), VALID_KINDS)
    _validate_choice("status", getattr(args, "status", None), VALID_STATUSES)
    _validate_choice("severity", getattr(args, "severity", None), VALID_SEVERITIES)
    _validate_choice("safety_class", getattr(args, "safety_class", None), VALID_SAFETY_CLASSES)


def get_goal_metrics(db: sqlite3.Connection) -> dict[str, object]:
    rate = db.execute("SELECT * FROM v_maintenance_rate_30d").fetchone()
    streak = db.execute("SELECT * FROM v_maintenance_free_streak").fetchone()
    infra = db.execute(
        "SELECT week, infra_commits, total_commits, infra_commit_ratio FROM v_infra_commit_ratio ORDER BY week DESC LIMIT 1"
    ).fetchone()
    goals = db.execute(
        "SELECT item_id, title, body, status FROM items WHERE kind = 'goal' ORDER BY created_at ASC"
    ).fetchall()
    return {
        "goals": [dict(row) for row in goals],
        "maintenance_sessions": int(rate["maintenance_sessions"] or 0),
        "total_sessions": int(rate["total_sessions"] or 0),
        "maintenance_rate": float(rate["maintenance_rate"] or 0.0),
        "maintenance_free_streak_days": float(streak["streak_days"] or 0.0),
        "last_maintenance_ts": streak["last_maintenance_ts"],
        "infra_week": infra["week"] if infra else None,
        "infra_commits": int(infra["infra_commits"] or 0) if infra else 0,
        "infra_total_commits": int(infra["total_commits"] or 0) if infra else 0,
        "infra_commit_ratio": float(infra["infra_commit_ratio"] or 0.0) if infra else 0.0,
    }


def render_goal_snapshot(metrics: dict[str, object]) -> list[str]:
    lines = [
        (
            f"- maintenance sessions: {metrics['maintenance_sessions']}/{metrics['total_sessions']} "
            f"({metrics['maintenance_rate']:.1%}) over last 30 days"
        ),
        f"- maintenance-free streak: {metrics['maintenance_free_streak_days']:.1f} days",
    ]
    if metrics["infra_week"]:
        lines.append(
            f"- infra commit ratio: {metrics['infra_commit_ratio']:.1%} "
            f"({metrics['infra_commits']}/{metrics['infra_total_commits']}) in week {metrics['infra_week']}"
        )
    else:
        lines.append("- infra commit ratio: no commit data yet")
    goal_rows = metrics["goals"]
    if goal_rows:
        lines.append("- tracked goals:")
        for goal in goal_rows[:5]:
            lines.append(f"  - {goal['title']} ({goal['status']})")
    return lines


def canary_item_id(name: str) -> str:
    return f"incident:canary:{name}"


def upsert_canary_incident(db: sqlite3.Connection, result: CanaryResult) -> None:
    item_id = canary_item_id(result.name)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    existing = db.execute("SELECT status FROM items WHERE item_id = ?", [item_id]).fetchone()
    if result.ok:
        if existing and existing["status"] != "done":
            db.execute(
                """
                UPDATE items
                SET status = 'done',
                    resolution = ?,
                    resolved_at = ?,
                    updated_at = ?
                WHERE item_id = ?
                """,
                (f"Recovered: {result.detail}", now, now, item_id),
            )
            log_item_event(db, item_id, "resolved", existing["status"], "done", result.detail)
        return

    title = f"Canary failed: {result.name}"
    body = result.detail
    if existing is None:
        db.execute(
            """
            INSERT INTO items (
                item_id, kind, status, title, body, severity, safety_class,
                shared_infra, recurrence_count, created_at, updated_at
            )
            VALUES (?, 'incident', 'proposed', ?, ?, 'high', 'escalate_only', 0, 1, ?, ?)
            """,
            (item_id, title, body, now, now),
        )
        log_item_event(db, item_id, "created", None, "proposed", body)
    else:
        db.execute(
            """
            UPDATE items
            SET status = 'proposed',
                body = ?,
                severity = 'high',
                safety_class = 'escalate_only',
                recurrence_count = recurrence_count + 1,
                updated_at = ?
            WHERE item_id = ?
            """,
            (body, now, item_id),
        )
        log_item_event(db, item_id, "escalated", existing["status"], "proposed", body)


def run_canaries(db: sqlite3.Connection, *, persist: bool) -> list[CanaryResult]:
    results = [
        check_board_fresh(),
        check_event_log_recent(),
        check_no_orphaned_item_events(db),
        check_sessions_fts(db),
    ]
    if persist:
        for result in results:
            upsert_canary_incident(db, result)
        db.commit()
    return results


def create_item(db: sqlite3.Connection, args: argparse.Namespace) -> str:
    validate_item_args(args)
    item_id = args.item_id or str(uuid.uuid4())
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    db.execute(
        """
        INSERT INTO items (
            item_id, kind, status, title, body, severity, safety_class,
            shared_infra, source_run_id, source_session_pk, recurrence_count,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            args.kind,
            args.status,
            args.title,
            args.body,
            args.severity,
            args.safety_class,
            1 if args.shared_infra else 0,
            args.source_run_id,
            args.source_session_pk,
            args.recurrence_count,
            now,
            now,
        ),
    )
    log_item_event(db, item_id, "created", None, args.status, args.note)
    db.commit()
    return item_id


def update_item(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    row = db.execute("SELECT * FROM items WHERE item_id = ?", [args.item_id]).fetchone()
    if row is None:
        raise SystemExit(f"Unknown item: {args.item_id}")
    validate_item_args(args)
    updates: dict[str, object] = {}
    for field in ("status", "title", "body", "severity", "safety_class", "resolution", "resolution_commit"):
        value = getattr(args, field, None)
        if value is not None:
            updates[field] = value
    if args.shared_infra is not None:
        updates["shared_infra"] = 1 if args.shared_infra else 0
    if not updates:
        return
    updates["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    assignments = ", ".join(f"{key} = ?" for key in updates)
    db.execute(
        f"UPDATE items SET {assignments} WHERE item_id = ?",
        [*updates.values(), args.item_id],
    )
    if "status" in updates:
        log_item_event(db, args.item_id, "status_change", row["status"], str(updates["status"]), args.note)
    db.commit()


def log_item_event(
    db: sqlite3.Connection,
    item_id: str,
    event_type: str,
    old_value: str | None,
    new_value: str | None,
    note: str | None,
) -> None:
    db.execute(
        """
        INSERT INTO item_events (item_id, event_type, old_value, new_value, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (item_id, event_type, old_value, new_value, note),
    )


def cmd_item_list(args: argparse.Namespace) -> int:
    db = get_db()
    clauses = []
    params: list[object] = []
    if args.kind:
        clauses.append("kind = ?")
        params.append(args.kind)
    if args.status:
        clauses.append("status = ?")
        params.append(args.status)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    rows = db.execute(
        f"SELECT item_id, kind, status, severity, title FROM items {where} ORDER BY created_at DESC",
        params,
    ).fetchall()
    print(json.dumps([dict(row) for row in rows], indent=2))
    return 0


def cmd_item_create(args: argparse.Namespace) -> int:
    db = get_db()
    item_id = create_item(db, args)
    print(item_id)
    return 0


def cmd_item_update(args: argparse.Namespace) -> int:
    db = get_db()
    update_item(db, args)
    print(args.item_id)
    return 0


def cmd_item_resolve(args: argparse.Namespace) -> int:
    db = get_db()
    current = db.execute("SELECT status FROM items WHERE item_id = ?", [args.item_id]).fetchone()
    if current is None:
        raise SystemExit(f"Unknown item: {args.item_id}")
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    db.execute(
        """
        UPDATE items
        SET status = 'done',
            resolution = ?,
            resolution_commit = ?,
            resolved_at = ?,
            updated_at = ?
        WHERE item_id = ?
        """,
        (args.resolution, args.commit, now, now, args.item_id),
    )
    log_item_event(db, args.item_id, "resolved", current["status"], "done", args.resolution)
    db.commit()
    print(args.item_id)
    return 0


def cmd_item_escalate(args: argparse.Namespace) -> int:
    db = get_db()
    current = db.execute("SELECT status FROM items WHERE item_id = ?", [args.item_id]).fetchone()
    if current is None:
        raise SystemExit(f"Unknown item: {args.item_id}")
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    db.execute(
        "UPDATE items SET status = 'proposed', updated_at = ? WHERE item_id = ?",
        (now, args.item_id),
    )
    log_item_event(db, args.item_id, "escalated", current["status"], "proposed", args.note)
    db.commit()
    print(args.item_id)
    return 0


def cmd_view_render(args: argparse.Namespace) -> int:
    db = get_db()
    outputs = render_views(db)
    for path in outputs.values():
        print(path)
    return 0


def cmd_view_board(args: argparse.Namespace) -> int:
    board = VIEWS_DIR / "board.md"
    if not board.exists():
        db = get_db()
        render_views(db)
    print(board.read_text(encoding="utf-8"))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    db = get_db()
    session_count = db.execute(
        "SELECT COUNT(*) AS c FROM sessions WHERE vendor = 'claude' AND client = 'claude-code' AND jsonl_path IS NOT NULL"
    ).fetchone()["c"]
    item_count = db.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
    prompts = sorted(p.name for p in PROMPTS_DIR.glob("*.md")) if PROMPTS_DIR.exists() else []
    report = {
        "runlogs_db": str(RUNLOGS_DB),
        "runlogs_exists": RUNLOGS_DB.exists(),
        "session_rows": session_count,
        "item_rows": item_count,
        "event_log_exists": EVENT_LOG.exists(),
        "views_dir": str(VIEWS_DIR),
        "views_exist": sorted(p.name for p in VIEWS_DIR.glob("*.md")) if VIEWS_DIR.exists() else [],
        "prompts": prompts,
    }
    print(json.dumps(report, indent=2))
    return 0


def cmd_canary_run(args: argparse.Namespace) -> int:
    db = get_db()
    results = run_canaries(db, persist=True)
    for result in results:
        prefix = "OK" if result.ok else "FAIL"
        print(f"{prefix} {result.name}: {result.detail}")
    return 0 if all(result.ok for result in results) else 1


def check_board_fresh() -> CanaryResult:
    board = VIEWS_DIR / "board.md"
    if not board.exists():
        return CanaryResult("board-view", False, "missing")
    age = datetime.now() - datetime.fromtimestamp(board.stat().st_mtime)
    if age <= timedelta(hours=26):
        return CanaryResult("board-view", True, f"{int(age.total_seconds() // 60)}m old")
    return CanaryResult("board-view", False, f"{int(age.total_seconds() // 3600)}h old")


def check_event_log_recent() -> CanaryResult:
    events = load_events(since=(datetime.now(timezone.utc) - timedelta(hours=24)).isoformat())
    if events:
        return CanaryResult("event-log", True, f"{len(events)} entries in 24h")
    if EVENT_LOG.exists():
        return CanaryResult("event-log", False, "no recent entries")
    return CanaryResult("event-log", False, "missing")


def check_no_orphaned_item_events(db: sqlite3.Connection) -> CanaryResult:
    count = db.execute(
        "SELECT COUNT(*) AS c FROM item_events WHERE item_id NOT IN (SELECT item_id FROM items)"
    ).fetchone()["c"]
    return CanaryResult("item-events", count == 0, f"{count} orphaned")


def check_sessions_fts(db: sqlite3.Connection) -> CanaryResult:
    try:
        count = db.execute(
            "SELECT COUNT(*) AS c FROM sessions_fts WHERE sessions_fts MATCH 'hook'"
        ).fetchone()["c"]
        return CanaryResult("sessions-fts", True, f"query ok ({count} matches)")
    except sqlite3.OperationalError as exc:
        return CanaryResult("sessions-fts", False, str(exc))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operational state CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    item = sub.add_parser("item", help="Item lifecycle commands")
    item_sub = item.add_subparsers(dest="item_command", required=True)

    item_list = item_sub.add_parser("list")
    item_list.add_argument("--kind")
    item_list.add_argument("--status")
    item_list.set_defaults(func=cmd_item_list)

    item_create = item_sub.add_parser("create")
    item_create.add_argument("--item-id")
    item_create.add_argument("--kind", required=True)
    item_create.add_argument("--status", default="proposed")
    item_create.add_argument("--title", required=True)
    item_create.add_argument("--body")
    item_create.add_argument("--severity")
    item_create.add_argument("--safety-class")
    item_create.add_argument("--shared-infra", action="store_true")
    item_create.add_argument("--source-run-id")
    item_create.add_argument("--source-session-pk", type=int)
    item_create.add_argument("--recurrence-count", type=int, default=1)
    item_create.add_argument("--note")
    item_create.set_defaults(func=cmd_item_create)

    item_update = item_sub.add_parser("update")
    item_update.add_argument("item_id")
    item_update.add_argument("--status")
    item_update.add_argument("--title")
    item_update.add_argument("--body")
    item_update.add_argument("--severity")
    item_update.add_argument("--safety-class")
    item_update.add_argument("--shared-infra", type=lambda value: value.lower() == "true")
    item_update.add_argument("--resolution")
    item_update.add_argument("--resolution-commit")
    item_update.add_argument("--note")
    item_update.set_defaults(func=cmd_item_update)

    item_resolve = item_sub.add_parser("resolve")
    item_resolve.add_argument("item_id")
    item_resolve.add_argument("--resolution", required=True)
    item_resolve.add_argument("--commit")
    item_resolve.set_defaults(func=cmd_item_resolve)

    item_escalate = item_sub.add_parser("escalate")
    item_escalate.add_argument("item_id")
    item_escalate.add_argument("--note")
    item_escalate.set_defaults(func=cmd_item_escalate)

    view = sub.add_parser("view", help="Render or print views")
    view_sub = view.add_subparsers(dest="view_command", required=True)
    view_render = view_sub.add_parser("render")
    view_render.set_defaults(func=cmd_view_render)
    view_board = view_sub.add_parser("board")
    view_board.set_defaults(func=cmd_view_board)

    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)

    canary = sub.add_parser("canary")
    canary_sub = canary.add_subparsers(dest="canary_command", required=True)
    canary_run = canary_sub.add_parser("run")
    canary_run.set_defaults(func=cmd_canary_run)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
