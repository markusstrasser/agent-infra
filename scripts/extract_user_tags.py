#!/usr/bin/env python3
"""Extract #tags from user messages in Claude Code session transcripts.

Tags are inline annotations the human adds during sessions to communicate
valence and issues: #wrong, #good, #waste, #pushback, #stale, #design.

Usage:
    uv run python3 scripts/extract_user_tags.py [--days N] [--project P] [--json]

Scans ~/.claude/projects/*/UUID.jsonl for user messages containing #tags.
Outputs a summary grouped by tag, or raw JSON for piping into other tools.
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"

KNOWN_TAGS = {"#wrong", "#good", "#waste", "#pushback", "#stale", "#design"}
TAG_RE = re.compile(r"(#(?:wrong|good|waste|pushback|stale|design))\b", re.IGNORECASE)


def extract_project_name(dir_name: str) -> str:
    """Convert dir name like '-Users-alien-Projects-intel' to 'intel'."""
    parts = dir_name.split("-")
    # Find 'Projects' and take what follows
    for i, p in enumerate(parts):
        if p == "Projects" and i + 1 < len(parts):
            return "-".join(parts[i + 1 :])
    return dir_name


def scan_session(session_path: Path) -> list[dict]:
    """Extract tagged messages from a session JSONL file."""
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

                # Only user messages
                if msg.get("type") != "human" and msg.get("role") != "human":
                    continue

                # Extract text content
                text = ""
                content = msg.get("content", msg.get("message", ""))
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = " ".join(
                        b.get("text", "") for b in content if isinstance(b, dict)
                    )

                tags = TAG_RE.findall(text.lower())
                if tags:
                    results.append(
                        {
                            "session": session_path.stem,
                            "line": line_num,
                            "tags": [t.lower() for t in tags],
                            "text": text.strip()[:500],
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

    all_tags = []
    by_tag = defaultdict(list)

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
                all_tags.append(r)
                for tag in r["tags"]:
                    by_tag[tag].append(r)

    if json_output:
        json.dump(all_tags, sys.stdout, indent=2)
        return

    # Summary output
    total = len(all_tags)
    print(f"User tags: {total} tagged messages in last {days} days\n")

    if not total:
        print("No #tags found. Tags: #wrong #good #waste #pushback #stale #design")
        return

    for tag in sorted(by_tag.keys()):
        entries = by_tag[tag]
        print(f"  {tag} ({len(entries)})")
        for e in entries[:5]:
            # Truncate text for display
            preview = e["text"][:120].replace("\n", " ")
            print(f"    [{e['project']}] {preview}")
        if len(entries) > 5:
            print(f"    ... +{len(entries) - 5} more")
        print()

    # Cross-tag summary
    print("Per-project breakdown:")
    proj_counts = defaultdict(lambda: defaultdict(int))
    for e in all_tags:
        for tag in e["tags"]:
            proj_counts[e["project"]][tag] += 1
    for proj in sorted(proj_counts):
        tags_str = ", ".join(f"{t}={c}" for t, c in sorted(proj_counts[proj].items()))
        print(f"  {proj}: {tags_str}")


if __name__ == "__main__":
    main()
