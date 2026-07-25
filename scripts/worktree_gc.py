#!/usr/bin/env python3
"""Prune stale agent git worktrees across Projects.

Git never removes worktrees when a branch merges — `claude --worktree`, Cursor
best-of-n, and autoresearch only call `git worktree add`. Session end / merge do
not call `git worktree remove`, so `.claude/worktrees/` accumulates duplicate
venvs and recordings.

This removes worktree *directories* only. Branches survive unless --prune-branches.

Safety classes (audit):
  SAFE           — ahead==0 (already on main), clean working tree
  DUP            — ahead>0 but every patch already on main (cherry-picked/rebased,
                   then stranded); clean. Reap with --include-unmerged; the branch
                   is pure cruft, prunable with --prune-branches.
  unmerged       — ahead>0: GENUINE unique commits on branch; NEVER removed by default
  stale-dirty    — ahead==0 but uncommitted edits; needs --force-stale
  skip-dirty     — ahead>0 AND uncommitted edits; never removed without --force-all

Audit also prints last-commit age (currency signal — branches weeks behind = cruft).

apply (default): SAFE only — stale merged trees, clean
apply --include-unmerged: also remove unmerged worktrees with NO local edits
  (branch + commits are preserved; only the directory/venv goes)
apply --force-stale: also stale (ahead==0) with dirty trees (discards wt edits)
apply --force-all: everything except --keep (dangerous)

Evidence: standing #g metafix — worktree leak is harness hygiene, not telos.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from config import PROJECT_ROOTS

PROJECTS_HOME = Path.home() / "Projects"
SKIP_PATH_SUBSTR = ("factory", "-factory")


@dataclass
class WorktreeRow:
    repo: str
    repo_root: Path
    path: Path
    branch: str | None
    ahead: int
    tracked_dirty: int
    size: str
    ancestor: bool  # detached HEAD is ancestor of main
    age: str = "?"  # relative last-commit date (currency signal)
    dup: bool = False  # ahead>0 but every patch already on main (git cherry all '-')
    held: int = 0  # processes doing real work whose cwd is inside this worktree
    daemon_held: int = 0  # detached pollers holding it forever by design (see DAEMON_SCRIPTS)
    daemon_pids: tuple[int, ...] = ()  # their exact PIDs, so a kill never needs pkill -f

    @property
    def stale(self) -> bool:
        return self.ahead == 0

    @property
    def safe(self) -> bool:
        """Stale on main, no local edits, and no process working in it.

        The liveness term is not decoration. Until 2026-07-25 this property was git
        state + age only, and on that day it called SIX worktrees SAFE — the default
        apply set — while `lsof` showed a live python3 holding each one. Crash-loop
        watchers and remat lanes poll on a timer and write nothing between polls, so a
        clean tree with an old mtime is exactly what a *working* agent looks like.
        """
        if self.held or self.daemon_held:
            return False
        if self.tracked_dirty:
            return False
        if self.branch is None:
            return self.ancestor
        return self.ahead == 0

    @property
    def unmerged_clean(self) -> bool:
        return self.ahead > 0 and self.tracked_dirty == 0 and self.branch is not None

    def classify(self) -> str:
        # DUP: commits exist (ahead>0) but their patches are already on main
        # (cherry-picked / rebased) — the heretic-fixes-stranded case. Safe to
        # reap, but surfaced distinctly so the operator reaps with confidence
        # rather than mistaking it for genuine unmerged work.
        # HELD dominates every other verdict. A process working in the directory makes
        # it un-reclaimable regardless of how clean or how old its git state looks.
        if self.held:
            return "HELD"
        # DAEMON is HELD's honest sibling: the only thing here is a detached poller that
        # will hold this cwd until someone kills it, so "live process" is true but
        # "someone is working here" is false. Kept OUT of every automatic apply set —
        # this only stops the operator reading an orphan as an agent, and supplies the
        # exact PID to kill. Reaping it is a deliberate, separate act.
        if self.daemon_held:
            return "DAEMON"
        if self.dup and not self.tracked_dirty:
            return "DUP"
        if self.safe:
            return "SAFE"
        if self.unmerged_clean:
            return "unmerged"
        if self.stale and self.tracked_dirty:
            return "stale-dirty"
        return "skip-dirty"


def run(
    cmd: list[str], cwd: Path | None = None, check: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


# Self-relaunching detached pollers that hold a worktree cwd FOREVER by design, whether
# or not anyone is working there. Matched on the exact script path in the full command
# line — never on the interpreter. Matching `python3` would reopen the precise hole the
# liveness gate exists to close; matching `scripts/modal_crash_loop_watcher.py` cannot,
# because an interactive agent is `claude`, a shell, a git process, or a DIFFERENT
# script, and none of those can collide with an exact path.
DAEMON_SCRIPTS: frozenset[str] = frozenset({"scripts/modal_crash_loop_watcher.py"})


def live_cwd_holders() -> dict[str, list[int]]:
    """Map every process cwd on the box to the PIDs there, in ONE lsof call.

    One call rather than one per worktree: 39 worktrees would otherwise mean 39 lsof
    invocations, and an audit that is slow gets run with the flag that skips it. `-d cwd`
    only — never `+D`, which walks every file in the tree and takes minutes on repos this
    size, which is why liveness got skipped here in the first place.

    `-F pn` is field output — `p<pid>` then `n<path>` — so this parses PIDs exactly
    instead of substring-matching a human-formatted table. The PID is what lets a caller
    ask *what* is holding a directory rather than only *how many*.

    Returns {} when lsof is unavailable. That is the dangerous direction, so an empty
    result means "unknown", never "nothing is running" — see the caller.
    """
    try:
        result = subprocess.run(
            [
                "lsof",
                "-a",
                "-d",
                "cwd",
                "-F",
                "pn",
                "-c",
                "python3",
                "-c",
                "bash",
                "-c",
                "git",
                "-c",
                "node",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    holders: dict[str, list[int]] = {}
    pid: int | None = None
    for line in result.stdout.splitlines():
        if line.startswith("p"):
            try:
                pid = int(line[1:])
            except ValueError:
                pid = None
        elif line.startswith("n") and pid is not None:
            holders.setdefault(line[1:], []).append(pid)
    return holders


def daemon_pids(pids: set[int]) -> set[int]:
    """Which of ``pids`` are known detached daemons, by exact script path.

    One batched `ps` for every candidate — a per-PID call would reintroduce the
    fan-out this module already avoids for lsof. A PID that has exited between the
    lsof and the ps simply does not come back, which is the safe direction: unknown
    stays counted as a live holder.
    """
    if not pids:
        return set()
    try:
        result = subprocess.run(
            ["ps", "-o", "pid=,command=", "-p", ",".join(str(p) for p in sorted(pids))],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    found: set[int] = set()
    for line in result.stdout.splitlines():
        head, _, command = line.strip().partition(" ")
        try:
            candidate = int(head)
        except ValueError:
            continue
        if any(script in command for script in DAEMON_SCRIPTS):
            found.add(candidate)
    return found


def holders_for(path: Path, holders: dict[str, list[int]]) -> list[int]:
    """PIDs working inside ``path``, including nested subdirectories."""
    needle = str(path)
    out: list[int] = []
    for cwd, pids in holders.items():
        if cwd == needle or cwd.startswith(needle + "/"):
            out.extend(pids)
    return out


def is_main_checkout(repo: Path) -> bool:
    """Skip linked worktrees — they duplicate .claude/worktrees/ paths."""
    return (repo / ".git").is_dir()


def repo_roots(explicit: list[str] | None, all_projects: bool) -> list[Path]:
    if explicit:
        roots = [Path(p).expanduser().resolve() for p in explicit]
    elif all_projects:
        roots = sorted(p.resolve() for p in PROJECTS_HOME.iterdir() if (p / ".git").exists())
    else:
        roots = [
            PROJECT_ROOTS["agent-infra"],
            *[PROJECT_ROOTS[k] for k in ("genomics", "personal")],
        ]
    return [r for r in roots if is_main_checkout(r)]


def parse_worktrees(repo: Path) -> list[tuple[Path, str | None]]:
    out = run(["git", "worktree", "list", "--porcelain"], cwd=repo)
    if out.returncode != 0:
        return []
    rows: list[tuple[Path, str | None]] = []
    wt: Path | None = None
    branch: str | None = None
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            if wt is not None:
                rows.append((wt, branch))
            wt = Path(line.split(" ", 1)[1])
            branch = None
        elif line.startswith("branch "):
            branch = line.split(" ", 1)[1].replace("refs/heads/", "")
        elif line == "detached":
            branch = None
    if wt is not None:
        rows.append((wt, branch))
    return [(p, b) for p, b in rows if p.resolve() != repo.resolve()]


def ahead_of_main(repo: Path, branch: str) -> int:
    r = run(["git", "rev-list", "--count", f"main..{branch}"], cwd=repo)
    if r.returncode != 0:
        r = run(["git", "rev-list", "--count", f"master..{branch}"], cwd=repo)
    try:
        return int(r.stdout.strip() or "0")
    except ValueError:
        return -1


def is_ancestor(repo: Path, sha: str) -> bool:
    for base in ("main", "master"):
        r = run(["git", "merge-base", "--is-ancestor", sha, base], cwd=repo)
        if r.returncode == 0:
            return True
    return False


def last_commit_rel(repo: Path, ref: str) -> str:
    """Relative age of ref's tip (currency signal: '2 days ago', '5 weeks ago')."""
    r = run(["git", "log", "-1", "--format=%cr", ref], cwd=repo)
    return r.stdout.strip() or "?"


