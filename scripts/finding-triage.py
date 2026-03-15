#!/usr/bin/env python3
"""Finding auto-triage — SQLite staging for session-analyst findings.

Manages a findings database with fingerprinting and recurrence counting.
Findings that recur 2+ times auto-promote to actionable. Novel findings
stay in staging until they either recur or decay.

Usage:
    finding-triage.py ingest <json_file>   # Ingest findings from session-retro JSON
    finding-triage.py promote [--dry-run]  # Auto-promote findings with 2+ recurrences
    finding-triage.py status               # Show staging table summary
    finding-triage.py list [--all]         # List findings (default: pending only)
    finding-triage.py decay [--days 30]    # Archive stale findings
"""

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import log_metric

DB_PATH = Path.home() / ".claude" / "findings.db"
IMPROVEMENT_LOG = Path.home() / "Projects" / "meta" / "improvement-log.md"
RETRO_ARTIFACTS = Path.home() / "Projects" / "meta" / "artifacts" / "session-retro"

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',
    evidence TEXT,
    root_cause TEXT,
    proposed_fix TEXT,
    session_uuid TEXT,
    project TEXT,
    source_file TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    occurrences INTEGER DEFAULT 1,
    status TEXT DEFAULT 'staging',
    promoted_at TEXT,
    detection_query TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_fingerprint ON findings(fingerprint);
CREATE INDEX IF NOT EXISTS idx_status ON findings(status);
CREATE INDEX IF NOT EXISTS idx_category ON findings(category);
CREATE INDEX IF NOT EXISTS idx_last_seen ON findings(last_seen);
"""


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    return db


def fingerprint(category: str, summary: str) -> str:
    """Generate a stable fingerprint for deduplication.

    Normalizes: lowercase, strip session IDs, strip dates, collapse whitespace.
    Two findings about the same anti-pattern in different sessions should match.
    """
    text = f"{category.lower()}::{summary.lower()}"
    # Strip session UUIDs (8+ hex chars)
    text = re.sub(r"[0-9a-f]{8,}", "SESSION", text)
    # Strip dates
    text = re.sub(r"\d{4}-\d{2}-\d{2}", "DATE", text)
    # Strip specific file paths
    text = re.sub(r"/[^\s]+\.(py|md|sh|json|ts|js)", "FILE", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def cmd_ingest(args):
    """Ingest findings from a session-retro JSON file or artifacts directory."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    source_path = Path(args.json_file)
    if source_path.is_dir():
        # Ingest all JSON files in directory
        files = sorted(source_path.glob("*.json")) + sorted(source_path.glob("*.md"))
    else:
        files = [source_path]

    total_ingested = 0
    total_deduped = 0

    for fpath in files:
        findings = _parse_findings(fpath)
        if not findings:
            continue

        for f in findings:
            fp = fingerprint(f["category"], f["summary"])

            # Check if this fingerprint already exists
            existing = db.execute(
                "SELECT id, occurrences, last_seen FROM findings WHERE fingerprint = ?",
                [fp],
            ).fetchone()

            if existing:
                # Update recurrence
                db.execute(
                    """UPDATE findings SET
                        occurrences = occurrences + 1,
                        last_seen = ?,
                        evidence = COALESCE(?, evidence),
                        session_uuid = COALESCE(?, session_uuid)
                    WHERE id = ?""",
                    [now, f.get("evidence"), f.get("session_uuid"), existing["id"]],
                )
                total_deduped += 1
            else:
                # Insert new finding
                db.execute(
                    """INSERT INTO findings
                        (fingerprint, category, summary, severity, evidence, root_cause,
                         proposed_fix, session_uuid, project, source_file,
                         first_seen, last_seen, occurrences, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'staging')""",
                    [
                        fp,
                        f["category"],
                        f["summary"],
                        f.get("severity", "medium"),
                        f.get("evidence"),
                        f.get("root_cause"),
                        f.get("proposed_fix"),
                        f.get("session_uuid"),
                        f.get("project"),
                        str(fpath),
                        now,
                        now,
                    ],
                )
                total_ingested += 1

    db.commit()
    print(f"Ingested: {total_ingested} new, {total_deduped} recurrences updated")

    log_metric("finding_triage_ingest",
               new=total_ingested, deduped=total_deduped,
               source=str(args.json_file))


