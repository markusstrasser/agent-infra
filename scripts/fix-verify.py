#!/usr/bin/env python3
"""Fix verification — closed-loop validation for improvement-log fixes.

Each finding in the findings DB can have a detection_query — a sessions.py
search pattern that would detect the same failure mode. This script runs
all detection queries against recent sessions and reports which fixes are
holding and which are recurring.

Usage:
    fix-verify.py run [--days N]       # Run all detection queries
    fix-verify.py tag <id> <query>     # Attach a detection query to a finding
    fix-verify.py report [--days N]    # Report fix effectiveness
"""

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import log_metric

FINDINGS_DB = Path.home() / ".claude" / "findings.db"
SESSIONS_DB = Path.home() / ".claude" / "sessions.db"
SESSIONS_SCRIPT = Path.home() / "Projects" / "meta" / "scripts" / "sessions.py"

# Built-in detection queries for common categories.
# These search session content_text in the sessions FTS index.
DEFAULT_QUERIES = {
    "TOKEN WASTE": [
        "redundant read same file",
        "git log overlapping",
        "retry same command",
    ],
    "SYCOPHANCY": [
        "sycophantic compliance",
        "folding under pushback",
    ],
    "BUILD-THEN-UNDO": [
        "revert delete undo wrote",
    ],
    "OVER-ENGINEERING": [
        "abstraction framework config",
    ],
    "RULE VIOLATION": [
        "pre-frontier presented current",
    ],
}


def get_findings_db() -> sqlite3.Connection:
    if not FINDINGS_DB.exists():
        print("Findings DB not found. Run: uv run python3 scripts/finding-triage.py ingest",
              file=sys.stderr)
        sys.exit(1)
    db = sqlite3.connect(str(FINDINGS_DB))
    db.row_factory = sqlite3.Row
    return db


def get_sessions_db() -> sqlite3.Connection:
    if not SESSIONS_DB.exists():
        print("Sessions DB not found. Run: uv run python3 scripts/sessions.py index",
              file=sys.stderr)
        sys.exit(1)
    db = sqlite3.connect(str(SESSIONS_DB))
    db.row_factory = sqlite3.Row
    return db


