"""Generate and validate index files across meta project.

Replaces hand-maintained indexes with generated ones.
Preserves manually-written content (Topic, Consult before) for existing entries.
Reports discrepancies, adds new entries, removes stale ones.

Usage:
    uv run python3 scripts/generate-indexes.py [--check] [--fix]

    --check   Report discrepancies without modifying files (default)
    --fix     Update index files and CLAUDE.md counts in place

Also regenerates codebase-map.md (via codebase-map.py) when stale,
and cleans plans older than 14 days.
"""

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = ROOT / "research"
RESEARCH_INDEX = ROOT / ".claude" / "rules" / "research-index.md"
CLAUDE_MD = ROOT / "CLAUDE.md"
DECISIONS_DIR = ROOT / "decisions"


def extract_title(path: Path) -> str:
    """Extract first # heading from a markdown file."""
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line.startswith("# "):
                title = line[2:].strip()
                # Truncate long titles
                if len(title) > 80:
                    title = title[:77] + "..."
                return title
    except Exception:
        pass
    return path.stem.replace("-", " ").title()


def parse_research_index(path: Path) -> dict[str, dict]:
    """Parse existing research index table into {filename: {topic, consult_before}}."""
    entries = {}
    if not path.exists():
        return entries
    for line in path.read_text().splitlines():
        m = re.match(r'^\|\s*`([^`]+\.md)`\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$', line)
        if m:
            entries[m.group(1)] = {
                "topic": m.group(2).strip(),
                "consult_before": m.group(3).strip(),
            }
    return entries


def generate_research_index(fix: bool) -> list[str]:
    """Generate research index, return list of issues found."""
    issues = []

    actual_files = sorted(
        [f.name for f in RESEARCH_DIR.glob("*.md")],
        key=str.lower,
    )
    existing = parse_research_index(RESEARCH_INDEX)
    existing_names = set(existing.keys())
    actual_names = set(actual_files)

    # Find discrepancies
    missing_from_index = actual_names - existing_names
    stale_in_index = existing_names - actual_names

    for f in sorted(missing_from_index):
        title = extract_title(RESEARCH_DIR / f)
        issues.append(f"  NEW: {f} — {title}")

    for f in sorted(stale_in_index):
        issues.append(f"  STALE: {f} — in index but file deleted")

    if fix:
        # Always rewrite to keep frontmatter and sort order canonical
        lines = [
            "---",
            "paths:",
            '  - "research/**"',
            '  - "decisions/**"',
            "---",
            "",
            "# Research Index (`research/`)",
            "",
            "Consult these files before acting on the topic. Scan this table when starting a task.",
            "",
            "| File | Topic | Consult before |",
            "|------|-------|----------------|",
        ]
        for fname in actual_files:
            if fname in existing:
                topic = existing[fname]["topic"]
                consult = existing[fname]["consult_before"]
            else:
                topic = extract_title(RESEARCH_DIR / fname)
                consult = "TODO"
            lines.append(f"| `{fname}` | {topic} | {consult} |")

        RESEARCH_INDEX.write_text("\n".join(lines) + "\n")

    return issues


def update_claude_md_count(fix: bool) -> list[str]:
    """Check and optionally fix research memo count in CLAUDE.md."""
    issues = []
    actual_count = len(list(RESEARCH_DIR.glob("*.md")))

    text = CLAUDE_MD.read_text()
    m = re.search(r'(\d+)\s+research memos in `research/`', text)
    if m:
        claimed = int(m.group(1))
        if claimed != actual_count:
            issues.append(f"  CLAUDE.md says {claimed} research memos, actual: {actual_count}")
            if fix:
                text = text.replace(
                    f"{claimed} research memos in `research/`",
                    f"{actual_count} research memos in `research/`",
                )
                CLAUDE_MD.write_text(text)
    return issues


def check_decision_index(fix: bool) -> list[str]:
    """Check decisions/ directory for any index staleness."""
    issues = []
    if not DECISIONS_DIR.exists():
        return issues

    decisions = sorted(DECISIONS_DIR.glob("*.md"))
    decisions = [d for d in decisions if d.name != ".template.md"]

    # Check if CLAUDE.md references decisions
    text = CLAUDE_MD.read_text()
    m = re.search(r'Decision Journal \(`decisions/`\)', text)
    if not m:
        return issues

    # Count actual decisions
    count = len(decisions)
    if count > 0:
        issues.append(f"  {count} decision records in decisions/")

    return issues


def check_codebase_map(fix: bool) -> list[str]:
    """Check if codebase map is stale and regenerate if needed."""
    issues = []
    cmap = ROOT / ".claude" / "rules" / "codebase-map.md"
    cmap_script = ROOT / "scripts" / "codebase-map.py"

    if not cmap.exists() or not cmap_script.exists():
        return issues

    # Count actual .py files in scripts/
    actual_on_disk = len(list((ROOT / "scripts").rglob("*.py")))

    text = cmap.read_text()
    m = re.search(r'# (\d+) Python files', text)
    claimed = int(m.group(1)) if m else 0

    # Check age — stale if >7 days
    age_days = (time.time() - cmap.stat().st_mtime) / 86400

    if claimed != actual_on_disk:
        issues.append(f"  codebase-map.md lists {claimed} files, disk has {actual_on_disk}")
    elif age_days > 7:
        issues.append(f"  codebase-map.md is {age_days:.0f} days old")

    if fix and issues:
        result = subprocess.run(
            [sys.executable, str(cmap_script), str(ROOT), "--source-dirs", "scripts"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            issues.append("  Regenerated codebase-map.md")
        else:
            issues.append(f"  Failed to regenerate: {result.stderr.strip()[:200]}")

    return issues


def clean_stale_plans(fix: bool) -> list[str]:
    """Remove plan files older than 14 days."""
    issues = []
    plans_dir = ROOT / ".claude" / "plans"
    if not plans_dir.exists():
        return issues

    cutoff = time.time() - 14 * 86400
    stale = [
        p for p in plans_dir.glob("*.md")
        if p.stat().st_mtime < cutoff
    ]

    if stale:
        issues.append(f"  {len(stale)} plan(s) older than 14 days")
        if fix:
            for p in stale:
                p.unlink()
            issues.append(f"  Removed {len(stale)} stale plan(s)")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Generate and validate index files")
    parser.add_argument("--check", action="store_true", default=True,
                        help="Report discrepancies (default)")
    parser.add_argument("--fix", action="store_true",
                        help="Update files in place")
    args = parser.parse_args()

    all_issues = []

    print("Research index:")
    issues = generate_research_index(args.fix)
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(i)
    else:
        print("  OK")

    print("\nCLAUDE.md counts:")
    issues = update_claude_md_count(args.fix)
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(i)
    else:
        print("  OK")

    print("\nCodebase map:")
    issues = check_codebase_map(args.fix)
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(i)
    else:
        print("  OK")

    print("\nDecisions:")
    issues = check_decision_index(args.fix)
    if issues:
        for i in issues:
            print(i)
    else:
        print("  OK")

    print("\nStale plans:")
    issues = clean_stale_plans(args.fix)
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(i)
    else:
        print("  OK")

    if all_issues:
        if args.fix:
            print(f"\nFixed {len(all_issues)} issue(s).")
        else:
            print(f"\n{len(all_issues)} issue(s) found. Run with --fix to update.")
            sys.exit(1)
    else:
        print("\nAll indexes up to date.")


if __name__ == "__main__":
    main()
