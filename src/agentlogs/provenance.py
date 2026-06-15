"""Code↔conversation provenance — the bidirectional link.

`who`    : a code line/range → the session, model, and intent that authored it
           (`git blame` → Session-ID trailer → agentlogs join).
`whence` : a session → the code it produced (`v_session_commits`).

Reconstruct-on-demand over git + a READ-ONLY join to agentlogs
(`git_commits` / `v_session_commits` / `sessions`). No new store, no index.
See `decisions/2026-06-15-code-conversation-link.md`.

Honest degradation (never fabricate):
  - line has no Session-ID trailer            → session=unknown
  - trailer present but session not indexed    → session=<sid> model=unknown (pre-index)
  - blame crossed a `.git-blame-ignore-revs`   → ignore-revs honored (refactor-wash skipped)

Caveats baked into the model (see ADR): blame is *last-touch*, not origin
(use `--history`); a line's model is the session's MAIN-loop model (subagent
authorship is not line-mappable); effort is not recorded anywhere → always `n/a`.
"""

from __future__ import annotations

import re
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path

# porcelain blame header: "<40-hex> <orig_lineno> <final_lineno> [<group_size>]"
_BLAME_HDR = re.compile(r"^([0-9a-f]{40}) \d+ (\d+)")
_SPEC = re.compile(r"^(.*?):(\d+)(?:-(\d+))?$")


@dataclass
class Hunk:
    start: int
    end: int
    sha: str
    authored_at: str | None = None
    session_id: str | None = None      # the Session-ID trailer value
    session_uuid: str | None = None
    model: str | None = None
    scope: str | None = None
    subject: str | None = None
    note: str | None = None            # 'pre-index' | 'no-trailer'


def parse_file_spec(spec: str) -> tuple[str, int | None, int | None]:
    """'f.py:10-20' → ('f.py',10,20); 'f.py:10' → ('f.py',10,10); 'f.py' → ('f.py',None,None)."""
    m = _SPEC.match(spec)
    if not m:
        return spec, None, None
    return m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else int(m.group(2))


def _git(repo: Path, *args: str, timeout: float = 30.0) -> str:
    res = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, timeout=timeout,
    )
    if res.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {res.stderr.strip() or res.returncode}")
    return res.stdout


def repo_root(path: Path) -> Path:
    base = path if path.is_dir() else path.parent
    return Path(_git(base, "rev-parse", "--show-toplevel").strip())


def _blame_lines(repo: Path, path: str, start: int | None, end: int | None) -> list[tuple[int, str]]:
    """[(final_lineno, sha)] for the requested range.

    Plain `git blame` already walks the file's rename history (no `--follow` — that is
    a git-log flag). Honors `.git-blame-ignore-revs` so refactor-wash commits are
    skipped when attributing.
    """
    args = ["blame", "--porcelain"]
    ignore = repo / ".git-blame-ignore-revs"
    if ignore.is_file():
        args += ["--ignore-revs-file", str(ignore)]
    if start is not None:
        args += ["-L", f"{start},{end}"]
    args += ["--", path]
    out = _git(repo, *args)
    lines: list[tuple[int, str]] = []
    for line in out.splitlines():
        m = _BLAME_HDR.match(line)
        if m:
            lines.append((int(m.group(2)), m.group(1)))
    return lines


def _group(lines: list[tuple[int, str]]) -> list[Hunk]:
    """Collapse consecutive same-sha lines into hunks."""
    hunks: list[Hunk] = []
    for lineno, sha in sorted(lines):
        if hunks and hunks[-1].sha == sha and lineno == hunks[-1].end + 1:
            hunks[-1].end = lineno
        else:
            hunks.append(Hunk(start=lineno, end=lineno, sha=sha))
    return hunks


def _enrich(db: sqlite3.Connection, repo: Path, project: str, h: Hunk) -> None:
    """Resolve sha → session/model. DB first (git_commits/sessions), then git fallback."""
    row = db.execute(
        """SELECT gc.session_id, gc.scope, gc.subject, gc.authored_at,
                  s.session_uuid, s.model
           FROM git_commits gc
           LEFT JOIN sessions s
             ON gc.session_id IS NOT NULL
            AND (gc.session_id = s.vendor_session_id
                 OR gc.session_id = s.synthetic_session_key)
           WHERE gc.hash = ? AND gc.project = ?
           LIMIT 1""",
        (h.sha, project),
    ).fetchone()
    if row is not None:
        h.session_id, h.scope, h.subject, h.authored_at = (
            row["session_id"], row["scope"], row["subject"], row["authored_at"])
        h.session_uuid, h.model = row["session_uuid"], row["model"]
        if h.session_id and h.session_uuid is None:
            h.note = "pre-index"      # trailer present, session not indexed
        elif not h.session_id:
            h.note = "no-trailer"
        return

    # Not in git_commits (predates the import --since window): read trailer from git.
    h.authored_at = _git(repo, "show", "-s", "--format=%ci", h.sha).strip()[:19] or None
    h.subject = _git(repo, "show", "-s", "--format=%s", h.sha).strip() or None
    sid = _git(repo, "show", "-s",
               "--format=%(trailers:key=Session-ID,valueonly)", h.sha).strip() or None
    h.session_id = sid
    if not sid:
        h.note = "no-trailer"
        return
    srow = db.execute(
        """SELECT session_uuid, model FROM sessions
           WHERE vendor_session_id = ? OR synthetic_session_key = ? LIMIT 1""",
        (sid, sid),
    ).fetchone()
    if srow is not None:
        h.session_uuid, h.model = srow["session_uuid"], srow["model"]
    else:
        h.note = "pre-index"


