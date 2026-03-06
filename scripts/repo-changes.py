#!/usr/bin/env python3
"""Recent changes grouped by area — what changed and where.

Combines git log with diffstat to show an agent what's been happening
in a repo without reading every commit.

Usage:
  repo-changes.py <path>                  # last 7 days
  repo-changes.py <path> --days 3         # last 3 days
  repo-changes.py <path> --commits 20     # last 20 commits
  repo-changes.py <path> --by-area        # group by directory
  repo-changes.py <path> --hot            # most-changed files
"""
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def git_log(repo: Path, days: int | None = None, max_commits: int | None = None) -> list[dict]:
    """Get recent commits with file stats."""
    cmd = ["git", "-C", str(repo), "log", "--format=%H|%ai|%an|%s", "--numstat"]
    if days:
        cmd.append(f"--since={days} days ago")
    if max_commits:
        cmd.extend(["-n", str(max_commits)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    commits = []
    current = None
    for line in result.stdout.splitlines():
        if "|" in line and not line.startswith(" ") and len(line.split("|")) == 4:
            parts = line.split("|", 3)
            if len(parts[0]) == 40:  # SHA
                if current:
                    commits.append(current)
                current = {
                    "sha": parts[0][:8],
                    "date": parts[1].strip()[:10],
                    "author": parts[2].strip(),
                    "subject": parts[3].strip(),
                    "files": [],
                }
                continue
        if current and line.strip() and "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 3:
                added = parts[0] if parts[0] != "-" else "0"
                removed = parts[1] if parts[1] != "-" else "0"
                filepath = parts[2]
                current["files"].append({
                    "path": filepath,
                    "added": int(added),
                    "removed": int(removed),
                })

    if current:
        commits.append(current)
    return commits


def cmd_default(repo: Path, commits: list[dict]):
    """Chronological commit list with changed files."""
    print(f"# Recent changes: {repo.name}")
    print(f"# {len(commits)} commits\n")

    for c in commits:
        file_summary = ", ".join(f["path"].split("/")[-1] for f in c["files"][:5])
        if len(c["files"]) > 5:
            file_summary += f" +{len(c['files']) - 5} more"
        total_delta = sum(f["added"] + f["removed"] for f in c["files"])
        print(f"  {c['sha']}  {c['date']}  (+{total_delta:>4} lines)  {c['subject']}")
        if c["files"]:
            print(f"           {file_summary}")


def cmd_by_area(repo: Path, commits: list[dict]):
    """Group changes by top-level directory."""
    print(f"# Changes by area: {repo.name}")
    print(f"# {len(commits)} commits\n")

    areas = defaultdict(lambda: {"commits": set(), "files": set(), "added": 0, "removed": 0})
    for c in commits:
        for f in c["files"]:
            parts = f["path"].split("/")
            area = parts[0] if len(parts) > 1 else "(root)"
            areas[area]["commits"].add(c["sha"])
            areas[area]["files"].add(f["path"])
            areas[area]["added"] += f["added"]
            areas[area]["removed"] += f["removed"]

    for area in sorted(areas, key=lambda a: areas[a]["added"] + areas[a]["removed"], reverse=True):
        info = areas[area]
        print(f"  {area}/")
        print(f"    {len(info['commits'])} commits, {len(info['files'])} files, +{info['added']}/-{info['removed']} lines")
        # Show most-changed files in this area
        file_changes = defaultdict(int)
        for c in commits:
            for f in c["files"]:
                p = f["path"]
                if p.startswith(area + "/") or (area == "(root)" and "/" not in p):
                    file_changes[p] += f["added"] + f["removed"]
        top_files = sorted(file_changes.items(), key=lambda x: -x[1])[:5]
        for fp, delta in top_files:
            print(f"      {fp.split('/')[-1]:<35} {delta:>5} lines changed")
        print()


def cmd_hot(repo: Path, commits: list[dict]):
    """Most-changed files (hotspots)."""
    print(f"# Hotspots: {repo.name}")
    print(f"# {len(commits)} commits\n")

    file_stats = defaultdict(lambda: {"commits": 0, "added": 0, "removed": 0})
    for c in commits:
        for f in c["files"]:
            file_stats[f["path"]]["commits"] += 1
            file_stats[f["path"]]["added"] += f["added"]
            file_stats[f["path"]]["removed"] += f["removed"]

    ranked = sorted(
        file_stats.items(),
        key=lambda x: x[1]["commits"] * (x[1]["added"] + x[1]["removed"]),
        reverse=True,
    )

    print(f"  {'File':<50} {'Commits':>7} {'Added':>7} {'Removed':>7}")
    print(f"  {'-'*50} {'-'*7} {'-'*7} {'-'*7}")
    for filepath, stats in ranked[:20]:
        # Shorten path if needed
        display = filepath if len(filepath) <= 50 else "..." + filepath[-(47):]
        print(f"  {display:<50} {stats['commits']:>7} {stats['added']:>7} {stats['removed']:>7}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="Git repository path")
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--commits", type=int, default=None, help="Limit to N commits")
    parser.add_argument("--by-area", action="store_true", help="Group by top-level directory")
    parser.add_argument("--hot", action="store_true", help="Show most-changed files")
    args = parser.parse_args()

    repo = args.path.resolve()
    if not (repo / ".git").exists() and not repo.is_file():
        print(f"Not a git repo: {repo}")
        sys.exit(1)

    commits = git_log(repo, days=args.days, max_commits=args.commits)
    if not commits:
        print(f"No commits found in the last {args.days} days")
        return

    if args.by_area:
        cmd_by_area(repo, commits)
    elif args.hot:
        cmd_hot(repo, commits)
    else:
        cmd_default(repo, commits)


if __name__ == "__main__":
    main()
