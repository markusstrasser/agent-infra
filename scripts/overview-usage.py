#!/usr/bin/env python3
"""Overview usage tracker — measure overview read rates from session transcripts.

Scans Claude Code session transcripts for Read tool calls targeting *-overview.md files.
Reports: read rate, which projects, which overview types.

Usage: uv run python3 scripts/overview-usage.py [--days N]
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from config import PROJECT_ROOTS, extract_project_name

from common.paths import PROJECTS_DIR as SESSIONS_DIR


def scan_transcripts(days: int = 7) -> dict:
    """Scan session transcripts for overview reads."""
    cutoff = datetime.now() - timedelta(days=days)
    results = {
        "total_sessions": 0,
        "sessions_with_reads": 0,
        "reads_by_project": defaultdict(int),
        "reads_by_type": defaultdict(int),
        "read_files": [],
    }

    for project_dir in SESSIONS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        project_name = extract_project_name(project_dir.name)

        for transcript in project_dir.glob("*.jsonl"):
            # Skip non-session files
            if transcript.name in ("userConfig.json",):
                continue

            # Check file modification time as proxy for session time
            mtime = datetime.fromtimestamp(transcript.stat().st_mtime)
            if mtime < cutoff:
                continue

            results["total_sessions"] += 1
            session_has_read = False

            try:
                with open(transcript) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        # Look for Read tool calls targeting overview files
                        if entry.get("type") != "tool_use":
                            continue
                        tool_name = entry.get("name", "")
                        if tool_name != "Read":
                            continue
                        tool_input = entry.get("input", {})
                        file_path = tool_input.get("file_path", "")

                        if "-overview.md" in file_path:
                            session_has_read = True
                            # Extract overview type from filename
                            match = re.search(r"/([^/]+)-overview\.md$", file_path)
                            if match:
                                overview_type = match.group(1)
                                results["reads_by_type"][overview_type] += 1
                            results["reads_by_project"][project_name] += 1
                            results["read_files"].append(
                                {
                                    "file": file_path,
                                    "project": project_name,
                                    "session": transcript.stem,
                                    "time": mtime.isoformat(),
                                }
                            )
            except (OSError, UnicodeDecodeError):
                continue

            if session_has_read:
                results["sessions_with_reads"] += 1

    return results


def get_overview_freshness() -> list[dict]:
    """Get freshness info for all overviews across projects."""
    overviews = []
    for name, root in PROJECT_ROOTS.items():
        overview_dir = root / ".claude" / "overviews"
        if not overview_dir.exists():
            continue
        for f in sorted(overview_dir.glob("*-overview.md")):
            try:
                text = f.read_text()
                # Parse metadata comment
                meta_match = re.search(
                    r"<!-- Generated: (\S+) \| git: (\S+) \| model: (\S+) -->", text
                )
                if meta_match:
                    gen_ts = meta_match.group(1)
                    git_sha = meta_match.group(2)
                    model = meta_match.group(3)
                else:
                    gen_ts = datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                    git_sha = "?"
                    model = "?"

                overview_type = f.stem.replace("-overview", "")
                overviews.append(
                    {
                        "project": name,
                        "type": overview_type,
                        "generated": gen_ts,
                        "git": git_sha,
                        "model": model,
                        "size": f.stat().st_size,
                    }
                )
            except OSError:
                continue
    return overviews


def main():
    days = 7
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    print(f"Overview Usage Report — last {days} days")
    print("=" * 50)

    # Freshness
    overviews = get_overview_freshness()
    if overviews:
        print(f"\n  Overviews ({len(overviews)} across {len(set(o['project'] for o in overviews))} projects):")
        for o in overviews:
            age = ""
            try:
                gen_dt = datetime.fromisoformat(o["generated"].replace("Z", "+00:00")).replace(tzinfo=None)
                age_days = (datetime.now() - gen_dt).days
                age = f"{age_days}d ago" if age_days > 0 else "today"
            except (ValueError, TypeError):
                age = "?"
            print(f"    {o['project']:<12} {o['type']:<10} {age:<10} git:{o['git']:<8} {o['model']}")
    else:
        print("\n  No overviews found.")

    # Usage
    results = scan_transcripts(days)
    total = results["total_sessions"]
    reads = results["sessions_with_reads"]
    rate = reads / total if total > 0 else 0

    print(f"\n  Read rate: {reads}/{total} sessions ({rate:.0%})")

    if results["reads_by_project"]:
        print("\n  By project:")
        for proj, count in sorted(results["reads_by_project"].items(), key=lambda x: -x[1]):
            print(f"    {proj:<20} {count} reads")

    if results["reads_by_type"]:
        print("\n  By type:")
        for otype, count in sorted(results["reads_by_type"].items(), key=lambda x: -x[1]):
            print(f"    {otype:<20} {count} reads")

    # Trigger log stats
    trigger_counts = defaultdict(int)
    for name, root in PROJECT_ROOTS.items():
        trigger_log = root / ".claude" / "overview-trigger.log"
        if trigger_log.exists():
            try:
                for line in trigger_log.read_text().splitlines():
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        ts = entry.get("ts", "")
                        if ts and datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None) > datetime.now() - timedelta(days=days):
                            trigger_counts[name] += 1
                    except (json.JSONDecodeError, ValueError):
                        continue
            except OSError:
                continue

    if trigger_counts:
        print(f"\n  Trigger events (last {days}d):")
        for proj, count in sorted(trigger_counts.items(), key=lambda x: -x[1]):
            print(f"    {proj:<20} {count} triggers")

    print()


if __name__ == "__main__":
    main()