def who(db: sqlite3.Connection, spec: str) -> tuple[str, list[Hunk]]:
    """Code → session. Returns (resolved_path, hunks)."""
    path, start, end = parse_file_spec(spec)
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    repo = repo_root(p)
    project = repo.name
    rel = str(p.resolve().relative_to(repo))
    hunks = _group(_blame_lines(repo, rel, start, end))
    for h in hunks:
        _enrich(db, repo, project, h)
    return rel, hunks


def history(db: sqlite3.Connection, spec: str) -> tuple[str, list[Hunk]]:
    """Code → EVERY session in a line range's lineage (oldest→newest).

    The honest answer to "who originated this": `git log -L start,end:file` returns the
    full set of commits that shaped the range, not just blame's last-touch.
    """
    path, start, end = parse_file_spec(spec)
    if start is None or end is None:
        raise ValueError("--history requires a line range, e.g. file.py:10-20")
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    repo = repo_root(p)
    project = repo.name
    rel = str(p.resolve().relative_to(repo))
    out = _git(repo, "log", f"-L{start},{end}:{rel}", "--format=%H", "--no-patch")
    seen: set[str] = set()
    hunks: list[Hunk] = []
    for sha in out.splitlines():
        sha = sha.strip()
        if len(sha) == 40 and sha not in seen:
            seen.add(sha)
            h = Hunk(start=start, end=end, sha=sha)
            _enrich(db, repo, project, h)
            hunks.append(h)
    hunks.reverse()   # git log is newest-first; lineage reads oldest→newest
    return rel, hunks


PROJECTS_ROOT = Path.home() / "Projects"
_DEFAULT_PROJECTS = ["agent-infra", "intel", "phenome", "genomics", "skills"]


def _candidate_repos(project_slug: str | None) -> list[Path]:
    """Repos to grep for a session's commits. A session belongs to one project, so
    scope to its project_slug when known; else scan the default set."""
    if project_slug:
        p = PROJECTS_ROOT / project_slug
        if (p / ".git").is_dir():
            return [p]
    return [PROJECTS_ROOT / n for n in _DEFAULT_PROJECTS if (PROJECTS_ROOT / n / ".git").is_dir()]


def whence(db: sqlite3.Connection, sid: str) -> tuple[sqlite3.Row | None, list[dict]]:
    """Session → the code it produced. (session_header, commit_dicts).

    Commits are reconstructed LIVE from `git log --grep` (always fresh) — the
    `git_commits` import table is a cache that can be stale (it was 2 months behind
    when this was written), and reading a stale cache silently under-reports. The DB
    is used only for the session metadata header (not in git).
    """
    sess = db.execute(
        """SELECT session_uuid, vendor_session_id, synthetic_session_key, vendor,
                  model, project_slug, start_ts, duration_min, transcript_lines
           FROM sessions
           WHERE vendor_session_id = ? OR synthetic_session_key = ? OR session_uuid = ?
           LIMIT 1""",
        (sid, sid, sid),
    ).fetchone()

    # The trailer in commits is the RAW id (not the vendor:-namespaced session_uuid).
    grep_ids = {sid}
    if sess is not None:
        for k in ("vendor_session_id", "synthetic_session_key"):
            if sess[k]:
                grep_ids.add(sess[k])

    slug = sess["project_slug"] if sess is not None else None
    commits: dict[str, dict] = {}
    for repo in _candidate_repos(slug):
        for gid in grep_ids:
            out = _git(repo, "log", "--all", "-F", f"--grep=Session-ID: {gid}",
                       "--no-merges", "--format=%H%x1f%cI%x1f%s", "--numstat")
            cur: dict | None = None
            for line in out.splitlines():
                if "\x1f" in line:
                    parts = line.split("\x1f")
                    cur = {"hash": parts[0][:8], "project": repo.name,
                           "authored_at": parts[1][:10], "subject": parts[2][:56],
                           "files": 0, "insertions": 0, "deletions": 0}
                    commits[parts[0]] = cur
                elif cur is not None and "\t" in line:
                    ins, dele, _ = (line.split("\t", 2) + ["", "", ""])[:3]
                    cur["files"] += 1
                    cur["insertions"] += int(ins) if ins.isdigit() else 0
                    cur["deletions"] += int(dele) if dele.isdigit() else 0
    rows = sorted(commits.values(), key=lambda c: c["authored_at"])
    return sess, rows