def run_detection_query(sessions_db: sqlite3.Connection, query: str, since: str) -> list[dict]:
    """Run a detection query against recent sessions via FTS5."""
    try:
        rows = sessions_db.execute(
            """
            SELECT s.uuid, s.project, s.start_ts, s.first_message
            FROM sessions_fts f
            JOIN sessions s ON s.rowid = f.rowid
            WHERE sessions_fts MATCH ? AND s.start_ts >= ?
            ORDER BY s.start_ts DESC
            LIMIT 20
            """,
            [query, since],
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []


def cmd_run(args):
    """Run all detection queries against recent sessions."""
    findings_db = get_findings_db()
    sessions_db = get_sessions_db()
    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    # Get findings with detection queries
    tagged = findings_db.execute(
        """SELECT id, fingerprint, category, summary, detection_query, status
           FROM findings WHERE detection_query IS NOT NULL"""
    ).fetchall()

    # Also run default queries for promoted findings without custom queries
    promoted_no_query = findings_db.execute(
        """SELECT id, fingerprint, category, summary, status
           FROM findings WHERE status = 'promoted' AND detection_query IS NULL"""
    ).fetchall()

    results = []

    # Run custom detection queries
    for f in tagged:
        matches = run_detection_query(sessions_db, f["detection_query"], since)
        results.append({
            "finding_id": f["id"],
            "category": f["category"],
            "summary": f["summary"][:60],
            "query": f["detection_query"],
            "status": f["status"],
            "matches": len(matches),
            "match_details": [
                {"uuid": m["uuid"][:8], "project": m["project"], "date": m["start_ts"][:10]}
                for m in matches[:5]
            ],
        })

    # Run default queries for untagged promoted findings
    for f in promoted_no_query:
        category = f["category"].upper().strip()
        default_qs = DEFAULT_QUERIES.get(category, [])
        total_matches = 0
        all_match_details = []
        for q in default_qs:
            matches = run_detection_query(sessions_db, q, since)
            total_matches += len(matches)
            all_match_details.extend(matches[:3])

        if default_qs:
            results.append({
                "finding_id": f["id"],
                "category": f["category"],
                "summary": f["summary"][:60],
                "query": f"(defaults: {', '.join(default_qs[:2])}...)",
                "status": f["status"],
                "matches": total_matches,
                "match_details": [
                    {"uuid": m["uuid"][:8], "project": m["project"], "date": m["start_ts"][:10]}
                    for m in all_match_details[:5]
                ],
            })

    # Report
    recurring = [r for r in results if r["matches"] > 0]
    holding = [r for r in results if r["matches"] == 0]

    print(f"Fix verification ({args.days}-day window)")
    print(f"{'='*60}")
    print(f"Queries run: {len(results)}")
    print(f"Fixes holding (no recurrence): {len(holding)}")
    print(f"Fixes recurring (needs escalation): {len(recurring)}")
    print()

    if recurring:
        print("⚠ RECURRING (fix didn't work):")
        for r in sorted(recurring, key=lambda x: x["matches"], reverse=True):
            print(f"  [{r['category']}] {r['summary']}")
            print(f"    matches={r['matches']}, query={r['query'][:50]}")
            for m in r["match_details"][:3]:
                print(f"    ↳ {m['uuid']} {m['date']} ({m['project']})")
            print()

    if holding:
        print("✓ HOLDING (fix working):")
        for r in holding:
            print(f"  [{r['category']}] {r['summary']}")
        print()

    # Update status for verified fixes
    now = datetime.now(timezone.utc).isoformat()
    for r in holding:
        findings_db.execute(
            "UPDATE findings SET status = 'verified', notes = ? WHERE id = ? AND status = 'promoted'",
            [f"Verified: no recurrence in {args.days}d as of {now[:10]}", r["finding_id"]],
        )
    findings_db.commit()

    log_metric("fix_verify",
               queries_run=len(results),
               recurring=len(recurring),
               holding=len(holding),
               days=args.days)


def cmd_tag(args):
    """Attach a detection query to a finding."""
    db = get_findings_db()
    result = db.execute("SELECT id, category, summary FROM findings WHERE id = ?", [args.id]).fetchone()
    if not result:
        print(f"No finding with ID {args.id}", file=sys.stderr)
        sys.exit(1)

    db.execute("UPDATE findings SET detection_query = ? WHERE id = ?", [args.query, args.id])
    db.commit()
    print(f"Tagged finding {args.id} ({result['category']}: {result['summary'][:40]})")
    print(f"  detection_query = {args.query}")


def cmd_report(args):
    """Generate fix effectiveness report."""
    db = get_findings_db()

    # Counts by status
    statuses = db.execute(
        "SELECT status, COUNT(*) as c FROM findings GROUP BY status ORDER BY c DESC"
    ).fetchall()

    print("Finding Status Report")
    print("=" * 40)
    for s in statuses:
        print(f"  {s['status']:<12} {s['c']:>4}")
    print()

    # Promotion velocity
    promoted = db.execute(
        """SELECT category, COUNT(*) as c,
                  AVG(julianday(promoted_at) - julianday(first_seen)) as avg_days
           FROM findings WHERE status IN ('promoted', 'verified')
           GROUP BY category ORDER BY c DESC"""
    ).fetchall()

    if promoted:
        print("Promotion velocity by category:")
        for p in promoted:
            avg = p["avg_days"] or 0
            print(f"  {p['category']:<25} {p['c']:>3} promoted, avg {avg:.1f} days to promote")
        print()

    # Verified fixes
    verified = db.execute(
        "SELECT category, summary, notes FROM findings WHERE status = 'verified' ORDER BY category"
    ).fetchall()
    if verified:
        print(f"Verified fixes ({len(verified)}):")
        for v in verified:
            print(f"  ✓ [{v['category']}] {v['summary'][:60]}")
        print()

    # Stale staging
    stale = db.execute(
        """SELECT COUNT(*) as c FROM findings
           WHERE status = 'staging' AND occurrences < 2
                 AND last_seen < date('now', '-30 days')"""
    ).fetchone()["c"]
    if stale:
        print(f"⚠ {stale} stale findings in staging (>30 days, <2 occurrences) — run `decay`")


def main():
    parser = argparse.ArgumentParser(description="Fix verification")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run detection queries")
    p_run.add_argument("--days", type=int, default=14, help="Look-back window (default: 14)")

    p_tag = sub.add_parser("tag", help="Tag finding with detection query")
    p_tag.add_argument("id", type=int, help="Finding ID")
    p_tag.add_argument("query", help="FTS5 search query")

    p_report = sub.add_parser("report", help="Fix effectiveness report")
    p_report.add_argument("--days", type=int, default=30, help="Report window (default: 30)")

    args = parser.parse_args()

    commands = {
        "run": cmd_run,
        "tag": cmd_tag,
        "report": cmd_report,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
