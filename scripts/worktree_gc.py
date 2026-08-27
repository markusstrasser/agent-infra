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
import shutil
import stat
import subprocess
import sys
from collections.abc import Iterator
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
    daemon_held: int = (
        0  # detached pollers holding it forever by design (see DAEMON_SCRIPTS)
    )
    daemon_pids: tuple[
        int, ...
    ] = ()  # their exact PIDs, so a kill never needs pkill -f
    # Untracked, non-ignored files. A lane's first hour of work is exactly this — a report
    # stub, a new test module — with zero tracked edits. On 2026-08-27 02:49Z the nightly
    # apply reaped two such worktrees (`ahead=0 dirty=0 SAFE`) out from under three live
    # codex processes each; the `??` lines were the only evidence and they were filtered out.
    untracked_work: int = 0

    @property
    def dirty(self) -> int:
        """Edits that can contain work: tracked modifications plus untracked files."""
        return self.tracked_dirty + self.untracked_work

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
        if self.dirty:
            return False
        if self.branch is None:
            return self.ancestor
        return self.ahead == 0

    @property
    def unmerged_clean(self) -> bool:
        return self.ahead > 0 and self.dirty == 0 and self.branch is not None

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
        if self.dup and not self.dirty:
            return "DUP"
        if self.safe:
            return "SAFE"
        if self.unmerged_clean:
            return "unmerged"
        if self.stale and self.dirty:
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
                "-c",
                "codex",
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


def liveness_known(holders: dict[str, list[int]]) -> bool:
    """False iff the cwd scan came back empty.

    This very process has a cwd, so an honest `lsof -d cwd` can never report nothing:
    an empty map means the scan FAILED (timeout, missing binary), never "nothing is
    running". Treating it as "nothing running" would put every held worktree in the
    default apply set — the exact hole the liveness term exists to close.
    """
    return bool(holders)


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
        roots = sorted(
            p.resolve() for p in PROJECTS_HOME.iterdir() if (p / ".git").exists()
        )
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


# Roots that hold worktrees no repo may still admit to owning. `/private/tmp` is where
# hand-rolled `git worktree add` lands; `~/.cursor/worktrees` is cursor-agent's own
# managed home (`cursor-agent -w` → `~/.cursor/worktrees/<repo>/<name>`), which nests one
# level deeper than the rest and would be missed by a flat scan.
#
# Claude's `<repo>/.claude/worktrees/` is deliberately NOT here: those are found through
# their repo by `parse_worktrees`, and a stranded one there is still reachable the same
# way this scan reaches these — by walking to a depth that covers the layout in use.
TEMP_ROOTS: tuple[Path, ...] = (
    Path("/private/tmp"),
    Path("/tmp"),
    Path.home() / ".cursor" / "worktrees",
)
_SCAN_DEPTH = 2


@dataclass
class StrandedRow:
    """A directory that WAS a worktree and no longer is.

    `git worktree remove` unregisters before deleting, so an aborted removal leaves the
    admin dir gone and the files behind. The directory still holds a `.git` FILE pointing
    at a `gitdir:` that no longer exists — which is precisely why `git worktree list`
    cannot report it, and why every audit built on that command has a blind spot the size
    of whatever failed last. On 2026-07-25 that was ~13 GiB across ten trees, found only
    by diffing on-disk markers against the registration list by hand.

    The owning repo is still recoverable from the dangling gitdir path
    (`<repo>/.git/worktrees/<name>`), so dirtiness is still checkable with an explicit
    `--work-tree` — a stranded tree is unreadable to git, not unknowable.

    That check is deliberately one-sided. The tree's own HEAD lived in the admin dir and
    died with it, so the comparison runs against the REPO's current HEAD: commit drift
    reads as modification. It therefore over-reports work and never under-reports it,
    which keeps a tree out of the automatic set rather than deleting something real.
    """

    path: Path
    repo_root: Path | None
    size: str
    tracked_dirty: int  # -1 when the owning repo could not be recovered
    held: list[int]

    @property
    def reclaimable(self) -> bool:
        return not self.held and self.tracked_dirty == 0


