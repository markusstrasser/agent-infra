#!/usr/bin/env python3
"""Daily git fetch for key OSS reference repos in ~/Projects/best/.

Fetches priority repos (AI vendor SDKs, docs, tools), reports new commits.
Designed to run as a morning-prep pipeline step or standalone.

Usage:
    uv run python3 scripts/best-sync.py              # fetch + report
    uv run python3 scripts/best-sync.py --all         # fetch ALL repos (slow)
    uv run python3 scripts/best-sync.py --output DIR  # write report to DIR
"""

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

BEST_DIR = Path.home() / "Projects" / "best"

# Priority repos — checked daily. Others only with --all.
PRIORITY_REPOS = {
    # Anthropic
    "anthropic-sdk-python",
    "claude-agent-sdk-python",
    "claude-agent-sdk-typescript",
    "claude-code",
    "claude-code-docs",
    "skills",
    # MCP
    "modelcontextprotocol",
    "fastmcp",
    # OpenAI
    "codex",
    # Google
    "adk-python",
}


def git_fetch_and_diff(repo_path: Path) -> dict:
    """Fetch remote and report new commits on default branch."""
    name = repo_path.name
    result = {"name": name, "path": str(repo_path)}

    try:
        # Get current HEAD
        old_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=30,
        ).stdout.strip()

        # Fetch
        fetch = subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=repo_path, capture_output=True, text=True, timeout=60,
        )
        if fetch.returncode != 0:
            result["status"] = "fetch_error"
            result["error"] = fetch.stderr.strip()[:200]
            return result

        # Find default remote branch
        remote_branch = None
        for candidate in ["origin/main", "origin/master"]:
            check = subprocess.run(
                ["git", "rev-parse", "--verify", candidate],
                cwd=repo_path, capture_output=True, text=True, timeout=10,
            )
            if check.returncode == 0:
                remote_branch = candidate
                break

        if not remote_branch:
            result["status"] = "no_remote_branch"
            return result

        # Count new commits
        new_head = subprocess.run(
            ["git", "rev-parse", remote_branch],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
        ).stdout.strip()

        if old_head == new_head:
            result["status"] = "up_to_date"
            result["head"] = old_head[:8]
            return result

        # Get new commit summaries
        log = subprocess.run(
            ["git", "log", "--oneline", f"{old_head}..{remote_branch}", "--max-count=20"],
            cwd=repo_path, capture_output=True, text=True, timeout=10,
        )
        commits = log.stdout.strip().split("\n") if log.stdout.strip() else []

        # Fast-forward merge (safe — we don't modify these repos)
        merge = subprocess.run(
            ["git", "merge", "--ff-only", remote_branch],
            cwd=repo_path, capture_output=True, text=True, timeout=30,
        )

        result["status"] = "updated" if merge.returncode == 0 else "ff_failed"
        result["old_head"] = old_head[:8]
        result["new_head"] = new_head[:8]
        result["new_commits"] = len(commits)
        result["commits"] = commits[:10]  # cap at 10 for readability
        if merge.returncode != 0:
            result["merge_error"] = merge.stderr.strip()[:200]

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]

    return result


def discover_repos(all_repos: bool) -> list[Path]:
    """Find git repos in best/ directory."""
    if not BEST_DIR.exists():
        return []

    repos = []
    for entry in sorted(BEST_DIR.iterdir()):
        if entry.is_dir() and (entry / ".git").exists():
            if all_repos or entry.name in PRIORITY_REPOS:
                repos.append(entry)
    return repos


def format_markdown(results: list[dict]) -> str:
    """Format sync results as markdown."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    updated = [r for r in results if r["status"] == "updated"]
    errors = [r for r in results if r["status"] in ("fetch_error", "timeout", "error")]

    lines = [f"# best/ Sync — {now}", ""]

    if updated:
        lines.append(f"## {len(updated)} repo(s) updated\n")
        for r in updated:
            lines.append(f"### {r['name']} ({r['old_head']} -> {r['new_head']}, {r['new_commits']} commits)")
            for c in r.get("commits", []):
                lines.append(f"- {c}")
            lines.append("")
    else:
        lines.append("All repos up to date.\n")

    if errors:
        lines.append(f"## {len(errors)} error(s)\n")
        for r in errors:
            lines.append(f"- **{r['name']}**: {r['status']} — {r.get('error', 'unknown')}")
        lines.append("")

    lines.append(f"Total: {len(results)} repos checked")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Sync best/ reference repos")
    parser.add_argument("--all", action="store_true", help="Fetch all repos, not just priority")
    parser.add_argument("--output", type=Path, help="Write report to directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    repos = discover_repos(args.all)
    if not repos:
        print(f"No repos found in {BEST_DIR}" + (" (use --all?)" if not args.all else ""))
        sys.exit(1)

    # Parallel fetch — 4 workers to avoid hammering GitHub
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(git_fetch_and_diff, r): r for r in repos}
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda r: r["name"])

    if args.json:
        now = datetime.now(timezone.utc).isoformat()
        print(json.dumps({"synced_at": now, "results": results}, indent=2))
    elif args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        md = format_markdown(results)
        (args.output / "best-sync.md").write_text(md)

        now = datetime.now(timezone.utc).isoformat()
        json_data = {"synced_at": now, "results": results}
        (args.output / "best-sync.json").write_text(
            json.dumps(json_data, indent=2) + "\n"
        )

        updated = [r for r in results if r["status"] == "updated"]
        if updated:
            print(f"{len(updated)} repo(s) updated:")
            for r in updated:
                print(f"  {r['name']}: {r['new_commits']} new commits")
        else:
            print(f"{len(results)} repos checked, all up to date")
    else:
        print(format_markdown(results))


if __name__ == "__main__":
    main()
