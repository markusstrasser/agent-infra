#!/usr/bin/env python3
"""Maintenance for design-review patterns.jsonl — dedup, prune, status-update.

Usage:
    pattern-maintenance.py dedup              # Merge duplicate pattern names
    pattern-maintenance.py prune [--days 30]  # Archive old patterns
    pattern-maintenance.py status             # Cross-reference with findings DB
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PATTERNS_FILE = Path(__file__).resolve().parent.parent / "artifacts" / "design-review" / "patterns.jsonl"
ARCHIVE_FILE = PATTERNS_FILE.parent / "patterns-archive.jsonl"
IMPROVEMENT_LOG = Path(__file__).resolve().parent.parent / "improvement-log.md"

from common.paths import FINDINGS_DB


def load_patterns() -> list[dict]:
    if not PATTERNS_FILE.exists():
        return []
    patterns = []
    for line in PATTERNS_FILE.read_text().splitlines():
        if not line.strip():
            continue
        try:
            patterns.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return patterns


def save_patterns(patterns: list[dict]) -> None:
    PATTERNS_FILE.write_text(
        "\n".join(json.dumps(p, default=str) for p in patterns) + "\n"
    )


def cmd_dedup(_args):
    """Merge duplicate pattern names — keep latest timestamp, sum frequencies, union sessions/projects."""
    patterns = load_patterns()
    if not patterns:
        print("No patterns to deduplicate.")
        return

    merged: dict[str, dict] = {}
    for p in patterns:
        name = p.get("name", "unknown")
        if name not in merged:
            merged[name] = dict(p)
            # Ensure sets for merging
            merged[name]["_sessions"] = set(p.get("sessions", []))
            merged[name]["_projects"] = set(p.get("projects", []))
        else:
            existing = merged[name]
            # Keep latest timestamp
            if p.get("ts", "") > existing.get("ts", ""):
                existing["ts"] = p["ts"]
                existing["evidence"] = p.get("evidence", existing.get("evidence", ""))
            # Sum frequency
            existing["frequency"] = existing.get("frequency", 0) + p.get("frequency", 0)
            # Union sessions and projects
            existing["_sessions"].update(p.get("sessions", []))
            existing["_projects"].update(p.get("projects", []))

    # Convert sets back to lists
    result = []
    for p in merged.values():
        p["sessions"] = sorted(p.pop("_sessions"))
        p["projects"] = sorted(p.pop("_projects"))
        result.append(p)

    before = len(patterns)
    after = len(result)
    save_patterns(result)
    print(f"Deduplicated: {before} → {after} patterns ({before - after} merged)")


def cmd_prune(args):
    """Archive patterns older than --days (default 30)."""
    patterns = load_patterns()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    keep = []
    archive = []
    for p in patterns:
        if p.get("ts", "") < cutoff and p.get("status") != "implemented":
            archive.append(p)
        else:
            keep.append(p)

    if not archive:
        print(f"No patterns older than {args.days} days to archive.")
        return

    # Append to archive file
    with open(ARCHIVE_FILE, "a") as f:
        for p in archive:
            f.write(json.dumps(p, default=str) + "\n")

    save_patterns(keep)
    print(f"Archived {len(archive)} patterns (>{args.days}d old). {len(keep)} remaining.")


def cmd_status(_args):
    """Cross-reference patterns with findings DB and improvement-log."""
    patterns = load_patterns()
    if not patterns:
        print("No patterns.")
        return

    # Load improvement-log statuses
    implemented_keywords = set()
    if IMPROVEMENT_LOG.exists():
        current_title = ""
        for line in IMPROVEMENT_LOG.read_text().splitlines():
            if line.startswith("### "):
                current_title = line.lower()
            if "status:" in line.lower() and "[x]" in line:
                # Extract keywords from the title
                for word in current_title.split():
                    if len(word) > 4 and word.isalpha():
                        implemented_keywords.add(word)

    # Load findings DB concept tags
    findings_concepts = set()
    if FINDINGS_DB.exists():
        import sqlite3
        try:
            db = sqlite3.connect(str(FINDINGS_DB))
            rows = db.execute(
                "SELECT DISTINCT concept_tag FROM findings WHERE concept_tag IS NOT NULL AND status='promoted'"
            ).fetchall()
            findings_concepts = {r[0] for r in rows}
            db.close()
        except Exception:
            pass

    # Status report
    updated = 0
    print(f"{'Status':<14} {'Count':<6} {'Name'}")
    print("-" * 60)

    by_status = defaultdict(list)
    for p in patterns:
        name = p.get("name", "unknown")
        current = p.get("status", "untracked")

        # Check if addressed
        name_words = set(name.replace("-", " ").lower().split())
        if name_words & implemented_keywords:
            current = "addressed"
        elif any(tag in name.replace("-", "_") for tag in findings_concepts):
            current = "tracked"

        if current != p.get("status"):
            p["status"] = current
            updated += 1

        by_status[current].append(name)

    for status, names in sorted(by_status.items()):
        for name in sorted(names):
            print(f"  {status:<12} {name}")
    print()
    print(f"Total: {len(patterns)} patterns. Updated: {updated}.")

    if updated:
        save_patterns(patterns)
        print(f"Saved {updated} status updates to patterns.jsonl.")


def main():
    parser = argparse.ArgumentParser(description="Design-review pattern maintenance")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("dedup", help="Merge duplicate pattern names")

    prune_p = sub.add_parser("prune", help="Archive old patterns")
    prune_p.add_argument("--days", type=int, default=30, help="Age threshold")

    sub.add_parser("status", help="Cross-reference with findings DB and improvement-log")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"dedup": cmd_dedup, "prune": cmd_prune, "status": cmd_status}[args.command](args)


if __name__ == "__main__":
    main()