def _admin_dir_of(wt: Path) -> str | None:
    """Read the `gitdir:` marker of a linked worktree, or None if it isn't one."""
    marker = wt / ".git"
    try:
        # A real repo has .git as a DIRECTORY — that is a clone, not a worktree. Temp
        # roots also hold dirs this uid cannot stat at all (other users' sandboxes),
        # and one unreadable neighbour must never abort the scan.
        if not marker.is_file():
            return None
        text = marker.read_text(errors="ignore")
    except OSError:
        return None
    admin = text.partition("gitdir:")[2].strip()
    return admin or None


def _repo_from_admin(admin: str) -> Path | None:
    """`<repo>/.git/worktrees/<name>` → `<repo>`, even after the admin dir is gone."""
    p = Path(admin)
    parts = p.parts
    try:
        i = len(parts) - 1 - parts[::-1].index(".git")
    except ValueError:
        return None
    repo = Path(*parts[:i])
    return repo if (repo / ".git").is_dir() else None


def _du(path: Path) -> str:
    out = run(["du", "-sh", str(path)]).stdout.split()
    return out[0] if out else "?"


def _candidate_dirs(
    roots: tuple[Path, ...], depth: int = _SCAN_DEPTH
) -> Iterator[Path]:
    """Directories under ``roots`` that could be a stranded worktree.

    Depth exists only because cursor-agent nests (`~/.cursor/worktrees/<repo>/<name>`)
    while everything else is flat. Recursion stops as soon as a directory carries a `.git`
    marker: a worktree never contains another worktree, and descending into one would walk
    a full checkout for nothing.
    """
    for root in roots:
        try:
            if not root.is_dir():
                continue
            entries = sorted(root.iterdir())
        except OSError:
            continue
        for entry in entries:
            try:
                if not entry.is_dir() or entry.is_symlink():
                    continue
                # Both stats must sit inside the guard: /private/tmp holds other uids'
                # sandboxes, and one EACCES here would abort the whole scan — a silent
                # zero that is indistinguishable from a clean box.
                marked = (entry / ".git").exists()
            except OSError:
                continue
            if marked:
                yield entry
            elif depth > 1:
                yield from _candidate_dirs((entry,), depth - 1)


