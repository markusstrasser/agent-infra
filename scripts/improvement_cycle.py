#!/usr/bin/env python3
"""Improvement-log cycle time — measures self-improvement pipeline velocity.

Parses improvement-log.md, extracts finding dates and status transitions,
computes cycle times, and identifies bottlenecks.

Usage:
    improvement_cycle.py                  # full report
    improvement_cycle.py --json           # machine-readable output
    improvement_cycle.py --stuck          # only stuck/zombie findings
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "improvement-log.md"

# Match finding headers: ### [2026-03-26] CATEGORY: description
FINDING_RE = re.compile(
    r"^### \[(\d{4}-\d{2}-\d{2})\]\s+(?:Session Analyst.*|(.+))$"
)
# Match status lines
STATUS_RE = re.compile(r"^\- \*\*Status:\*\*\s+(.+)$")


def parse_status(text: str) -> tuple[str, str | None]:
    """Classify status into: implemented, proposed, deferred, superseded, new."""
    lower = text.lower()
    # Extract implementation date if present (date in parentheses)
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    impl_date = date_match.group(1) if date_match else None

    if "[x]" in lower or "implemented" in lower or "covered" in lower:
        return "implemented", impl_date
    if "[~]" in lower or "deferred" in lower:
        return "deferred", impl_date
    if "superseded" in lower:
        return "superseded", impl_date
    if "[ ]" in lower or "new finding" in lower or "first occurrence" in lower:
        return "new", None
    # Fallback: if it has content but no checkbox, treat as proposed
    return "proposed", impl_date


def parse_log(path: Path) -> list[dict]:
    """Parse improvement-log.md into structured findings."""
    findings = []
    current = None

    for line in path.read_text().splitlines():
        m = FINDING_RE.match(line)
        if m:
            if current:
                findings.append(current)
            observed = m.group(1)
            title = m.group(2) or line.split("]", 1)[1].strip()
            # Skip batch headers (Session Analyst — ...)
            if "Session Analyst" in title:
                current = None
                continue
            current = {
                "observed": observed,
                "title": title[:80],
                "status": "new",
                "impl_date": None,
                "raw_status": "",
            }
            continue

        if current:
            sm = STATUS_RE.match(line)
            if sm:
                current["raw_status"] = sm.group(1)
                current["status"], current["impl_date"] = parse_status(sm.group(1))

    if current:
        findings.append(current)
    return findings


def compute_metrics(findings: list[dict]) -> dict:
    today = date.today().isoformat()
    total = len(findings)

    by_status = {}
    for f in findings:
        by_status.setdefault(f["status"], []).append(f)

    # Cycle times for implemented findings
    cycle_days = []
    for f in by_status.get("implemented", []):
        if f["impl_date"]:
            try:
                obs = datetime.strptime(f["observed"], "%Y-%m-%d").date()
                imp = datetime.strptime(f["impl_date"], "%Y-%m-%d").date()
                cycle_days.append((imp - obs).days)
            except ValueError:
                pass

    # Stuck findings: new or proposed for >7 days
    stuck = []
    for f in by_status.get("new", []) + by_status.get("proposed", []):
        try:
            obs = datetime.strptime(f["observed"], "%Y-%m-%d").date()
            age = (datetime.strptime(today, "%Y-%m-%d").date() - obs).days
            if age > 7:
                stuck.append({**f, "age_days": age})
        except ValueError:
            pass

    # Zombies: implemented but no measurement mentioned
    zombies = []
    for f in by_status.get("implemented", []):
        raw = f["raw_status"].lower()
        if "measured" not in raw and "verified" not in raw and "monitor" not in raw:
            zombies.append(f)

    return {
        "total_findings": total,
        "by_status": {k: len(v) for k, v in by_status.items()},
        "cycle_days": sorted(cycle_days),
        "median_cycle": sorted(cycle_days)[len(cycle_days) // 2] if cycle_days else None,
        "mean_cycle": round(sum(cycle_days) / len(cycle_days), 1) if cycle_days else None,
        "stuck": stuck,
        "zombies_no_measurement": len(zombies),
        "measurement_rate": round(
            (len(by_status.get("implemented", [])) - len(zombies))
            / max(len(by_status.get("implemented", [])), 1) * 100, 1
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--stuck", action="store_true", help="Only show stuck findings")
    parser.add_argument("--log", type=Path, default=LOG_PATH, help="Path to improvement-log.md")
    args = parser.parse_args()

    if not args.log.exists():
        print(f"error: {args.log} not found", file=sys.stderr)
        return 1

    findings = parse_log(args.log)
    metrics = compute_metrics(findings)

    if args.json:
        print(json.dumps(metrics, indent=2))
        return 0

    if args.stuck:
        if not metrics["stuck"]:
            print("No stuck findings (>7 days without implementation)")
            return 0
        print(f"Stuck findings ({len(metrics['stuck'])}):")
        for f in sorted(metrics["stuck"], key=lambda x: x["age_days"], reverse=True):
            print(f"  {f['age_days']}d  [{f['status']}]  {f['title']}")
        return 0

    # Full report
    print(f"Improvement Log — Self-Improvement Velocity")
    print(f"{'=' * 50}")
    print(f"Total findings: {metrics['total_findings']}")
    print(f"Status: {metrics['by_status']}")
    print()

    if metrics["cycle_days"]:
        print(f"Cycle time (observed → implemented):")
        print(f"  Median: {metrics['median_cycle']}d")
        print(f"  Mean:   {metrics['mean_cycle']}d")
        print(f"  Range:  {min(metrics['cycle_days'])}d – {max(metrics['cycle_days'])}d")
    else:
        print("No cycle time data (no implemented findings with dates)")

    print()
    print(f"Measurement rate: {metrics['measurement_rate']}%")
    print(f"  ({metrics['zombies_no_measurement']} implemented findings never verified)")

    if metrics["stuck"]:
        print(f"\nStuck findings ({len(metrics['stuck'])}):")
        for f in sorted(metrics["stuck"], key=lambda x: x["age_days"], reverse=True)[:10]:
            print(f"  {f['age_days']}d  [{f['status']}]  {f['title']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
