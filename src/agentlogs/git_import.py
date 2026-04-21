"""Import git commits with session attribution.

Populates `git_commits` and `git_commit_files` from `git log` across a set of
projects. Ported from the legacy `scripts/runlog.py git-import` command.

The Session-ID trailer (set by the prepare-commit-msg hook in each repo) is
the join key for `v_session_commits` / `v_fix_chains` / `v_session_durability`.
"""

from __future__ import annotations

import re
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path


PROJECTS_ROOT = Path.home() / "Projects"
DEFAULT_PROJECTS = ["agent-infra", "intel", "phenome", "genomics", "skills"]

FIX_PATTERNS = re.compile(r"\b(fix|repair|correct|patch|resolve|handle)\b", re.I)
REVERT_PATTERNS = re.compile(r"\b(revert|undo|drop|remove|retire)\b", re.I)
RULE_PATHS = re.compile(r"(CLAUDE\.md|rules/|hooks/|improvement-log)")
RESEARCH_PATHS = re.compile(r"(research/|decisions/)")
SCOPE_RE = re.compile(r"^\[([^\]]+)\]\s*")


def _classify_commit(subject: str, files: list[str]) -> str:
    if REVERT_PATTERNS.search(subject):
        return "revert"
    if FIX_PATTERNS.search(subject):
        return "fix"
    if any(RULE_PATHS.search(f) for f in files):
        return "rule"
    if any(RESEARCH_PATHS.search(f) for f in files):
        return "research"
    return "feature"


def _extract_scope(subject: str) -> str | None:
    m = SCOPE_RE.match(subject)
    return m.group(1) if m else None


def _parse_git_log(project: str, project_dir: Path, days: int) -> list[dict]:
    """Parse `git log --numstat` into structured commit records."""
    sep = "\x1f"  # unit separator — avoids collision with commit text
    fmt = sep.join(["%H", "%ai", "%an", "%s", "%(trailers:key=Session-ID,valueonly)"])
    cmd = [
        "git", "-C", str(project_dir), "log",
        f"--since={days} days ago",
        f"--format={fmt}",
        "--numstat",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return []

    commits: list[dict] = []
    current: dict | None = None
    for line in result.stdout.splitlines():
        if sep in line:
            if current:
                commits.append(current)
            parts = line.split(sep)
            # Strip tz offset from authored_at so julianday() comparisons work
            authored = parts[1][:19] if len(parts) > 1 else ""
            current = {
                "hash": parts[0],
                "project": project,
                "authored_at": authored,
                "author": parts[2] if len(parts) > 2 else "",
                "subject": parts[3] if len(parts) > 3 else "",
                "body": None,
                "session_id": (parts[4].strip() or None) if len(parts) > 4 else None,
                "scope": _extract_scope(parts[3] if len(parts) > 3 else ""),
                "files": [],
                "insertions": 0,
                "deletions": 0,
            }
        elif current and line.strip():
            numstat = line.split("\t", 2)
            if len(numstat) == 3:
                current["files"].append(numstat[2])
                try:
                    current["insertions"] += int(numstat[0])
                except ValueError:
                    pass
                try:
                    current["deletions"] += int(numstat[1])
                except ValueError:
                    pass
    if current:
        commits.append(current)

    # Classify + detect fix-of-fix (fix touching a file fixed within 3 days prior)
    for c in commits:
        c["commit_type"] = _classify_commit(c["subject"], c["files"])

    fix_commits = [c for c in commits if c["commit_type"] == "fix"]
    for i, fc in enumerate(fix_commits):
        fc_files = set(fc["files"])
        fc_date = fc["authored_at"][:10]
        for prior in fix_commits[i + 1:]:
            prior_date = prior["authored_at"][:10]
            try:
                gap = (datetime.fromisoformat(fc_date) - datetime.fromisoformat(prior_date)).days
            except ValueError:
                continue
            if gap > 3:
                break
            if fc_files & set(prior["files"]):
                fc["commit_type"] = "fix-of-fix"
                break

    return commits


def import_git_commits(
    db: sqlite3.Connection,
    *,
    projects: list[str] | None = None,
    days: int = 30,
) -> int:
    """Import git commits for the given projects. Returns commit count."""
    total = 0
    for project in (projects or DEFAULT_PROJECTS):
        project_dir = PROJECTS_ROOT / project
        if not (project_dir / ".git").is_dir():
            continue
        commits = _parse_git_log(project, project_dir, days)
        for c in commits:
            db.execute(
                """INSERT INTO git_commits
                   (hash, project, authored_at, author, subject, scope, commit_type,
                    session_id, body, files_changed, insertions, deletions)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(hash, project) DO UPDATE SET
                       authored_at = excluded.authored_at,
                       author = excluded.author,
                       subject = excluded.subject,
                       scope = excluded.scope,
                       commit_type = excluded.commit_type,
                       session_id = excluded.session_id,
                       body = excluded.body,
                       files_changed = excluded.files_changed,
                       insertions = excluded.insertions,
                       deletions = excluded.deletions""",
                (c["hash"], c["project"], c["authored_at"], c["author"],
                 c["subject"], c["scope"], c["commit_type"], c["session_id"],
                 c["body"], len(c["files"]), c["insertions"], c["deletions"]),
            )
            for f in c["files"]:
                db.execute(
                    """INSERT OR IGNORE INTO git_commit_files
                       (hash, project, path, insertions, deletions)
                       VALUES (?, ?, ?, NULL, NULL)""",
                    (c["hash"], c["project"], f),
                )
            total += 1
    return total