def find_stranded(
    holders: dict[str, list[int]],
    roots: tuple[Path, ...] = TEMP_ROOTS,
    with_size: bool = True,
) -> list[StrandedRow]:
    """Directories whose worktree registration is gone but whose files remain."""
    rows: list[StrandedRow] = []
    seen: set[Path] = set()
    for entry in _candidate_dirs(roots):
        try:
            resolved = entry.resolve()
        except OSError:
            continue
        if resolved in seen:  # /tmp is a symlink to /private/tmp on macOS
            continue
        admin = _admin_dir_of(entry)
        if admin is None or Path(admin).exists():
            continue  # not a worktree, or still properly registered
        seen.add(resolved)
        repo = _repo_from_admin(admin)
        dirty = -1
        if repo is not None:
            out = run(
                [
                    "git",
                    f"--git-dir={repo / '.git'}",
                    f"--work-tree={entry}",
                    "status",
                    "--porcelain",
                    "--untracked-files=no",
                ]
            )
            # Count only edits that can CONTAIN work. A half-removed tree is missing most
            # of its files, so a plain line count reports thousands of "edits" that are
            # the aborted deletion itself — which would make every stranded tree look
            # maximally dirty and permanently un-reclaimable, i.e. exactly the bytes this
            # scan exists to recover. Deletions are the damage, not the work;
            # modifications and adds are the work.
            dirty = (
                sum(
                    1
                    for ln in out.stdout.splitlines()
                    if len(ln) >= 2 and set(ln[:2]) & {"M", "A", "R", "C", "U"}
                )
                if out.returncode == 0
                else -1
            )
            rows.append(
                StrandedRow(
                    path=entry,
                    repo_root=repo,
                    size=_du(entry) if with_size else "?",
                    tracked_dirty=dirty,
                    held=holders_for(entry, holders),
                )
            )
    return rows


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
        if not wt.exists():
            # Registered but the directory is gone (e.g. a scratchpad worktree whose
            # session dir was deleted out from under git). No cwd exists to run
            # anything in — subprocess with a missing cwd raises FileNotFoundError,
            # which killed the whole nightly GC 10 nights running (2026-08). The
            # `git worktree prune` at the end of apply clears the registration.
            print(f"  (prunable: {wt} — registered, directory gone)")
            continue
        st = run(["git", "status", "--porcelain"], cwd=wt)
        tracked_dirty = sum(
            1 for ln in st.stdout.splitlines() if not ln.startswith("??")
        )
        # Porcelain already omits ignored paths (.venv, caches), so every `??` line is a
        # real file somebody put here on purpose.
        untracked_work = sum(1 for ln in st.stdout.splitlines() if ln.startswith("??"))
        # `du` is the slow part; skip it on the cheap --check path (size irrelevant to the flag).
        size = (
            run(["du", "-sh", str(wt)]).stdout.split()[0]
            if (with_size and wt.exists())
            else "?"
        )
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
                untracked_work=untracked_work,
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
    """Remove a worktree, surviving read-only caches and never half-removing.

    `git worktree remove --force` unregisters FIRST and deletes files second, so a
    permission error partway through leaves the worst possible state: the admin dir
    under .git/worktrees is gone, the files are still on disk, and the directory is
    no longer a worktree — so it is invisible to the next audit and its bytes are
    never reclaimed. On 2026-07-25 that silently stranded ~13 GiB across ten
    worktrees, and the run reported them as failures while they were in fact
    already unregistered.

    The trigger is `.claude/cache/source-epochs/`, which materializes trees
    read-only on purpose. Make the tree writable first so the delete can finish;
    then, if git still failed, finish the job rather than leaving a half-state.
    """
    for path in wt.rglob("*"):
        try:
            if not path.is_symlink():
                path.chmod(path.stat().st_mode | stat.S_IWUSR)
        except OSError:
            pass
    try:
        run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo, check=True)
    except subprocess.CalledProcessError:
        # Half-removed is not a state to leave behind. If git already unregistered
        # it, the directory is now inert and only wastes disk; delete it and prune.
        if wt.exists() and not (wt / ".git").exists():
            shutil.rmtree(wt, ignore_errors=True)
        elif wt.exists():
            marker = (
                (wt / ".git").read_text(errors="ignore")
                if (wt / ".git").is_file()
                else ""
            )
            admin = marker.partition("gitdir:")[2].strip()
            if admin and not Path(admin).exists():
                shutil.rmtree(wt, ignore_errors=True)
            else:
                raise
        run(["git", "worktree", "prune"], cwd=repo)
    if wt.exists():
        raise RuntimeError(f"{wt} still on disk after removal")
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
    ap.add_argument(
        "--all-projects", action="store_true", help="scan all ~/Projects/* git repos"
    )
    ap.add_argument(
        "--include-unmerged",
        action="store_true",
        help="remove unmerged worktrees with no local edits (branch kept)",
    )
    ap.add_argument(
        "--force-stale",
        action="store_true",
        help="remove ahead==0 worktrees even with local edits",
    )
    ap.add_argument(
        "--force-all",
        action="store_true",
        help="remove all worktrees except --keep matches",
    )
    ap.add_argument(
        "--keep",
        action="append",
        default=[],
        help="substring; skip paths containing this",
    )
    ap.add_argument(
        "--prune-branches",
        action="store_true",
        help="delete branch after remove when ahead==0",
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
    if not liveness_known(cwd_holders):
        print(
            "[DEGRADED] liveness unknown — lsof reported no cwd holders at all; "
            "every removal is refused until the scan works",
            file=sys.stderr,
        )
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
        bits = [
            f"{counts[b]} to {b}" for b in ("LAND", "INSPECT", "REAP") if counts.get(b)
        ]
        print(
            f"STRANDED worktree branches: {', '.join(bits)} — `just worktree-gc audit --all-projects`"
        )
        for r in sorted(stranded, key=lambda x: bucket[x.classify()]):
            print(
                f"  [{bucket[r.classify()]:7}] {r.repo}/{r.branch}  ahead={r.ahead} dirty={r.dirty} age={r.age}"
            )
        return 0

    keep = set(args.keep)
    to_remove = [
        r
        for r in all_rows
        if should_remove(
            r, args.include_unmerged, args.force_stale, args.force_all, keep
        )
    ]

    for row in all_rows:
        cls = row.classify()
        mark = "→" if row in to_remove else " "
        br = row.branch or "(detached)"
        extra = ""
        if row.held:
            extra = f"  ← {row.held} LIVE process(es) working here"
        elif row.daemon_held:
            # State the OBSERVATION, never the conclusion. "Only a poller holds this
            # cwd" is what lsof proves; "nobody is working here" is an inference that
            # was caught being false on 2026-07-25 — an actively-running 6-sample wave
            # classified DAEMON because its shells ran from a scratchpad directory
            # elsewhere, leaving only the poller in the worktree's own cwd. The row
            # stayed out of every apply set on git state, so nothing was at risk, but
            # the wording claimed more than the evidence.
            # Print the exact PID: reclaiming needs a targeted kill, and a substring
            # `pkill -f` on a shared box has already killed a healthy job here twice.
            pids = " ".join(str(p) for p in row.daemon_pids)
            extra = f"  ← only a detached poller holds this cwd (kill {pids})"
            if row.ahead > 0 or row.dirty:
                extra += " — but it has commits/edits, verify before reclaiming"
        elif row.branch and row.ahead > 0:
            extra = f"  commits: {commit_preview(row.repo_root, row.branch)}"
        print(
            f"{mark} {row.repo:15} {br:42} ahead={row.ahead:>3} "
            f"dirty={row.dirty:>3} {cls:9} {row.age:>14} {row.size:>6}  {row.path}{extra}"
        )

    # Stranded trees are invisible to `git worktree list`, so they are found by scanning
    # the temp roots directly rather than by asking any repo what it owns.
    stranded = find_stranded(cwd_holders, with_size=with_size)
    if stranded:
        print(
            "\nSTRANDED — registration gone, files remain (invisible to `git worktree list`):"
        )
        for s in stranded:
            if s.held:
                why = f"HELD by {' '.join(str(p) for p in s.held)}"
            elif s.tracked_dirty > 0:
                why = f"{s.tracked_dirty} tracked edits — recover before removing"
            elif s.tracked_dirty < 0:
                why = "owning repo unrecoverable — inspect by hand"
            else:
                why = "reclaimable"
            owner = s.repo_root.name if s.repo_root else "?"
            print(
                f"{'→' if s.reclaimable else ' '} {owner:15} {s.size:>6}  {s.path}  ({why})"
            )

    if not all_rows and not stranded:
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

    if not liveness_known(cwd_holders):
        print("refusing to remove anything: liveness unknown (see [DEGRADED] above)")
        return 2

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

    # Stranded trees are no longer worktrees, so `git worktree remove` cannot touch them —
    # the directory is inert and the reclaim is a plain delete. Gated on the same evidence
    # the registered rows use: no live holder, no tracked edits, owning repo recovered.
    reclaimed = 0
    for s in stranded:
        if not s.reclaimable:
            continue
        try:
            shutil.rmtree(s.path, ignore_errors=False)
        except OSError:
            for p in s.path.rglob("*"):
                try:
                    if not p.is_symlink():
                        p.chmod(p.stat().st_mode | stat.S_IWUSR)
                except OSError:
                    pass
            shutil.rmtree(s.path, ignore_errors=True)
        if s.path.exists():
            print(f"FAIL stranded {s.path}: still on disk", file=sys.stderr)
            continue
        print(f"reclaimed stranded {s.path} ({s.size})")
        reclaimed += 1

    # A registration whose directory is already gone is the mirror image of a stranded
    # tree, and it is what makes `worktree list` report paths that do not exist.
    for repo in repos:
        run(["git", "worktree", "prune"], cwd=repo)

    print(
        f"\nremoved {removed}/{len(to_remove)} worktrees; reclaimed {reclaimed} stranded"
    )
    # Janitor effect-receipt (observe 2026-08-11 B3): principal = trees removed+reclaimed
    try:
        from janitor_receipt import write_receipt

        write_receipt(
            "worktree_gc",
            principal_metric=removed + reclaimed,
            detail=f"removed={removed} reclaimed_stranded={reclaimed}",
        )
    except Exception as e:  # never fail the GC over a receipt write
        print(f"janitor_receipt write skipped: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
