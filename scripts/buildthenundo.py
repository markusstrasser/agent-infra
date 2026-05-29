#!/usr/bin/env python3
"""Build-then-undo detector — REPORT-ONLY git-history analyzer.

Detects the "build-then-undo" anti-pattern: an agent adds a file (or symbol) in
one commit, then deletes/reverts it shortly after within the SAME session. This
is the most recurrent failure in improvement-log.md (8th+ instance) with zero
enforcement today (Constitution P11: 10+ occurrences -> architecture).

NOT a live blocking hook. Scans git log and emits findings. Callable as:
    uv run python3 scripts/buildthenundo.py [--days N] [--json]
and importable:
    from buildthenundo import find_build_then_undo
    findings = find_build_then_undo(days=30)  # list[dict]

Each finding: {pattern, files, add_commit, delete_commit, session,
               lines_added, lines_deleted, confidence, evidence}

ALL git reads use `git --no-pager log --no-ext-diff` — external differs inject
control bytes (~/.claude/CLAUDE.md <environment>).
"""

# Gov-ID: hook:buildthenundo
# goal: detect build-then-undo recurrence (report-only)
# verifier: null
# blast_radius: local

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# --- Exclusion patterns (false positives) ---------------------------------
_TEST_RE = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.py)$|(^|/)tests?/")
_GENERATED_RE = re.compile(
    r"\.lock$|(^|/)_inventory\.md$|(^|/)(uv|poetry|package-lock)\.lock"
    r"|-index\.md$|_index\.md$|(^|/)__pycache__/"
)
# Commit messages signalling deliberate revert (NOT build-then-undo)
_REVERT_RE = re.compile(r"\b(revert|rollback|roll back|undo|back ?out)\b", re.I)


def _is_excluded(path: str) -> bool:
    return bool(_TEST_RE.search(path) or _GENERATED_RE.search(path))


# --- Git reading (single isolated fn — monkeypatch this in tests) ---------
def read_git_log(days: int) -> str:
    """Return raw `git log` output for the window. Sole git-touching point.

    Record format per commit (NUL-free, line-based):
        \x1e<sha>\x1f<session-id-or-empty>\x1f<subject>
        <name-status lines: A/D/M\tpath>
    """
    fmt = "\x1e%H\x1f%(trailers:key=Session-ID,valueonly,separator=)\x1f%s"
    out = subprocess.run(
        [
            "git", "--no-pager", "-C", str(REPO), "log", "--no-ext-diff",
            f"--since={days}.days.ago", "--name-status", "--no-renames",
            f"--format={fmt}",
        ],
        capture_output=True, text=True, check=True,
    )
    return out.stdout


def read_numstat(sha: str) -> dict[str, tuple[int, int]]:
    """Per-file (added, deleted) line counts for a commit. Isolated for tests."""
    out = subprocess.run(
        ["git", "--no-pager", "-C", str(REPO), "show", "--no-ext-diff",
         "--numstat", "--format=", "--no-renames", sha],
        capture_output=True, text=True, check=True,
    )
    res: dict[str, tuple[int, int]] = {}
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            a, d, path = parts
            res[path] = (0 if a == "-" else int(a), 0 if d == "-" else int(d))
    return res


# --- Parsing --------------------------------------------------------------
def _parse_commits(raw: str) -> list[dict]:
    """Parse read_git_log output into ordered commit records (newest first)."""
    commits: list[dict] = []
    cur: dict | None = None
    for line in raw.split("\n"):
        if line.startswith("\x1e"):
            sha, session, subject = (line[1:].split("\x1f") + ["", ""])[:3]
            cur = {
                "sha": sha, "session": session.strip(), "subject": subject,
                "added": [], "deleted": [], "modified": [],
            }
            commits.append(cur)
        elif cur is not None and "\t" in line:
            status, _, path = line.partition("\t")
            if status.startswith("A"):
                cur["added"].append(path)
            elif status.startswith("D"):
                cur["deleted"].append(path)
            elif status.startswith("M"):
                cur["modified"].append(path)
    return commits


# --- Core detection -------------------------------------------------------
def _detect(commits: list[dict]) -> list[dict]:
    """Find files added in one commit and deleted in a later same-session one."""
    findings: list[dict] = []
    # commits are newest-first; iterate oldest-first so add precedes delete.
    chrono = list(reversed(commits))
    # path -> add_commit_record (last add wins; cleared on delete)
    pending: dict[str, dict] = {}
    for c in chrono:
        is_revert = bool(_REVERT_RE.search(c["subject"]))
        # record adds (global, not session-scoped — cross-session is medium)
        for p in c["added"]:
            if not _is_excluded(p):
                pending[p] = c
        # check deletes against any earlier add
        for p in c["deleted"]:
            if _is_excluded(p):
                continue
            add_c = pending.pop(p, None)
            if add_c is None:
                continue
            # legitimate revert => skip
            if is_revert or _REVERT_RE.search(add_c["subject"]):
                continue
            same_session = bool(c["session"]) and c["session"] == add_c["session"]
            la = read_numstat(add_c["sha"]).get(p, (0, 0))[0]
            ld = read_numstat(c["sha"]).get(p, (0, 0))[1]
            findings.append({
                "pattern": "add_then_delete_file",
                "files": [p],
                "add_commit": add_c["sha"],
                "delete_commit": c["sha"],
                "session": c["session"] if same_session else None,
                "lines_added": la,
                "lines_deleted": ld,
                "confidence": "high" if same_session else "medium",
                "evidence": f"{add_c['sha'][:10]}..{c['sha'][:10]} {p}",
            })
    return findings


def find_build_then_undo(days: int = 30) -> list[dict]:
    """Scan the last `days` of git history for build-then-undo findings."""
    return _detect(_parse_commits(read_git_log(days)))


# --- CLI ------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Report-only build-then-undo detector")
    ap.add_argument("--days", type=int, default=30, help="history window (default 30)")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    findings = find_build_then_undo(args.days)

    if args.json:
        print(json.dumps(findings, indent=2))
        return 0

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from common.console import con
        header, ok, warn = con.header, con.ok, con.warn
    except Exception:  # console is optional
        def header(s): print(f"\n[{s}]")
        def ok(s): print(f"  + {s}")
        def warn(s): print(f"  ! {s}")

    header(f"build-then-undo scan (last {args.days}d)")
    if not findings:
        ok("no build-then-undo patterns found")
        return 0
    hi = sum(1 for f in findings if f["confidence"] == "high")
    warn(f"{len(findings)} finding(s) — {hi} high-confidence")
    for f in findings:
        print(
            f"  [{f['confidence']}] {f['files'][0]}\n"
            f"        +{f['lines_added']} (add {f['add_commit'][:10]})"
            f" -> -{f['lines_deleted']} (del {f['delete_commit'][:10]})"
            f" session={f['session'] or 'n/a'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
