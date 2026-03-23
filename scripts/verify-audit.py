#!/usr/bin/env python3
"""Audit Haiku orchestrator verification accuracy against human judgment.

Pulls recent verified tasks from orchestrator.db and displays task prompt,
output summary, and Haiku verdict for manual review.

Usage:
    uv run python scripts/verify-audit.py                # show last 20 verified tasks
    uv run python scripts/verify-audit.py --limit 50     # show more
    uv run python scripts/verify-audit.py --export        # export to JSON for batch review
"""

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".claude" / "orchestrator.db"
AUDIT_OUTPUT = Path(__file__).resolve().parent.parent / "artifacts" / "verify-audit"


def get_verified_tasks(limit: int = 20) -> list[dict]:
    """Pull tasks with verification results from orchestrator.db."""
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return []

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT t.id, t.pipeline, t.step, t.prompt, t.status, t.output,
               e.data as event_data, e.timestamp as verify_time
        FROM tasks t
        JOIN events e ON e.task_id = t.id
        WHERE e.action = 'verify'
        ORDER BY e.timestamp DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    tasks = []
    for row in rows:
        event_data = json.loads(row["event_data"]) if row["event_data"] else {}
        tasks.append({
            "id": row["id"],
            "pipeline": row["pipeline"],
            "step": row["step"],
            "prompt": (row["prompt"] or "")[:500],
            "output": (row["output"] or "")[:500],
            "status": row["status"],
            "haiku_pass": event_data.get("pass"),
            "haiku_reasoning": event_data.get("reasoning", ""),
            "verify_time": row["verify_time"],
        })
    return tasks


def display_tasks(tasks: list[dict]) -> None:
    """Display tasks for manual review."""
    if not tasks:
        print("No verified tasks found.")
        return

    print(f"{'=' * 70}")
    print(f"  HAIKU VERIFICATION AUDIT — {len(tasks)} tasks")
    print(f"{'=' * 70}")

    for i, t in enumerate(tasks, 1):
        verdict = "PASS" if t["haiku_pass"] else "FAIL"
        print(f"\n--- Task {i}/{len(tasks)} [{t['id'][:8]}] ---")
        print(f"  Pipeline: {t['pipeline']} / {t['step']}")
        print(f"  Status:   {t['status']}")
        print(f"  Haiku:    {verdict} — {t['haiku_reasoning']}")
        print(f"  Prompt:   {t['prompt'][:200]}...")
        print(f"  Output:   {t['output'][:200]}...")

    # Summary
    passes = sum(1 for t in tasks if t["haiku_pass"])
    fails = len(tasks) - passes
    print(f"\n{'=' * 70}")
    print(f"  Summary: {passes} PASS, {fails} FAIL out of {len(tasks)} verified tasks")
    print(f"  Next: manually rate each task to compute agreement.")
    print(f"  Export with --export, then edit the JSON to add 'human_pass' field.")


def export_for_review(tasks: list[dict]) -> None:
    """Export tasks to JSON for batch review."""
    AUDIT_OUTPUT.mkdir(parents=True, exist_ok=True)
    out_file = AUDIT_OUTPUT / "verify-audit-batch.json"

    for t in tasks:
        t["human_pass"] = None  # To be filled in manually
        t["human_note"] = ""

    with open(out_file, "w") as f:
        json.dump(tasks, f, indent=2)
    print(f"Exported {len(tasks)} tasks to {out_file}")
    print("Edit the file: set 'human_pass' to true/false for each task, then run --score")


def score_audit(audit_file: Path) -> None:
    """Score a completed audit file."""
    with open(audit_file) as f:
        tasks = json.load(f)

    rated = [t for t in tasks if t.get("human_pass") is not None]
    if not rated:
        print("No tasks have been human-rated yet. Set 'human_pass' in the JSON.")
        return

    agree = sum(1 for t in rated if t["haiku_pass"] == t["human_pass"])
    false_pos = sum(1 for t in rated if t["haiku_pass"] and not t["human_pass"])
    false_neg = sum(1 for t in rated if not t["haiku_pass"] and t["human_pass"])

    print(f"{'=' * 50}")
    print(f"  VERIFICATION AUDIT SCORE")
    print(f"{'=' * 50}")
    print(f"  Rated:          {len(rated)}")
    print(f"  Agreement:      {agree}/{len(rated)} ({agree/len(rated):.0%})")
    print(f"  False positive: {false_pos} (Haiku passed, human failed)")
    print(f"  False negative: {false_neg} (Haiku failed, human passed)")


def main() -> int:
    args = sys.argv[1:]
    limit = 20

    if "--limit" in args:
        idx = args.index("--limit")
        if idx + 1 < len(args):
            limit = int(args[idx + 1])

    if "--score" in args:
        audit_file = AUDIT_OUTPUT / "verify-audit-batch.json"
        if not audit_file.exists():
            print(f"No audit file at {audit_file}. Run --export first.")
            return 1
        score_audit(audit_file)
        return 0

    tasks = get_verified_tasks(limit=limit)

    if "--export" in args:
        export_for_review(tasks)
    else:
        display_tasks(tasks)

    return 0


if __name__ == "__main__":
    sys.exit(main())