def all_patches_on_main(repo: Path, branch: str) -> bool:
    """True if every commit on `branch` has an equivalent patch already on main.

    `git cherry main <branch>` prints '- <sha>' for commits whose patch is
    already upstream, '+ <sha>' for genuinely-unmerged ones. All '-' (and at
    least one line) => the branch is a pure duplicate, safe to reap even though
    `ahead>0`. This is the cherry-picked/rebased-then-stranded case.
    """
    for base in ("main", "master"):
        r = run(["git", "cherry", base, branch], cwd=repo)
        if r.returncode != 0:
            continue
        lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        if not lines:
            return False
        return all(ln.startswith("-") for ln in lines)
    return False


def audit_repo(repo: Path, with_size: bool = True) -> list[WorktreeRow]:
    name = repo.name
    rows: list[WorktreeRow] = []
    for wt, branch in parse_worktrees(repo):
        if any(s in str(wt) for s in SKIP_PATH_SUBSTR):
            continue
        st = run(["git", "status", "--porcelain"], cwd=wt)
        tracked_dirty = sum(1 for ln in st.stdout.splitlines() if not ln.startswith("??"))
        # `du` is the slow part; skip it on the cheap --check path (size irrelevant to the flag).
        size = run(["du", "-sh", str(wt)]).stdout.split()[0] if (with_size and wt.exists()) else "?"
        dup = False
        if branch:
            ahead = ahead_of_main(repo, branch)
            ancestor = ahead == 0
            age = last_commit_rel(repo, branch)
            if ahead > 0:
                dup = all_patches_on_main(repo, branch)
        else:
            sha = run(["git", "rev-parse", "HEAD"], cwd=wt).stdout.strip()
            ancestor = is_ancestor(repo, sha)
            ahead = 0 if ancestor else -1
            age = last_commit_rel(repo, sha) if sha else "?"
        rows.append(
            WorktreeRow(
                repo=name,
                repo_root=repo,
                path=wt,
                branch=branch,
                ahead=ahead,
                tracked_dirty=tracked_dirty,
                size=size,
                ancestor=ancestor,
                age=age,
                dup=dup,
            )
        )
    return rows