def _parse_findings(fpath: Path) -> list[dict]:
    """Parse findings from JSON or markdown file."""
    content = fpath.read_text()

    # Try JSON first (session-retro output format)
    if fpath.suffix == ".json":
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "findings" in data:
                return data["findings"]
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Try markdown (improvement-log format or retro artifact)
    if fpath.suffix == ".md":
        return _parse_markdown_findings(content)

    return []


def _parse_markdown_findings(content: str) -> list[dict]:
    """Parse findings from markdown format (improvement-log style)."""
    findings = []
    current = None

    for line in content.split("\n"):
        # New finding header: ### [DATE] CATEGORY: summary
        m = re.match(r"^###\s+\[(\d{4}-\d{2}-\d{2})\]\s+(\w[\w\s]*?):\s+(.+)$", line)
        if m:
            if current:
                findings.append(current)
            current = {
                "category": m.group(2).strip(),
                "summary": m.group(3).strip(),
            }
            continue

        if current is None:
            continue

        # Parse fields
        if line.startswith("- **Evidence:**"):
            current["evidence"] = line.split("**Evidence:**", 1)[1].strip()
        elif line.startswith("- **Session:**"):
            parts = line.split("**Session:**", 1)[1].strip().split()
            if len(parts) >= 2:
                current["project"] = parts[0]
                current["session_uuid"] = parts[1]
            elif parts:
                current["session_uuid"] = parts[0]
        elif line.startswith("- **Severity:**"):
            sev = line.split("**Severity:**", 1)[1].strip().split()[0].lower()
            if sev in ("low", "medium", "high"):
                current["severity"] = sev
        elif line.startswith("- **Root cause:**"):
            current["root_cause"] = line.split("**Root cause:**", 1)[1].strip()
        elif line.startswith("- **Proposed fix:**"):
            current["proposed_fix"] = line.split("**Proposed fix:**", 1)[1].strip()

    if current:
        findings.append(current)

    return findings


def cmd_promote(args):
    """Auto-promote findings with 2+ recurrences."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    candidates = db.execute(
        """SELECT * FROM findings
           WHERE status = 'staging' AND occurrences >= 2
           ORDER BY occurrences DESC, severity DESC""",
    ).fetchall()

    if not candidates:
        print("No findings ready for promotion (need 2+ occurrences).")
        return

    print(f"Found {len(candidates)} findings ready for promotion:\n")

    promoted = 0
    for f in candidates:
        print(f"  [{f['severity'].upper()}] {f['category']}: {f['summary']}")
        print(f"    Occurrences: {f['occurrences']}, "
              f"First: {f['first_seen'][:10]}, Last: {f['last_seen'][:10]}")
        if f["proposed_fix"]:
            print(f"    Fix: {f['proposed_fix']}")
        print()

        if not args.dry_run:
            db.execute(
                "UPDATE findings SET status = 'promoted', promoted_at = ? WHERE id = ?",
                [now, f["id"]],
            )
            # Append to improvement-log.md
            _append_to_improvement_log(f)
            promoted += 1

    if args.dry_run:
        print(f"(dry run — {len(candidates)} would be promoted)")
    else:
        db.commit()
        print(f"Promoted {promoted} findings to improvement-log.md")
        log_metric("finding_triage_promote", promoted=promoted)


def _append_to_improvement_log(finding: sqlite3.Row):
    """Append a promoted finding to improvement-log.md."""
    today = datetime.now().strftime("%Y-%m-%d")
    entry = f"""
