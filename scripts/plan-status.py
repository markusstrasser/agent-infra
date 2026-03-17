#!/usr/bin/env python3
"""Plan status tracker — scans .claude/plans/ across projects.

Usage:
    plan-status.py                  # Human-readable table
    plan-status.py --json           # Machine-readable JSON
    plan-status.py --active         # Only partial/running plans
    plan-status.py --update FILE STATUS [--completed PHASES]
                                    # Update plan frontmatter

Plan files use YAML frontmatter:
    ---
    status: pending|running|partial|done|failed
    completed_phases: [1, 2]
    content_hash: abc123
    updated: 2026-03-17T12:00:00Z
    ---
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECTS_DIR = Path.home() / "Projects"
PROJECT_NAMES = ["meta", "intel", "selve", "genomics", "arc-agi", "skills"]


def parse_frontmatter(text: str) -> dict:
    """Extract YAML-ish frontmatter from plan file."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            fm[key.strip()] = val
    return fm


def content_hash(text: str) -> str:
    """Hash plan body (everything after frontmatter) for idempotency."""
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
    body = m.group(1) if m else text
    return hashlib.sha256(body.encode()).hexdigest()[:12]


def count_phases(text: str) -> tuple[int, list[str]]:
    """Count total phases and identify completed ones from ### Phase headers."""
    phases = re.findall(r"^### Phase (\d+[a-z]?):?\s*(.*)", text, re.MULTILINE)
    total = len(phases)
    return total, [p[0] for p in phases]


def scan_plans() -> list[dict]:
    """Scan all projects for plan files."""
    results = []
    for name in PROJECT_NAMES:
        plans_dir = PROJECTS_DIR / name / ".claude" / "plans"
        if not plans_dir.exists():
            continue
        for f in sorted(plans_dir.glob("*.md")):
            try:
                text = f.read_text()
            except OSError:
                continue
            fm = parse_frontmatter(text)
            total_phases, phase_ids = count_phases(text)
            stat = f.stat()
            results.append({
                "project": name,
                "file": f.name,
                "path": str(f),
                "status": fm.get("status", "unknown"),
                "completed_phases": fm.get("completed_phases", []),
                "total_phases": total_phases,
                "content_hash": content_hash(text),
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "size": stat.st_size,
            })
    return results


def update_plan(filepath: str, status: str, completed: list[str] | None = None):
    """Update or add YAML frontmatter to a plan file."""
    p = Path(filepath)
    text = p.read_text()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chash = content_hash(text)

    new_fm = f"---\nstatus: {status}\n"
    if completed:
        new_fm += f"completed_phases: [{', '.join(completed)}]\n"
    new_fm += f"content_hash: {chash}\nupdated: {now}\n---\n"

    # Replace existing frontmatter or prepend
    if text.startswith("---\n"):
        text = re.sub(r"^---\n.*?\n---\n", new_fm, text, count=1, flags=re.DOTALL)
    else:
        text = new_fm + text

    p.write_text(text)
    print(f"Updated {p.name}: status={status}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Plan status tracker")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--active", action="store_true", help="Only partial/running")
    parser.add_argument("--update", metavar="FILE", help="Update plan status")
    parser.add_argument("--status", default="partial", help="Status to set")
    parser.add_argument("--completed", help="Comma-separated completed phase numbers")
    args = parser.parse_args()

    if args.update:
        completed = args.completed.split(",") if args.completed else None
        update_plan(args.update, args.status, completed)
        return

    plans = scan_plans()
    if args.active:
        plans = [p for p in plans if p["status"] in ("partial", "running")]

    if args.json:
        print(json.dumps(plans, indent=2))
        return

    if not plans:
        print("No plans found.")
        return

    # Table output
    print(f"{'Project':<10} {'Status':<10} {'Phases':<10} {'Modified':<22} {'File'}")
    print("-" * 90)
    for p in plans:
        completed = p["completed_phases"]
        phase_str = f"{len(completed) if isinstance(completed, list) else '?'}/{p['total_phases']}" if p["total_phases"] else "—"
        mod = p["modified"][:16].replace("T", " ")
        status = p["status"]
        # Color coding for terminal
        if status in ("partial", "running"):
            status = f"\033[33m{status}\033[0m"
        elif status == "done":
            status = f"\033[32m{status}\033[0m"
        elif status == "failed":
            status = f"\033[31m{status}\033[0m"
        print(f"{p['project']:<10} {status:<20} {phase_str:<10} {mod:<22} {p['file']}")


if __name__ == "__main__":
    main()
