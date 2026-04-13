#!/usr/bin/env python3
"""Plan staleness scanner — find stale .claude/plans/ across projects.

Plans >14d with incomplete items → flag. Plans >30d → propose archive.
Writes JSON report and appends findings to MAINTAIN.md.
"""

import json
import re
from datetime import datetime
from pathlib import Path

PROJECTS_DIR = Path.home() / "Projects"
PROJECTS = ["agent-infra", "intel", "phenome", "genomics", "skills", "research-mcp"]
STALE_THRESHOLD = 14  # days
ARCHIVE_THRESHOLD = 30  # days


def scan_plans() -> list[dict]:
    """Scan .claude/plans/ across projects for stale plans."""
    findings = []
    now = datetime.now()

    for proj_name in PROJECTS:
        plans_dir = PROJECTS_DIR / proj_name / ".claude" / "plans"
        if not plans_dir.is_dir():
            continue

        for plan_file in plans_dir.glob("*.md"):
            text = plan_file.read_text(errors="replace")
            stat = plan_file.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime)
            age_days = (now - mtime).days

            if age_days < STALE_THRESHOLD:
                continue

            # Check for incomplete items
            incomplete = len(re.findall(r"^\s*[-*]\s*\[ \]", text, re.MULTILINE))
            completed = len(re.findall(r"^\s*[-*]\s*\[x\]", text, re.MULTILINE | re.IGNORECASE))

            # Extract date from filename if present
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", plan_file.name)
            plan_date = date_match.group(1) if date_match else mtime.strftime("%Y-%m-%d")

            status = "archive" if age_days >= ARCHIVE_THRESHOLD else "stale"

            findings.append({
                "project": proj_name,
                "file": str(plan_file.relative_to(PROJECTS_DIR / proj_name)),
                "name": plan_file.stem,
                "age_days": age_days,
                "plan_date": plan_date,
                "incomplete": incomplete,
                "completed": completed,
                "status": status,
                "last_modified": mtime.isoformat()[:10],
            })

    return sorted(findings, key=lambda x: -x["age_days"])


def append_to_maintain(findings: list[dict]) -> None:
    """Append stale plan findings to MAINTAIN.md if it exists."""
    maintain_path = PROJECTS_DIR / "agent-infra" / "MAINTAIN.md"
    if not maintain_path.exists():
        return

    text = maintain_path.read_text()

    # Find highest existing M-number
    existing = re.findall(r"\*\*M(\d+)\*\*", text)
    next_id = max((int(n) for n in existing), default=0) + 1

    new_entries = []
    for f in findings:
        if f["name"] in text:
            continue  # already tracked
        entry = (
            f"- **M{next_id:03d}** [new] [PLAN_STALE] "
            f"{f['project']}/{f['name']} — {f['age_days']}d old, "
            f"{f['incomplete']} incomplete items "
            f"(source: plan-staleness, {datetime.now().strftime('%Y-%m-%d')})"
        )
        new_entries.append(entry)
        next_id += 1

    if new_entries:
        # Insert after ## Findings header
        marker = "## Findings"
        if marker in text:
            idx = text.index(marker) + len(marker)
            # Find the next line
            nl = text.index("\n", idx)
            text = text[:nl + 1] + "\n".join(new_entries) + "\n" + text[nl + 1:]
            maintain_path.write_text(text)
            print(f"  ✓ {len(new_entries)} findings appended to MAINTAIN.md")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scan for stale plans")
    parser.add_argument("--output", help="JSON output path")
    parser.add_argument("--no-maintain", action="store_true", help="Skip MAINTAIN.md append")
    args = parser.parse_args()

    findings = scan_plans()

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(findings, indent=2))
        print(f"  ✓ {len(findings)} stale plans → {out_path}")

    if not args.no_maintain:
        append_to_maintain(findings)

    # Summary
    stale = [f for f in findings if f["status"] == "stale"]
    archive = [f for f in findings if f["status"] == "archive"]
    print(f"\n  {len(stale)} stale (>14d), {len(archive)} archive candidates (>30d)")
    for f in findings[:10]:
        marker = "📦" if f["status"] == "archive" else "⏰"
        print(f"  {marker} {f['project']}/{f['name']} — {f['age_days']}d, {f['incomplete']} incomplete")


if __name__ == "__main__":
    main()