def commit_preview(repo: Path, branch: str, n: int = 2) -> str:
    r = run(["git", "log", "--oneline", f"-{n}", f"main..{branch}"], cwd=repo)
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    return " | ".join(lines) if lines else ""


def should_remove(
    row: WorktreeRow,
    include_unmerged: bool,
    force_stale: bool,
    force_all: bool,
    keep: set[str],
) -> bool:
    if any(k in str(row.path) for k in keep):
        return False
    # Held beats every force flag, --force-all included. On 2026-07-25 the six worktrees
    # this check now protects were all in the default apply set, each with a live
    # process; the 2026-07-24 near-miss was the same class. Nothing about "remove all"
    # implies "remove out from under a running agent" — kill the process first.
    if row.held:
        return False
    # A daemon-only hold is not work, but removing a directory a live process is chdir'd
    # into is still not something a force flag should do silently. Kill the printed PID
    # first, then the row reclassifies to SAFE on the next run and reaps normally.
    if row.daemon_held:
        return False
    if force_all:
        return True
    if row.safe:
        return True
    if include_unmerged and row.unmerged_clean:
        return True
    if force_stale and row.stale:
        return True
    return False


def remove_worktree(repo: Path, wt: Path) -> None:
    run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo, check=True)
    run(["git", "worktree", "prune"], cwd=repo)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("mode", nargs="?", default="audit", choices=("audit", "apply"))
    ap.add_argument(
        "--repo",
        action="append",
        help="repo path (repeatable); default agent-infra+genomics+personal",
    )
    ap.add_argument("--all-projects", action="store_true", help="scan all ~/Projects/* git repos")
    ap.add_argument(
        "--include-unmerged",
        action="store_true",
        help="remove unmerged worktrees with no local edits (branch kept)",
    )
    ap.add_argument(
        "--force-stale", action="store_true", help="remove ahead==0 worktrees even with local edits"
    )
    ap.add_argument(
        "--force-all", action="store_true", help="remove all worktrees except --keep matches"
    )
    ap.add_argument(
        "--keep", action="append", default=[], help="substring; skip paths containing this"
    )
    ap.add_argument(
        "--prune-branches", action="store_true", help="delete branch after remove when ahead==0"
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="cheap advisory flag for the control plane: print STRANDED line iff "
        "genuine-unmerged or reapable-DUP branches exist (skips du). Always exit 0.",
    )
    ap.add_argument("--no-size", action="store_true", help="skip du -sh (faster audit)")
    args = ap.parse_args()

    with_size = not (args.no_size or args.check)
    # --check defaults to all-projects so the hub surfaces stranded work in every repo.
    repos = repo_roots(args.repo, args.all_projects or args.check)
    all_rows: list[WorktreeRow] = []
    for repo in repos:
        if not (repo / ".git").exists():
            continue
        all_rows.extend(audit_repo(repo, with_size=with_size))

    # Liveness last, in one lsof call for every row, so it also gates --check. The
    # daemon split needs one further batched `ps` over only the PIDs lsof actually
    # found, so the cost is two calls total regardless of worktree count.
    cwd_holders = live_cwd_holders()
    per_row = {row.path: holders_for(row.path, cwd_holders) for row in all_rows}
    daemons = daemon_pids({pid for pids in per_row.values() for pid in pids})
    for row in all_rows:
        pids = per_row[row.path]
        row.daemon_pids = tuple(sorted(pid for pid in pids if pid in daemons))
        row.daemon_held = len(row.daemon_pids)
        row.held = len(pids) - row.daemon_held

    if args.check:
        # 3 buckets, all carrying unmerged COMMITS (so never a fresh active checkout):
        #   LAND   = unmerged clean      INSPECT = skip-dirty (commits + uncommitted)
        #   REAP   = DUP (patches on main)
        bucket = {"unmerged": "LAND", "DUP": "REAP", "skip-dirty": "INSPECT"}
        stranded = [r for r in all_rows if r.classify() in bucket]
        if not stranded:
            return 0  # silent when clean — no drift flag
        from collections import Counter

        counts = Counter(bucket[r.classify()] for r in stranded)
        bits = [f"{counts[b]} to {b}" for b in ("LAND", "INSPECT", "REAP") if counts.get(b)]
        print(
            f"STRANDED worktree branches: {', '.join(bits)} — `just worktree-gc audit --all-projects`"
        )
        for r in sorted(stranded, key=lambda x: bucket[x.classify()]):
            print(
                f"  [{bucket[r.classify()]:7}] {r.repo}/{r.branch}  ahead={r.ahead} dirty={r.tracked_dirty} age={r.age}"
            )
        return 0

    keep = set(args.keep)
    to_remove = [
        r
        for r in all_rows
        if should_remove(r, args.include_unmerged, args.force_stale, args.force_all, keep)
    ]

    for row in all_rows:
        cls = row.classify()
        mark = "→" if row in to_remove else " "
        br = row.branch or "(detached)"
        extra = ""
        if row.held:
            extra = f"  ← {row.held} LIVE process(es) working here"
        elif row.daemon_held:
            # Print the exact PID: the whole point is that reclaiming this needs a
            # targeted kill, and a substring `pkill -f` on a shared box has already
            # killed a healthy job here twice.
            pids = " ".join(str(p) for p in row.daemon_pids)
            extra = f"  ← orphaned poller only, no work — reclaim after: kill {pids}"
        elif row.branch and row.ahead > 0:
            extra = f"  commits: {commit_preview(row.repo_root, row.branch)}"
        print(
            f"{mark} {row.repo:15} {br:42} ahead={row.ahead:>3} "
            f"dirty={row.tracked_dirty:>3} {cls:9} {row.age:>14} {row.size:>6}  {row.path}{extra}"
        )

    if not all_rows:
        print("(no extra worktrees)")
        return 0

    if args.mode == "audit":
        n_safe = sum(1 for r in all_rows if r.safe)
        n_dup = sum(1 for r in all_rows if r.classify() == "DUP")
        n_unmerged = sum(1 for r in all_rows if r.classify() == "unmerged")
        print(f"\n{len(all_rows)} worktrees; {n_safe} stale+clean (default apply)")
        if n_dup:
            print(
                f"  {n_dup} DUP (patches already on main) — reap: --include-unmerged --prune-branches"
            )
        if n_unmerged:
            print(
                f"  {n_unmerged} GENUINE unmerged+clean — LAND these; --include-unmerged drops dir but keeps branch"
            )
        print("Run: just worktree-gc apply --all-projects")
        return 0

    removed = 0
    seen: set[Path] = set()
    for row in to_remove:
        if row.path in seen:
            continue
        seen.add(row.path)
        try:
            remove_worktree(row.repo_root, row.path)
            print(f"removed {row.path}")
            removed += 1
            if args.prune_branches and row.branch and (row.stale or row.dup):
                run(["git", "branch", "-D", row.branch], cwd=row.repo_root)
                print(f"  branch -D {row.branch}")
        except subprocess.CalledProcessError as e:
            print(f"FAIL {row.path}: {e.stderr or e}", file=sys.stderr)

    print(f"\nremoved {removed}/{len(to_remove)} worktrees")
    return 0


if __name__ == "__main__":
    sys.exit(main())