### [{today}] {finding['category']}: {finding['summary']}
- **Session:** {finding['project'] or '?'} {finding['session_uuid'] or '?'}
- **Evidence:** {finding['evidence'] or 'See staging DB'}
- **Failure mode:** {finding['category']}
- **Proposed fix:** {finding['proposed_fix'] or 'TBD'}
- **Root cause:** {finding['root_cause'] or 'TBD'}
- **Recurrences:** {finding['occurrences']} (auto-promoted from staging)
- **Status:** [ ] proposed
"""
    with open(IMPROVEMENT_LOG, "a") as f:
        f.write(entry)


def cmd_status(args):
    """Show staging table summary."""
    db = get_db()

    total = db.execute("SELECT COUNT(*) as c FROM findings").fetchone()["c"]
    staging = db.execute("SELECT COUNT(*) as c FROM findings WHERE status = 'staging'").fetchone()["c"]
    promoted = db.execute("SELECT COUNT(*) as c FROM findings WHERE status = 'promoted'").fetchone()["c"]
    archived = db.execute("SELECT COUNT(*) as c FROM findings WHERE status = 'archived'").fetchone()["c"]

    print(f"Total findings: {total}")
    print(f"  Staging:  {staging}")
    print(f"  Promoted: {promoted}")
    print(f"  Archived: {archived}")
    print()

    # Category breakdown
    cats = db.execute(
        """SELECT category, COUNT(*) as c, SUM(occurrences) as occ
           FROM findings WHERE status = 'staging'
           GROUP BY category ORDER BY occ DESC"""
    ).fetchall()
    if cats:
        print("Staging by category:")
        for row in cats:
            print(f"  {row['category']:<30} {row['c']:>3} findings, {row['occ']:>4} occurrences")

    # Ready for promotion
    ready = db.execute(
        "SELECT COUNT(*) as c FROM findings WHERE status = 'staging' AND occurrences >= 2"
    ).fetchone()["c"]
    if ready:
        print(f"\n⚡ {ready} findings ready for promotion (2+ occurrences)")


def cmd_list(args):
    """List findings."""
    db = get_db()

    if args.all:
        rows = db.execute("SELECT * FROM findings ORDER BY last_seen DESC").fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM findings WHERE status = 'staging' ORDER BY occurrences DESC, last_seen DESC"
        ).fetchall()

    if not rows:
        print("No findings.")
        return

    for f in rows:
        status_icon = {"staging": "○", "promoted": "●", "archived": "◌", "verified": "✓"}.get(
            f["status"], "?"
        )
        print(
            f"{status_icon} [{f['severity']:<6}] {f['category']}: {f['summary'][:70]}"
        )
        print(f"  occ={f['occurrences']}  fp={f['fingerprint'][:8]}  "
              f"first={f['first_seen'][:10]}  last={f['last_seen'][:10]}  "
              f"status={f['status']}")
        print()


def cmd_decay(args):
    """Archive findings not seen in N days."""
    db = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    stale = db.execute(
        """SELECT COUNT(*) as c FROM findings
           WHERE status = 'staging' AND last_seen < ? AND occurrences < 2""",
        [cutoff],
    ).fetchone()["c"]

    if stale == 0:
        print(f"No stale findings (older than {args.days} days with <2 occurrences).")
        return

    print(f"Archiving {stale} stale findings (last seen before {cutoff[:10]}).")
    db.execute(
        """UPDATE findings SET status = 'archived'
           WHERE status = 'staging' AND last_seen < ? AND occurrences < 2""",
        [cutoff],
    )
    db.commit()
    log_metric("finding_triage_decay", archived=stale, cutoff_days=args.days)


def main():
    parser = argparse.ArgumentParser(description="Finding auto-triage")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingest findings from JSON/markdown")
    p_ingest.add_argument("json_file", help="Path to findings JSON or directory")

    p_promote = sub.add_parser("promote", help="Auto-promote recurring findings")
    p_promote.add_argument("--dry-run", action="store_true")

    sub.add_parser("status", help="Show staging summary")

    p_list = sub.add_parser("list", help="List findings")
    p_list.add_argument("--all", action="store_true", help="Include promoted/archived")

    p_decay = sub.add_parser("decay", help="Archive stale findings")
    p_decay.add_argument("--days", type=int, default=30, help="Stale threshold (default: 30)")

    args = parser.parse_args()

    commands = {
        "ingest": cmd_ingest,
        "promote": cmd_promote,
        "status": cmd_status,
        "list": cmd_list,
        "decay": cmd_decay,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
