#!/usr/bin/env python3
"""Extract #f feedback from user messages in Claude Code session transcripts.

The user drops `#f` inline during sessions as a ground-truth signal.
The text after it carries the meaning — no predefined taxonomy.

Usage:
    uv run python3 scripts/extract_user_tags.py [--days N] [--project P] [--json]

Scans ~/.claude/projects/*/UUID.jsonl for user messages containing #f.
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Match #f at word boundary (not #foo, #function, etc.)
TAG_RE = re.compile(r"(?:^|\s)#f(?:\s|$)", re.MULTILINE)


def extract_project_name(dir_name: str) -> str:
    """Convert dir name like '-Users-alien-Projects-intel' to 'intel'."""
    parts = dir_name.split("-")
    for i, p in enumerate(parts):
        if p == "Projects" and i + 1 < len(parts):
            return "-".join(parts[i + 1 :])
    return dir_name


def scan_session(session_path: Path) -> list[dict]:
    """Extract #f messages from a session JSONL file."""
    results = []
    try:
        with open(session_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if msg.get("type") != "human" and msg.get("role") != "human":
                    continue

                text = ""
                content = msg.get("content", msg.get("message", ""))
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = " ".join(
                        b.get("text", "") for b in content if isinstance(b, dict)
                    )

                if TAG_RE.search(text):
                    # Strip the #f itself, keep the rest as the feedback
                    feedback = TAG_RE.sub(" ", text).strip()
                    results.append(
                        {
                            "session": session_path.stem,
                            "line": line_num,
                            "feedback": feedback[:500],
                        }
                    )
    except (OSError, UnicodeDecodeError):
        pass
    return results


def main():
    days = 7
    project_filter = None
    json_output = "--json" in sys.argv

    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    if "--project" in sys.argv:
        idx = sys.argv.index("--project")
        if idx + 1 < len(sys.argv):
            project_filter = sys.argv[idx + 1]

    cutoff = datetime.now() - timedelta(days=days)
    cutoff_ts = cutoff.timestamp()

    all_feedback = []

    if not PROJECTS_DIR.exists():
        print("No projects directory found", file=sys.stderr)
        sys.exit(1)

    for proj_dir in PROJECTS_DIR.iterdir():
        if not proj_dir.is_dir():
            continue
        proj_name = extract_project_name(proj_dir.name)
        if project_filter and project_filter not in proj_name:
            continue

        for session_file in proj_dir.glob("*.jsonl"):
            if session_file.stat().st_mtime < cutoff_ts:
                continue

            results = scan_session(session_file)
            for r in results:
                r["project"] = proj_name
                all_feedback.append(r)

    if json_output:
        json.dump(all_feedback, sys.stdout, indent=2)
        return

    total = len(all_feedback)
    print(f"User feedback (#f): {total} entries in last {days} days\n")

    if not total:
        print("No #f feedback found yet.")
        return

    # Group by project
    by_project = defaultdict(list)
    for e in all_feedback:
        by_project[e["project"]].append(e)

    for proj in sorted(by_project):
        entries = by_project[proj]
        print(f"  {proj} ({len(entries)})")
        for e in entries:
            preview = e["feedback"][:120].replace("\n", " ")
            print(f"    {e['session'][:8]}:{e['line']} | {preview}")
        print()


if __name__ == "__main__":
    main()
