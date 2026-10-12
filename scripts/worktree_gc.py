#!/usr/bin/env python3
"""Prune stale agent git worktrees across Projects.

Git never removes worktrees when a branch merges — `claude --worktree`, Cursor
best-of-n, and autoresearch only call `git worktree add`. Session end / merge do
not call `git worktree remove`, so `.claude/worktrees/` accumulates duplicate
venvs and recordings.

This removes worktree *directories* only. Branches survive unless --prune-branches.

Safety classes (audit):
  SAFE           — already on main, clean working tree, idle >= --safe-idle-min
  SAFE-fresh     — otherwise SAFE but the work clock is fresh or unknown; kept
  DUP            — ahead>0 but every patch already on main (cherry-picked/rebased,
                   then stranded); clean. Reap with --include-unmerged; the branch
                   is pure cruft, prunable with --prune-branches.
  unmerged       — ahead>0: GENUINE unique commits on branch; NEVER removed by default
  stale-dirty    — ahead==0 but uncommitted edits; needs --force-stale
  skip-dirty     — ahead>0 AND uncommitted edits; never removed without --force-all
  LOCKED         — `git worktree lock`ed; pid-less locks are never auto-released.
                   A lock naming a `pid <N>` that no longer exists prints `stale-lock`
                   and is released (`git worktree unlock`) right before a removal.

Audit also prints last-commit age (currency signal — branches weeks behind = cruft).

apply (default): SAFE only — clean merged trees idle >= --safe-idle-min (default 60)
apply --include-unmerged: also remove unmerged worktrees with NO local edits
  (HEAD pinned, branch kept when present; only the directory/venv goes)
apply --unmerged-idle-hours N: remove only patch-duplicate branched trees idle >= N
  hours; unique commits are suggestion-only
audit/suggest --lock-max-age-hours N: label old pid-less locks aged-lock, read-only
suggest [--json]: size-ranked reclaim suggestions, never changes anything
archive --path TREE: explicitly archive, pin HEAD and remove this one tree
apply --force-stale: also stale (ahead==0) with dirty trees (discards wt edits)
apply --force-all: everything except --keep, held, and live-locked trees (dangerous)
apply --strip-idle-caches-min N: also delete the derived caches (.venv, .uv-cache,
  .claude/cache/index-trees) of any tree with no process inside and nothing touched for N
  minutes; a live lock keeps the tree, never its caches (audit marks would-strip)
apply --prune-pytest-hours N: also delete pytest-of-<user> basetemp dirs untouched for N
  hours whose pytest has exited (audit marks would-prune-pytest)
prune: only those two steps; never removes a worktree (the low-disk guard's mode)

Evidence: standing #g metafix — worktree leak is harness hygiene, not telos.
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
import json
import math
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from config import PROJECT_ROOTS

PROJECTS_HOME = Path.home() / "Projects"
SKIP_PATH_SUBSTR = ("factory", "-factory")
# lsof lives in /usr/sbin; a launchd/cron PATH without it turns the liveness scan
# into an OSError → empty map → "liveness unknown" → every nightly apply exits 2.
# Never let PATH decide a safety scan.
LSOF = shutil.which("lsof") or "/usr/sbin/lsof"
# Why the last cwd scan came back the way it did — printed with the [DEGRADED] line.
LAST_SCAN_DIAG = "scan not run"


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
    # `git worktree lock` reason: None = unlocked, "" = locked without a reason.
    lock: str | None = None
    # The lock names a `pid <N>` that no longer exists (session ended, reboot).
    lock_stale: bool = False
    idle_days: float = 0.0  # audited work clock; unknown counts as fresh
    safe_idle_min: float = 60.0

    @property
    def dirty(self) -> int:
        """Edits that can contain work: tracked modifications plus untracked files."""
        return self.tracked_dirty + self.untracked_work

    @property
    def lock_live(self) -> bool:
        """Claude Code locks agent and `--worktree` session trees while they run.

        An agent between tool calls holds no cwd inside its tree, so for those lanes the
        lock is the liveness evidence lsof cannot give.
        """
        return self.lock is not None and not self.lock_stale

    @property
    def stale(self) -> bool:
        return self.ahead == 0

    @property
    def clean_on_main(self) -> bool:
        """On main, no local edits, and no process working in it.

        The liveness term is not decoration. Until 2026-07-25 this property was git
        state + age only, and on that day it called SIX worktrees SAFE — the default
        apply set — while `lsof` showed a live python3 holding each one. Crash-loop
        watchers and remat lanes poll on a timer and write nothing between polls, so a
        clean tree with an old mtime is exactly what a *working* agent looks like.
        """
        if self.held or self.daemon_held or self.lock_live:
            return False
        if self.dirty:
            return False
        if self.branch is None:
            return self.ancestor
        return self.ahead == 0

    @property
    def safe(self) -> bool:
        """Clean on main and idle long enough to survive pauses between tool calls."""
        return self.clean_on_main and self.idle_days * 1440 >= self.safe_idle_min

    @property
    def unmerged_clean(self) -> bool:
        return self.ahead > 0 and self.dirty == 0

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
        if self.lock_live:
            return "LOCKED"
        if self.dup and not self.dirty:
            return "DUP"
        if self.clean_on_main:
            return "SAFE" if self.safe else "SAFE-fresh"
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

    Every process counts, whatever its name. Until 2026-09-28 the scan kept only
    `python3`/`bash`/`git`/`node`/`codex`, and Claude Code's native binary runs as its
    version string (lsof `c2.1.283`), so a claude session sitting in a worktree never read
    as HELD. The unfiltered scan is ~1.5k lines in <0.1 s.

    Returns {} when lsof is unavailable. That is the dangerous direction, so an empty
    result means "unknown", never "nothing is running" — see the caller.
    """
    global LAST_SCAN_DIAG
    started = time.monotonic()
    try:
        result = subprocess.run(
            [LSOF, "-a", "-d", "cwd", "-F", "pn"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        LAST_SCAN_DIAG = (
            "lsof timed out after 60s (a sleeping/unreachable mount stalls stat())"
        )
        return {}
    except (OSError, subprocess.SubprocessError) as exc:
        LAST_SCAN_DIAG = f"lsof could not run: {exc!r}"
        return {}
    LAST_SCAN_DIAG = (
        f"lsof rc={result.returncode} in {time.monotonic() - started:.1f}s, "
        f"{len(result.stdout.splitlines())} output lines, stderr={result.stderr.strip()[:200]!r}"
    )
    return _parse_lsof_fields(result.stdout)


def _parse_lsof_fields(stdout: str) -> dict[str, list[int]]:
    """`lsof -F pn` field output (`p<pid>` then its `n<path>` lines) → {path: [pids]}."""
    holders: dict[str, list[int]] = {}
    pid: int | None = None
    for line in stdout.splitlines():
        if line.startswith("p"):
            try:
                pid = int(line[1:])
            except ValueError:
                pid = None
        elif line.startswith("n") and pid is not None:
            holders.setdefault(line[1:], []).append(pid)
    return holders


def live_mapped_holders() -> dict[str, list[int]]:
    """Map every file a process has mapped as text (its binary, dylibs, extension modules).

    A python run from a lane's `.venv` with its cwd elsewhere (`uv run --project <tree>`, a
    bgrun job started from a scratchpad) is invisible to the cwd scan, but every compiled
    module it imported stays mapped from `.venv/lib/.../site-packages`. One lsof call, ~0.4 s
    for ~15k lines on 2026-09-29. This process maps its own interpreter, so {} means the scan
    failed and callers must read it as "unknown", exactly like the cwd scan.
    """
    try:
        result = subprocess.run(
            [LSOF, "-a", "-d", "txt", "-F", "pn"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    return _parse_lsof_fields(result.stdout)


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
    """PIDs working inside ``path``, including nested subdirectories.

    lsof reports kernel paths, so `/var/folders/…/T` (a lane's $TMPDIR) comes back as
    `/private/var/folders/…/T`; the resolved spelling is matched as well as the given one.
    """
    needles = {str(path)}
    try:
        needles.add(str(path.resolve()))
    except OSError:
        pass
    out: list[int] = []
    for cwd, pids in holders.items():
        if any(cwd == needle or cwd.startswith(needle + "/") for needle in needles):
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


def parse_worktrees(repo: Path) -> list[tuple[Path, str | None, str | None]]:
    """(path, branch, lock reason) per linked worktree; lock None = unlocked, "" = no reason."""
    out = run(["git", "worktree", "list", "--porcelain"], cwd=repo)
    if out.returncode != 0:
        return []
    rows: list[tuple[Path, str | None, str | None]] = []
    wt: Path | None = None
    branch: str | None = None
    lock: str | None = None
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            if wt is not None:
                rows.append((wt, branch, lock))
            wt = Path(line.split(" ", 1)[1])
            branch = None
            lock = None
        elif line.startswith("branch "):
            branch = line.split(" ", 1)[1].replace("refs/heads/", "")
        elif line == "detached":
            branch = None
        elif line == "locked" or line.startswith("locked "):
            lock = line[len("locked ") :]
            # git C-quotes a reason carrying special characters; the pid survives either way.
            if len(lock) > 1 and lock.startswith('"') and lock.endswith('"'):
                lock = lock[1:-1]
    if wt is not None:
        rows.append((wt, branch, lock))
    return [(p, b, lk) for p, b, lk in rows if p.resolve() != repo.resolve()]


# Claude Code's lock reason is `claude agent|session <name> (pid <N> start <date>)`, and the
# lock outlives a session that dies (crash, reboot). 2.1.283 treats a dead-pid lock as stale
# and re-takes it when it resumes that tree; a tree nobody resumes stays pinned.
_LOCK_PID = re.compile(r"\bpid (\d{1,10})\b")


def lock_is_stale(reason: str | None) -> bool:
    """True only when the lock names a `pid <N>` and no process with that pid exists.

    A reason without a pid may be a human's `git worktree lock --reason`, so it stays live.
    A reused pid also reads live; both errors keep the tree, never remove it.
    """
    match = _LOCK_PID.search(reason or "")
    if match is None:
        return False
    pid = int(match.group(1))
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except (OSError, OverflowError):
        return False  # EPERM: the process exists under another uid
    return False


def current_lock(repo: Path, wt: Path) -> str | None:
    for path, _branch, lock in parse_worktrees(repo):
        if path == wt:
            return lock
    return None


def lock_age_hours(row: WorktreeRow, now: float | None = None) -> float | None:
    admin = run(["git", "rev-parse", "--absolute-git-dir"], cwd=row.path, check=True)
    stamp = _mtime(Path(admin.stdout.strip()) / "locked")
    if stamp is None:
        return None
    return max(0.0, ((time.time() if now is None else now) - stamp) / 3600)


def lock_is_aged(
    row: WorktreeRow,
    max_age_hours: float | None,
    reason: str | None,
    now: float | None = None,
) -> bool:
    """Only pid-less locks with a known old lock-file clock are age eligible."""
    if max_age_hours is None or reason is None or _LOCK_PID.search(reason):
        return False
    if row.held or row.daemon_held:
        return False
    age = lock_age_hours(row, now)
    return age is not None and age > max_age_hours


def release_stale_lock(row: WorktreeRow) -> str | None:
    """Release only a dead-pid lock; return a hold reason, else None.

    Re-reads the lock rather than trusting the audit: Claude Code re-locks a tree when it
    resumes an agent there, which can happen between the scan and the removal.
    """
    lock = current_lock(row.repo_root, row.path)
    if lock is None:
        return None
    if not lock_is_stale(lock):
        return f"locked ({lock or 'no reason given'})"
    out = run(["git", "worktree", "unlock", str(row.path)], cwd=row.repo_root)
    if out.returncode != 0:
        return f"stale lock could not be released: {out.stderr.strip()[:160]}"
    print(f"unlocked {row.path} (stale lock: {lock})")
    return None


def removal_hold(row: WorktreeRow) -> str | None:
    """Refresh cwd and lock vetoes immediately before a registered-tree removal."""
    holders = live_cwd_holders()
    if not liveness_known(holders):
        return "[DEGRADED] liveness unknown at removal"
    if holders_for(row.path, holders):
        return "live process inside at removal"
    return release_stale_lock(row)


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
                    "--no-optional-locks",
                    f"--git-dir={repo / '.git'}",
                    f"--work-tree={entry}",
                    "status",
                    "--porcelain",
                    "--untracked-files=all",
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
                    if ln.startswith("??")
                    or (len(ln) >= 2 and set(ln[:2]) & {"M", "A", "R", "C", "U"})
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
    try:
        base = default_branch(repo)
    except RuntimeError:
        return -1
    r = run(["git", "rev-list", "--count", f"{base}..{branch}"], cwd=repo)
    if r.returncode != 0:
        return -1
    try:
        return int(r.stdout.strip() or "0")
    except ValueError:
        return -1


def is_ancestor(repo: Path, sha: str) -> bool:
    try:
        base = default_branch(repo)
    except RuntimeError:
        return False  # Unknown upstream must preserve a pin before any removal.
    return (
        run(["git", "merge-base", "--is-ancestor", sha, base], cwd=repo).returncode == 0
    )


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
    try:
        base = default_branch(repo)
    except RuntimeError:
        return False
    r = run(["git", "cherry", base, branch], cwd=repo)
    if r.returncode != 0:
        return False
    commits = run(["git", "rev-list", f"{base}..{branch}"], cwd=repo)
    if commits.returncode != 0:
        return False
    ahead = set(commits.stdout.splitlines())
    equivalent = {ln.split()[1] for ln in r.stdout.splitlines() if ln.startswith("- ")}
    # git cherry omits merges. An omitted commit may hold conflict-resolution work.
    return bool(ahead) and ahead <= equivalent


def audit_repo(
    repo: Path, with_size: bool = True, safe_idle_min: float = 60.0
) -> list[WorktreeRow]:
    name = repo.name
    rows: list[WorktreeRow] = []
    for wt, branch, lock in parse_worktrees(repo):
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
        # --no-optional-locks: a plain `git status` rewrites the index stat cache,
        # which would reset the idle clock (index mtime) on every nightly audit.
        st = run(
            ["git", "--no-optional-locks", "status", "--porcelain"], cwd=wt, check=True
        )
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
            ahead = ahead_of_main(repo, sha) if sha else -1
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
                lock=lock,
                lock_stale=lock_is_stale(lock),
                idle_days=idle_age_days(wt),
                safe_idle_min=safe_idle_min,
            )
        )
    return rows


def commit_preview(repo: Path, branch: str, n: int = 2) -> str:
    try:
        base = default_branch(repo)
    except RuntimeError:
        return "? (default branch unknown)"
    r = run(["git", "log", "--oneline", f"-{n}", f"{base}..{branch}"], cwd=repo)
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
    # A live lock is Claude Code's own "an agent runs here" and outranks every force flag,
    # exactly like HELD. A stale lock (dead pid) falls through and is released at removal.
    if row.lock_live:
        return False
    if force_all:
        return True
    if row.safe:
        return True
    if include_unmerged and row.unmerged_clean:
        return True
    return bool(force_stale and row.stale)


def make_writable(root: Path) -> None:
    """Give the owner rwx on ``root`` and every directory below it, never through a symlink.

    Deleting an entry needs write and search permission on its PARENT directory, not on the
    entry; listing a directory needs read. Trees materialized read-only on purpose
    (`.claude/cache/source-epochs/`, pre-commit's `.claude/cache/index-trees/`, pytest
    fixtures that chmod a-w) otherwise stop `git worktree remove`, `shutil.rmtree` and a
    plain `rm -rf` partway; on 2026-09-29 pytest's own cleanup had left 4.2 GB of
    `garbage-*` basetemp dirs it could not delete. Each directory is fixed before it is
    listed, so even a mode-000 directory is entered.
    """

    def fix(path: str) -> None:
        try:
            st = os.lstat(path)
            if stat.S_ISDIR(st.st_mode) and st.st_mode & stat.S_IRWXU != stat.S_IRWXU:
                os.chmod(path, stat.S_IMODE(st.st_mode) | stat.S_IRWXU)
        except OSError:
            pass

    if root.is_symlink() or not root.is_dir():
        return
    fix(str(root))
    for dirpath, dirnames, _files in os.walk(
        root
    ):  # top-down: children fixed before entry
        for name in dirnames:
            fix(os.path.join(dirpath, name))


def delete_tree(path: Path) -> bool:
    """Delete ``path`` and everything below it, read-only subtrees included. True iff gone.

    A symlink is never followed or deleted: the caller named a real directory.
    """
    if path.is_symlink():
        return False
    make_writable(path)
    shutil.rmtree(path, ignore_errors=True)
    return not path.exists()


def remove_worktree(repo: Path, wt: Path, force: bool = True) -> None:
    """Remove a worktree, surviving read-only caches and never half-removing.

    ``force=False`` lets git re-check cleanliness at the moment of deletion: it refuses a
    tree with tracked edits or untracked files (ignored caches like .venv do not count) or
    a lock, and raises CalledProcessError with the tree intact.

    `git worktree remove --force` unregisters FIRST and deletes files second, so a
    permission error partway through leaves the worst possible state: the admin dir
    under .git/worktrees is gone, the files are still on disk, and the directory is
    no longer a worktree — so it is invisible to the next audit and its bytes are
    never reclaimed. On 2026-07-25 that silently stranded ~13 GiB across ten
    worktrees, and the run reported them as failures while they were in fact
    already unregistered.

    Pin unique HEADs before git can unregister them. Permission failures get one
    directory-only chmod/retry, then half-removal recovery. Regular files may be
    hardlinked outside the tree, so changing their mode would escape the boundary.
    """
    if wt.is_symlink():
        raise RuntimeError(f"refusing to remove symlinked worktree {wt}")
    head = run(["git", "rev-parse", "HEAD"], cwd=wt, check=True).stdout.strip()
    if not is_ancestor(repo, head):
        ref = _pin_ref(repo, wt.name, time.strftime("%Y%m%d"), head)
        print(f"pinned {wt} HEAD={head} at {ref}")
    cmd = ["git", "worktree", "remove", *(["--force"] if force else []), str(wt)]
    try:
        run(cmd, cwd=repo, check=True)
    except subprocess.CalledProcessError as first:
        if "permission denied" in (first.stderr or "").lower() and wt.exists():
            print(
                f"RETRY {wt}: permission denied; owner-writable directories, retry once"
            )
            # Unlink needs parent permissions, never a regular file's write bit.
            make_writable(wt)
            try:
                run(cmd, cwd=repo, check=True)
            except subprocess.CalledProcessError:
                if wt.exists() and (wt / ".git").exists():
                    admin = _admin_dir_of(wt)
                    if not admin or Path(admin).exists():
                        raise
            else:
                if not wt.exists():
                    return
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


# ---------------------------------------------------------------------------
# Archive-then-reap for stale dirty trees, and cache stripping for idle ones.
#
# The 2026-09-23 04:10 nightly listed 26 worktrees (19 genomics, ~18 GB) as
# stale-dirty/skip-dirty and removed 0: lanes landed onto main by per-file patch
# keep their uncommitted diff forever, and --force-stale discards it. Archiving
# the diff + untracked files (with HEAD pinned under refs/wt-archive/) makes the
# removal restorable. The 2026-10-12 ruling supersedes age-based archiving:
# only explicit archive --path may remove unlanded work; age is a suggestion.
# ---------------------------------------------------------------------------
ARCHIVE_ROOT = Path.home() / ".local" / "share" / "worktree-archives"
CACHE_DIRS: tuple[str, ...] = (".venv", ".uv-cache", "node_modules")
# Rederivable, git-ignored caches a lane builds inside its own tree: `uv run` from the tree
# root syncs a ~735 MB .venv, and the genomics pre-commit materializes the staged index
# read-only under .claude/cache/index-trees (~430 MB). Across 27 lane trees these, plus 7 GB
# of pytest basetemps, took the data volume to 334 MB free on 2026-09-29 06:05, the second
# ENOSPC in two days.
STRIP_DIRS: tuple[str, ...] = (".venv", ".uv-cache", ".claude/cache/index-trees")


def _mtime(path: Path) -> float | None:
    try:
        return path.lstat().st_mtime
    except OSError:
        return None  # vanished between status and stat


def idle_age_days(wt: Path, now: float | None = None) -> float:
    """Days since the newest touch of any dirty path or the git-dir index/HEAD.

    Last-commit age is deliberately NOT used: a detached lane sits on an old main
    commit while someone edits it all day.
    """
    now = time.time() if now is None else now
    stamps = activity_stamps(wt)
    if not stamps:
        return 0.0  # unknown → treat as fresh (the safe direction)
    return max(0.0, (now - max(stamps)) / 86400.0)


def activity_stamps(wt: Path) -> list[float]:
    """mtimes of every dirty path and of the git-dir index/HEAD: the tree's own work clock."""
    # -uall: a collapsed `dir/` entry carries the directory's mtime, which editing a file
    # inside it never bumps; list every untracked file so each edit counts as activity.
    st = run(
        ["git", "--no-optional-locks", "status", "--porcelain", "-z", "-uall"],
        cwd=wt,
    )
    stamps: list[float] = []
    entries = st.stdout.split("\0")
    i = 0
    while i < len(entries):
        ent = entries[i]
        i += 1
        if len(ent) < 4:
            continue
        code, rel = ent[:2], ent[3:]
        if "R" in code or "C" in code:
            i += 1  # -z rename carries the source path as the next entry
        m = _mtime(wt / rel)
        if m is not None:
            stamps.append(m)
    gd = run(["git", "rev-parse", "--git-dir"], cwd=wt).stdout.strip()
    if gd:
        gdir = Path(gd) if Path(gd).is_absolute() else wt / gd
        for name in ("index", "HEAD"):
            m = _mtime(gdir / name)
            if m is not None:
                stamps.append(m)
    return stamps


def _under_cache(rel: str) -> bool:
    return any(part in CACHE_DIRS for part in Path(rel).parts)


def _write_patch(wt: Path, dest: Path) -> None:
    # --no-ext-diff: the operator's diff.external=difft writes non-patches otherwise.
    out = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--binary", "HEAD"],
        cwd=wt,
        capture_output=True,
        check=True,
    )
    dest.write_bytes(out.stdout)


def _archive_name(row: WorktreeRow) -> str:
    """The leaf, qualified by its parent when the leaf is just the repo's name.

    Codex lanes end in `<lane>/<repo>` (~/.codex/worktrees/<lane>/genomics), so the leaf
    alone names every codex tree of a repo alike.
    """
    wt = row.path
    return f"{wt.parent.name}--{wt.name}" if wt.name == row.repo else wt.name


def _fresh_dir(base: Path) -> Path:
    """Create and return base, else base-2, base-3 …: an archive is never written over.

    A shared directory would let the second archive overwrite the first after the first
    tree was already removed — the one irreversible outcome this path exists to prevent.
    """
    dest, n = base, 1
    while True:
        try:
            dest.mkdir(parents=True)
            return dest
        except FileExistsError:
            n += 1
            dest = base.with_name(f"{base.name}-{n}")


def _pin_ref(repo: Path, name: str, day: str, head: str) -> str:
    base = f"refs/wt-archive/{name}-{day}"
    ref, n = base, 1
    while True:
        cur = run(["git", "rev-parse", "--verify", "-q", ref], cwd=repo).stdout.strip()
        if not cur or cur == head:
            break
        n += 1
        ref = f"{base}-{n}"
    run(["git", "update-ref", ref, head], cwd=repo, check=True)
    return ref


@dataclass
class ArchiveResult:
    dir: Path
    ok: bool
    reason: str = ""
    patch_bytes: int = 0
    untracked: int = 0
    ref: str = ""
    ignored_cache_files: int = 0
    ignored_cache_bytes: int = 0


def _archive_ignored_cache(wt: Path, dest: Path) -> tuple[int, int]:
    """Save small regular cache files; exclude index trees and all symlinks."""
    cache = _real_subdir(wt, ".claude/cache")
    count = total = 0
    with tarfile.open(dest, "w:gz") as archive:
        if cache is None:
            return count, total

        def walk_error(error: OSError) -> None:
            raise error  # An unreadable report must hold the tree, never disappear.

        for directory, dirs, files in os.walk(cache, onerror=walk_error):
            dirs[:] = [
                d
                for d in dirs
                if not (Path(directory) / d).is_symlink()
                and not (Path(directory) == cache and d == "index-trees")
            ]
            for name in sorted(files):
                path = Path(directory) / name
                st = path.lstat()
                if not stat.S_ISREG(st.st_mode) or st.st_size > 20 * 1024 * 1024:
                    continue
                with os.fdopen(
                    os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb"
                ) as source:
                    st = os.fstat(source.fileno())
                    if not stat.S_ISREG(st.st_mode) or st.st_size > 20 * 1024 * 1024:
                        continue
                    info = tarfile.TarInfo(path.relative_to(wt).as_posix())
                    info.size, info.mode, info.mtime = (
                        st.st_size,
                        stat.S_IMODE(st.st_mode),
                        st.st_mtime,
                    )
                    archive.addfile(info, source)
                    count += 1
                    total += st.st_size
    # Read every member through gzip's checksum, including empty archives.
    with tarfile.open(dest, "r:gz") as archive:
        members = archive.getmembers()
        if len(members) != count or sum(m.size for m in members) != total:
            raise OSError("ignored-cache archive failed its entry/size self-check")
        for member in members:
            source = archive.extractfile(member)
            assert source is not None
            with source:
                while source.read(1024 * 1024):
                    pass
    return count, total


def archive_worktree(
    row: WorktreeRow, now: float | None = None, root: Path | None = None
) -> ArchiveResult:
    """Write a restorable archive of ``row`` and self-check it. Never removes.

    Also preserve small regular .claude/cache files, excluding index-trees and symlinks.
    Other ignored files retain the SAFE removal contract.
    """
    now = time.time() if now is None else now
    root = ARCHIVE_ROOT if root is None else root
    wt = row.path
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    name = _archive_name(row)
    dest = _fresh_dir(root / row.repo / day / name)
    head = run(["git", "rev-parse", "HEAD"], cwd=wt).stdout.strip()
    (dest / "head.txt").write_text(head + "\n")
    status = run(["git", "--no-optional-locks", "status", "--porcelain"], cwd=wt).stdout
    (dest / "status.txt").write_text(status)
    patch = dest / "tracked.patch"
    _write_patch(wt, patch)
    others = run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=wt
    ).stdout.split("\0")
    files = [f for f in others if f and not _under_cache(f)]
    (dest / "untracked.list").write_text("".join(f + "\n" for f in files))
    tgz = dest / "untracked.tgz"
    if files:
        subprocess.run(
            ["tar", "-czf", str(tgz), "--null", "-T", "-"],
            cwd=wt,
            input="\0".join(files).encode(),
            capture_output=True,
            check=True,
        )
    ignored_tgz = dest / "ignored-cache.tgz"
    ignored_count, ignored_bytes = _archive_ignored_cache(wt, ignored_tgz)
    (dest / "RESTORE.md").write_text(
        f"# Restore {wt}\n\nArchived {day} from repo `{row.repo_root}`.\n\n```sh\n"
        f"git -C {row.repo_root} worktree add --detach {wt} {head}\n"
        f"git -C {wt} apply {patch}\n"
        + (f"tar -xzf {tgz} -C {wt}\n" if files else "")
        + f"tar -xzf {ignored_tgz} -C {wt}\n"
        + "```\n"
    )
    res = ArchiveResult(
        dir=dest,
        ok=False,
        patch_bytes=patch.stat().st_size,
        untracked=len(files),
        ignored_cache_files=ignored_count,
        ignored_cache_bytes=ignored_bytes,
    )
    if res.patch_bytes:
        chk = run(["git", "apply", "--check", "-R", str(patch)], cwd=wt)
        if chk.returncode != 0:
            res.reason = f"patch does not reverse-apply: {chk.stderr.strip()[:160]}"
            return res
    if files:
        listed = run(["tar", "-tzf", str(tgz)])
        have = {ln.rstrip("/") for ln in listed.stdout.splitlines()}
        missing = [f for f in files if f not in have]
        if listed.returncode != 0 or missing:
            res.reason = f"tarball missing {len(missing)} of {len(files)} entries"
            return res
    res.ref = _pin_ref(
        row.repo_root, name, time.strftime("%Y%m%d", time.localtime(now)), head
    )
    res.ok = True
    return res


def _real_subdir(wt: Path, rel: str) -> Path | None:
    """``wt/rel`` if it is a real directory reached without crossing a symlink, else None.

    Every component is checked, not only the leaf: a `.claude` symlinked to main's checkout
    would otherwise walk the strip into main's own caches.
    """
    path = wt
    for part in Path(rel).parts:
        path = path / part
        if path.is_symlink():
            return None
    return path if path.is_dir() else None


def strip_candidates(wt: Path) -> list[Path]:
    """``wt``'s real, git-ignored, untracked STRIP_DIRS; a symlink is never followed or deleted.

    A directory that git tracks anything under, or does not ignore, holds somebody's content
    rather than a derived cache, so it stays. If git cannot answer, nothing is a candidate.
    """
    found = [p for rel in STRIP_DIRS if (p := _real_subdir(wt, rel)) is not None]
    if not found:
        return []
    rels = [p.relative_to(wt).as_posix() for p in found]
    tracked = run(["git", "ls-files", "-z", "--", *rels], cwd=wt)
    # STRIP_DIRS are plain constants, so line output is exact (-z needs --stdin).
    ignored = run(["git", "check-ignore", *rels], cwd=wt)
    if tracked.returncode != 0 or ignored.returncode not in (0, 1):
        return []
    tracked_paths = [t for t in tracked.stdout.split("\0") if t]
    ignored_rels = {i.rstrip("/") for i in ignored.stdout.splitlines() if i}
    return [
        p
        for p, rel in zip(found, rels)
        if rel in ignored_rels
        and not any(t == rel or t.startswith(rel + "/") for t in tracked_paths)
    ]


def strip_idle_caches(wt: Path, planned: list[Path] | None = None) -> dict[str, str]:
    """Delete ``wt``'s caches (only ``planned`` ones, when given) → {relative path: size}.

    Candidates are re-derived here rather than trusted from the plan, so a cache that became
    a symlink or gained tracked content since the audit stays.
    """
    sizes: dict[str, str] = {}
    for p in strip_candidates(wt):
        if planned is not None and p not in planned:
            continue
        size = _du(p)
        if delete_tree(p):
            sizes[p.relative_to(wt).as_posix()] = size
        else:
            print(f"FAIL strip {p}: still on disk", file=sys.stderr)
    return sizes


def cache_activity_stamps(cache: Path, depth: int = 3) -> list[float]:
    """mtimes of ``cache``, its top-level files, and every directory up to ``depth`` below.

    A directory's mtime moves whenever an entry is added, removed or renamed in it, so this
    sees `uv sync` installing into `.venv/lib/python3.x/site-packages` (depth 3) and
    pre-commit materializing a new tree under `index-trees` without statting every file.
    """
    stamps: list[float] = []
    level: list[Path] = [cache]
    for depth_now in range(depth + 1):
        below: list[Path] = []
        for directory in level:
            m = _mtime(directory)
            if m is not None:
                stamps.append(m)
            if depth_now == depth:
                continue
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                below.append(Path(entry.path))
                            elif depth_now == 0:
                                stamps.append(
                                    entry.stat(follow_symlinks=False).st_mtime
                                )
                        except OSError:
                            continue
            except OSError:
                continue
        level = below
    return stamps


def plan_idle_archive(
    rows: list[WorktreeRow],
    archive_days: float | None,
    keep: set[str],
    exclude: list[WorktreeRow],
    now: float | None = None,
) -> list[WorktreeRow]:
    """Stale-dirty/skip-dirty trees idle >= ``archive_days``: archived, then removed."""
    if archive_days is None:
        return []
    archive: list[WorktreeRow] = []
    for row in rows:
        if row.held or row.daemon_held or row.lock_live:
            continue
        if any(k in str(row.path) for k in keep):
            continue
        if row in exclude or not row.path.exists():
            continue
        if (
            row.classify() in ("stale-dirty", "skip-dirty")
            and idle_age_days(row.path, now) >= archive_days
        ):
            archive.append(row)
    return archive


def plan_cache_strip(
    rows: list[WorktreeRow],
    idle_min: float | None,
    keep: set[str],
    exclude: list[WorktreeRow],
    mapped: dict[str, list[int]],
    now: float | None = None,
) -> list[tuple[WorktreeRow, list[Path]]]:
    """(tree, caches) to strip: no process inside and nothing touched for ``idle_min`` minutes.

    Idle means all of: no process has its cwd in the tree (HELD/DAEMON); no process maps a
    file inside the cache (``mapped``: a `.venv` python started from elsewhere); and no
    mtime newer than ``idle_min`` among the tree's dirty paths, git index/HEAD, root
    directory and the cache's own directories. Dirty trees qualify, because only ignored,
    untracked cache directories are deleted, never a tracked or unignored file.

    A live `git worktree lock` does NOT protect caches. Claude Code locks every agent tree
    with the PARENT session's pid, so the lock reads live for as long as the lead runs: on
    2026-09-29 all 19 genomics agent trees carried one 28 h-old pid, and the 72-minute
    .venv strip, which skipped locked trees, logged `stripped 0` while 11 of them held a
    .venv or index-trees and the volume filled. The lock still keeps the tree; its caches
    are rederivable (the next `uv run` re-syncs from the shared uv cache, and pre-commit
    re-materializes its index tree).
    """
    if idle_min is None:
        return []
    now = time.time() if now is None else now
    out: list[tuple[WorktreeRow, list[Path]]] = []
    for row in rows:
        if row.held or row.daemon_held:
            continue
        if any(k in str(row.path) for k in keep):
            continue
        if row in exclude or not row.path.exists():
            continue
        caches = [c for c in strip_candidates(row.path) if not holders_for(c, mapped)]
        if not caches:
            continue
        stamps = activity_stamps(row.path)
        root = _mtime(row.path)
        if root is not None:
            stamps.append(root)
        for cache in caches:
            stamps.extend(cache_activity_stamps(cache))
        if stamps and (now - max(stamps)) / 60.0 >= idle_min:
            out.append((row, caches))
    return out


# pytest roots each session at `pytest-of-<user>/pytest-<N>` and rotates old sessions out by
# renaming them `garbage-<uuid>` and deleting that; one read-only directory inside makes the
# delete fail, and the garbage dir then stays forever. 7 GB of basetemps (4.2 GB of them
# `garbage-*`) sat in $TMPDIR when the volume filled on 2026-09-29.
_PYTEST_ENTRY = re.compile(r"pytest-\d+|garbage-[0-9a-f-]+")


def pytest_temp_roots() -> list[Path]:
    """Every `pytest-of-<user>` directory a lane's pytest can have written.

    pytest roots basetemp at `tempfile.gettempdir()`: $TMPDIR (/var/folders/…/T) in a login
    shell, /tmp where TMPDIR is unset. A launchd job need not inherit TMPDIR, so the per-user
    temp dir is also asked of `getconf` rather than taken from the environment.
    """
    bases = [Path(tempfile.gettempdir()), Path("/private/tmp")]
    try:
        out = subprocess.run(
            ["getconf", "DARWIN_USER_TEMP_DIR"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            bases.append(Path(out.stdout.strip()))
    except (OSError, subprocess.SubprocessError):
        pass
    roots: list[Path] = []
    seen: set[Path] = set()
    for base in bases:
        root = base / f"pytest-of-{getpass.getuser()}"
        try:
            if root.is_symlink() or not root.is_dir():
                continue
            resolved = root.resolve()
        except OSError:
            continue
        if resolved not in seen:
            seen.add(resolved)
            roots.append(root)
    return roots


def _pytest_lock_live(entry: Path, now: float, max_age_h: float) -> bool:
    """True while the pytest that owns ``entry`` (or pytest's own cleanup of it) still runs.

    pytest writes its pid into `<dir>/.lock` and removes the file at exit; a killed run leaves
    it naming a dead pid. A lock without a usable pid counts as live until the lock file is
    itself older than the age cutoff; an unreadable one always does.
    """
    lock = entry / ".lock"
    try:
        text = lock.read_text(errors="ignore").strip()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    pid = int(text) if text.isdigit() else 0
    if pid <= 0:
        m = _mtime(lock)
        return m is None or (now - m) / 3600.0 < max_age_h
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (OSError, OverflowError):
        return True  # EPERM: the process exists under another uid
    return True


def plan_pytest_prune(
    roots: list[Path],
    max_age_h: float | None,
    holders: dict[str, list[int]],
    now: float | None = None,
) -> list[tuple[Path, float]]:
    """(dir, hours idle) for pytest basetemp dirs untouched for ``max_age_h`` whose run exited.

    Age is the newest mtime among the dir and its immediate entries. A `garbage-*` dir needs
    no age: pytest renames a numbered dir to garbage only once it has judged it dead, and
    every later pytest exit renames it again (new uuid, fresh mtime) and fails the same
    delete, so its mtime never ages; on 2026-09-29 all 11 garbage dirs were re-stamped
    within the same second, twice in half an hour. A live `.lock` pid or a process cwd
    inside keeps any dir.
    """
    if max_age_h is None:
        return []
    now = time.time() if now is None else now
    out: list[tuple[Path, float]] = []
    for root in roots:
        try:
            entries = sorted(root.iterdir())
        except OSError:
            continue
        for entry in entries:
            try:
                if (
                    entry.is_symlink() or not entry.is_dir()
                ):  # `pytest-current` is a symlink
                    continue
            except OSError:
                continue
            if not _PYTEST_ENTRY.fullmatch(entry.name):
                continue
            if holders_for(entry, holders) or _pytest_lock_live(entry, now, max_age_h):
                continue
            stamps = [m for m in [_mtime(entry)] if m is not None]
            try:
                stamps += [
                    m for child in entry.iterdir() if (m := _mtime(child)) is not None
                ]
            except OSError:
                pass
            age_h = (now - max(stamps)) / 3600.0 if stamps else 0.0
            if entry.name.startswith("garbage-") or age_h >= max_age_h:
                out.append((entry, age_h))
    return out


def plan_idle_unmerged(
    rows: list[WorktreeRow],
    idle_hours: float | None,
    keep: set[str],
    exclude: list[WorktreeRow],
    now: float | None = None,
) -> list[WorktreeRow]:
    """Branched, ahead>0, edit-free trees idle >= ``idle_hours``: their directories go.

    Lanes landed onto main by format-patch replay get new hashes, so their branches stay
    `ahead>0` forever and only --include-unmerged (no idle gate) could remove them; on
    2026-09-28 about 20 such trees plus per-lane .venvs filled 24 GB in seven hours. The
    branch keeps every commit. Detached trees are never eligible: nothing else names their
    commits. A live agent is clean between commits, so the idle clock, HELD, and a live
    lock all gate it, and apply removes without --force so git re-checks cleanliness.
    """
    if idle_hours is None:
        return []
    out: list[WorktreeRow] = []
    for row in rows:
        if not row.unmerged_clean or row.branch is None:
            continue
        if row.held or row.daemon_held or row.lock_live:
            continue
        if any(k in str(row.path) for k in keep):
            continue
        if row in exclude or not row.path.exists():
            continue
        if idle_age_days(row.path, now) * 24 >= idle_hours:
            out.append(row)
    return out


def plan_aged_locks(
    rows: list[WorktreeRow],
    max_age_hours: float | None,
    keep: set[str],
) -> list[WorktreeRow]:
    return [
        row
        for row in rows
        if not any(k in str(row.path) for k in keep)
        and lock_is_aged(row, max_age_hours, row.lock)
    ]


def default_branch(repo: Path) -> str:
    """Use the remote's declared default, then the local main/master convention."""
    remote = run(
        ["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], cwd=repo
    )
    if remote.returncode == 0:
        ref = remote.stdout.strip()
        local = "refs/heads/" + ref.removeprefix("refs/remotes/origin/")
        if (
            run(["git", "show-ref", "--verify", "--quiet", local], cwd=repo).returncode
            == 0
        ):
            return local  # Landed local work may be ahead of the last remote fetch.
        return ref
    for branch in ("main", "master"):
        if (
            run(
                ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                cwd=repo,
            ).returncode
            == 0
        ):
            return branch
    raise RuntimeError(f"cannot identify default branch in {repo}")


def commit_evidence(row: WorktreeRow) -> dict[str, object]:
    """Subjects are review hints; only git cherry establishes patch equivalence."""
    base = default_branch(row.repo_root)
    head = run(["git", "rev-parse", "HEAD"], cwd=row.path, check=True).stdout.strip()
    commit_lines = run(
        ["git", "log", "--format=%H%x00%s", f"{base}..{head}"],
        cwd=row.repo_root,
        check=True,
    ).stdout.splitlines()
    commits = {
        sha: subject
        for line in commit_lines
        for sha, _, subject in [line.partition("\0")]
    }
    cherry = run(["git", "cherry", base, head], cwd=row.repo_root, check=True)
    equivalent = {
        line.split()[1] for line in cherry.stdout.splitlines() if line.startswith("- ")
    }
    subjects = set(
        run(
            ["git", "log", "--format=%s", base], cwd=row.repo_root, check=True
        ).stdout.splitlines()
    )
    no_subject = unmatched = 0
    for sha, subject in commits.items():
        if subject not in subjects:
            no_subject += 1
            unmatched += sha not in equivalent
    return {
        "default_branch": base,
        "commits_not_on_default": len(commits),
        "patch_unique_commits": len(set(commits) - equivalent),
        "no_same_subject_commits": no_subject,
        "unmatched_commits": unmatched,
    }


def suggest(
    rows: list[WorktreeRow],
    lock_max_age_hours: float | None,
    keep: set[str],
    liveness: bool,
    as_json: bool,
) -> int:
    """Read-only inventory; return before every mutation/receipt/planning path."""
    candidates: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    for row in rows:
        reasons = []
        try:
            evidence = commit_evidence(row)
            row.ahead = evidence["commits_not_on_default"]
            row.ancestor = row.ahead == 0
            row.dup = row.ahead > 0 and evidence["patch_unique_commits"] == 0
        except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
            reasons.append(f"commit evidence unknown: {error}")
            evidence = {
                key: None
                for key in (
                    "default_branch",
                    "commits_not_on_default",
                    "patch_unique_commits",
                    "no_same_subject_commits",
                    "unmatched_commits",
                )
            }
        cls = (
            "aged-lock"
            if lock_is_aged(row, lock_max_age_hours, row.lock) and liveness
            else row.classify()
        )
        if not liveness:
            reasons.append("liveness unknown")
        if row.held or row.daemon_held:
            reasons.append("live process inside")
        if row.lock_live and cls != "aged-lock":
            reasons.append(
                "live-pid lock"
                if _LOCK_PID.search(row.lock or "")
                else "pid-less lock below age threshold or unknown age"
            )
        if any(k in str(row.path) for k in keep):
            reasons.append("keep match")
        if cls == "SAFE-fresh":
            reasons.append("fresh or unknown idle clock")
        size = run(["du", "-sk", str(row.path)])
        fields = size.stdout.split()
        size_bytes = (
            int(fields[0]) * 1024
            if size.returncode == 0 and fields and fields[0].isdigit()
            else None
        )
        if size_bytes is None:
            reasons.append("size unknown")
        untracked = run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=row.path,
            check=True,
        )
        untracked_count = len([p for p in untracked.stdout.split("\0") if p])
        record: dict[str, object] = {
            "path": str(row.path),
            "repo": str(row.repo_root),
            "class": cls,
            "size_bytes": size_bytes,
            "idle_hours": row.idle_days * 24,
            "dirty_count": row.tracked_dirty + untracked_count,
            "tracked_dirty_count": row.tracked_dirty,
            "untracked_count": untracked_count,
            "lock_reason": row.lock,
            "lock_age_hours": lock_age_hours(row) if row.lock is not None else None,
            "archive_command": shlex.join(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "archive",
                    "--path",
                    str(row.path),
                ]
            ),
        }
        record.update(evidence)
        record.update(candidate=not reasons, not_candidate_reasons=reasons)
        (excluded if reasons else candidates).append(record)
    for records in (candidates, excluded):
        records.sort(
            key=lambda r: r["size_bytes"] if r["size_bytes"] is not None else -1,
            reverse=True,
        )
    if as_json:
        print(
            json.dumps(
                {
                    "candidates": candidates,
                    "not_candidates": excluded,
                    "liveness_known": liveness,
                }
            )
        )
    else:
        for record in candidates + excluded:
            print(
                f"{'CANDIDATE' if record['candidate'] else 'NOT-CANDIDATE'} {record['path']} [{record['class']}] size={record['size_bytes']}B idle={record['idle_hours']:.1f}h ahead={record['commits_not_on_default']} no-same-subject={record['no_same_subject_commits']} patch-unique={record['patch_unique_commits']} dirty={record['dirty_count']} untracked={record['untracked_count']}"
            )
            if record["lock_reason"] is not None:
                print(
                    f"  lock age={record['lock_age_hours']}h reason={record['lock_reason']}"
                )
            if record["not_candidate_reasons"]:
                print(f"  held: {'; '.join(record['not_candidate_reasons'])}")
            print(f"  {record['archive_command']}")
    return 0 if liveness else 2


def explicit_archive(path: Path) -> int:
    """Archive one human-selected tree. Age never authorizes unlocking a lock."""
    try:
        if path.is_symlink():
            raise RuntimeError("refusing symlinked worktree")
        path = path.resolve(strict=True)
        listing = run(["git", "worktree", "list", "--porcelain"], cwd=path, check=True)
        root = Path(listing.stdout.splitlines()[0].removeprefix("worktree "))
        row = next(
            (r for r in audit_repo(root, with_size=False) if r.path.resolve() == path),
            None,
        )
        if row is None:
            raise RuntimeError("--path must be a registered secondary worktree")
        holders = live_cwd_holders()
        if not liveness_known(holders) or holders_for(path, holders):
            raise RuntimeError("liveness unknown or live process inside")
        reason = current_lock(root, path)
        if (
            reason is not None
            and _LOCK_PID.search(reason)
            and not lock_is_stale(reason)
        ):
            raise RuntimeError("live-pid lock")
        res = archive_worktree(row)
        if not res.ok:
            raise RuntimeError(f"archive self-check failed: {res.reason}")
        print(
            f"ARCHIVED {path} -> {res.dir} (patch={res.patch_bytes}B untracked={res.untracked} ignored-cache={res.ignored_cache_files} ignored-cache-bytes={res.ignored_cache_bytes}B) pinned={res.ref}"
        )
        blocked = removal_hold(row)
        if blocked:
            print(
                f"HOLD {path}: {blocked}; archive complete, tree kept. Unlocking a pid-less lock requires a separate explicit decision."
            )
            return 2
        remove_worktree(root, path)
        print(f"removed {path}")
        return 0
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"HOLD {path}: {error}", file=sys.stderr)
        return 2


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "mode",
        nargs="?",
        default="audit",
        choices=("audit", "apply", "prune", "suggest", "archive"),
    )
    ap.add_argument(
        "--json", action="store_true", help="machine-readable suggest output"
    )
    ap.add_argument(
        "--path", help="one registered worktree to explicitly archive and remove"
    )
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
        help="remove unmerged worktrees with no local edits (HEAD pinned; branch kept when present)",
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
    ap.add_argument(
        "--safe-idle-min",
        type=float,
        default=60.0,
        metavar="N",
        help="default SAFE removal requires the work clock to be idle >= N minutes "
        "(default 60); fresh or unknown clocks are kept as SAFE-fresh",
    )
    ap.add_argument(
        "--archive-stale-days",
        type=float,
        default=None,
        metavar="N",
        help="audit only: suggest archiving dirty trees idle >= N days; apply never age-archives unlanded work; use archive --path explicitly",
    )
    ap.add_argument(
        "--lock-max-age-hours",
        type=float,
        default=None,
        metavar="N",
        help="audit/suggest only: mark pid-less locks older than N hours as aged-lock; never unlock or remove",
    )
    ap.add_argument(
        "--strip-idle-caches-min",
        type=float,
        default=None,
        metavar="N",
        help="delete real, git-ignored .venv/.uv-cache/.claude/cache/index-trees dirs "
        "(never symlinks, never tracked files) of any tree with no process inside and "
        "nothing touched for N minutes, live-locked trees included; audit marks would-strip",
    )
    ap.add_argument(
        "--prune-pytest-hours",
        type=float,
        default=None,
        metavar="N",
        help="delete pytest-of-<user> basetemp dirs (pytest-N, garbage-*) untouched for "
        "N hours with no live .lock pid and no process inside; audit marks would-prune-pytest",
    )
    ap.add_argument(
        "--unmerged-idle-hours",
        type=float,
        default=None,
        metavar="N",
        help="remove only clean patch-duplicate branched trees idle >= N hours; unique commits are suggestion-only",
    )
    ap.add_argument(
        "--receipt-motor",
        default="worktree_gc",
        help="janitor receipt name; a second schedule writes its own so its successes "
        "never overwrite a failed nightly's receipt",
    )
    args = ap.parse_args()
    if args.json and args.mode != "suggest":
        ap.error("--json is only supported by suggest")
    if args.mode == "archive":
        if not args.path or args.repo or args.all_projects or args.check:
            ap.error("archive requires --path TREE, without scan flags")
        return explicit_archive(Path(args.path).expanduser())
    if args.path:
        ap.error("--path is only supported by archive")
    if args.mode == "suggest" and args.check:
        ap.error("suggest cannot be combined with --check")
    if not math.isfinite(args.safe_idle_min) or args.safe_idle_min <= 0:
        ap.error("--safe-idle-min must be a positive finite number")
    if args.lock_max_age_hours is not None and (
        not math.isfinite(args.lock_max_age_hours) or args.lock_max_age_hours <= 0
    ):
        ap.error("--lock-max-age-hours must be a positive finite number")
    pruning = args.mode == "prune"
    if (
        pruning
        and args.strip_idle_caches_min is None
        and args.prune_pytest_hours is None
    ):
        ap.error("prune needs --strip-idle-caches-min and/or --prune-pytest-hours")

    with_size = not (args.no_size or args.check)
    # --check defaults to all-projects so the hub surfaces stranded work in every repo.
    repos = repo_roots(args.repo, args.all_projects or args.check)
    all_rows: list[WorktreeRow] = []
    for repo in repos:
        if not (repo / ".git").exists():
            continue
        # Missing registrations are diagnostics, never stray text in hook JSON.
        with (
            contextlib.redirect_stdout(sys.stderr)
            if args.mode == "suggest"
            else contextlib.nullcontext()
        ):
            all_rows.extend(
                audit_repo(
                    repo,
                    with_size=with_size and args.mode != "suggest",
                    safe_idle_min=args.safe_idle_min,
                )
            )

    # Liveness last, in one lsof call for every row, so it also gates --check. The
    # daemon split needs one further batched `ps` over only the PIDs lsof actually
    # found, so the cost is two calls total regardless of worktree count.
    cwd_holders = live_cwd_holders()
    if not liveness_known(cwd_holders):
        # Say WHY the scan is empty: the nightly apply has exited 2 here every
        # night since 2026-08-27 with a bare message, so the receipt could not
        # tell a timeout from a missing binary from a genuinely empty parse.
        print(
            "[DEGRADED] liveness unknown — lsof reported no cwd holders at all; "
            f"every removal is refused until the scan works ({LAST_SCAN_DIAG})",
            file=sys.stderr,
        )
    per_row = {row.path: holders_for(row.path, cwd_holders) for row in all_rows}
    daemons = daemon_pids({pid for pids in per_row.values() for pid in pids})
    for row in all_rows:
        pids = per_row[row.path]
        row.daemon_pids = tuple(sorted(pid for pid in pids if pid in daemons))
        row.daemon_held = len(row.daemon_pids)
        row.held = len(pids) - row.daemon_held

    if args.mode == "suggest":
        return suggest(
            all_rows,
            args.lock_max_age_hours,
            set(args.keep),
            liveness_known(cwd_holders),
            args.json,
        )

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
    aged_rows = (
        plan_aged_locks(all_rows, args.lock_max_age_hours, keep)
        if not pruning and liveness_known(cwd_holders)
        else []
    )
    # prune touches derived caches only, so every tree-removal plan stays empty in that mode.
    to_remove = (
        []
        if pruning
        else [
            r
            for r in all_rows
            if should_remove(
                r, args.include_unmerged, args.force_stale, args.force_all, keep
            )
        ]
    )
    idle_rows = (
        []
        if pruning
        else plan_idle_unmerged(
            [r for r in all_rows if r.dup],
            args.unmerged_idle_hours,
            keep,
            exclude=to_remove,
        )
    )
    archive_rows = (
        []
        if pruning or args.mode == "apply"
        else plan_idle_archive(
            all_rows, args.archive_stale_days, keep, exclude=to_remove + idle_rows
        )
    )
    # A tree that goes takes its caches with it, so only surviving trees are stripped.
    strip_plan: list[tuple[WorktreeRow, list[Path]]] = []
    mapping_known = True
    if args.strip_idle_caches_min is not None:
        mapped = live_mapped_holders()
        mapping_known = bool(mapped)
        if mapping_known:
            strip_plan = plan_cache_strip(
                all_rows,
                args.strip_idle_caches_min,
                keep,
                exclude=to_remove + idle_rows + archive_rows,
                mapped=mapped,
            )
        else:
            print(
                "[DEGRADED] mapped-file scan unknown — lsof -d txt reported nothing; "
                "every cache strip is refused until the scan works",
                file=sys.stderr,
            )
    pytest_plan = (
        plan_pytest_prune(pytest_temp_roots(), args.prune_pytest_hours, cwd_holders)
        if args.prune_pytest_hours is not None
        else []
    )

    for row in [] if pruning else all_rows:
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
        elif row.lock_live:
            extra = f"  ← locked: {row.lock or '(no reason given)'}"
            if row in aged_rows:
                extra += f" (aged-lock, age {lock_age_hours(row):.1f}h)"
        elif cls == "SAFE-fresh":
            extra = (
                f"  ← idle {row.idle_days * 1440:.1f}m < "
                f"--safe-idle-min {row.safe_idle_min:g} (unknown clock counts as fresh)"
            )
        elif row.branch and row.ahead > 0:
            extra = f"  commits: {commit_preview(row.repo_root, row.branch)}"
        if row.lock_stale:
            extra += f"  stale-lock ({row.lock})"
        print(
            f"{mark} {row.repo:15} {br:42} ahead={row.ahead:>3} "
            f"dirty={row.dirty:>3} {cls:9} {row.age:>14} {row.size:>6}  {row.path}{extra}"
        )

    # Stranded trees are invisible to `git worktree list`, so they are found by scanning
    # the temp roots directly rather than by asking any repo what it owns.
    stranded = [] if pruning else find_stranded(cwd_holders, with_size=with_size)
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
                why = "suggestion only: original HEAD unavailable"
            owner = s.repo_root.name if s.repo_root else "?"
            print(
                f"{'→' if s.reclaimable else ' '} {owner:15} {s.size:>6}  {s.path}  ({why})"
            )

    if not all_rows and not stranded and not pruning:
        print("(no extra worktrees)")
        # apply still runs to the receipt: a reaper that emptied every repo is a success,
        # and skipping the receipt would read as a dead motor after 36 h.
        if args.mode == "audit" and not pytest_plan:
            return 0

    if args.mode == "audit":
        for row in idle_rows:
            idle_h = idle_age_days(row.path) * 24
            print(
                f"would-reap-idle {row.path} ({row.classify()}, {row.repo}, idle {idle_h:.1f}h; "
                f"branch {row.branch} keeps {row.ahead} commit(s))"
            )
        for row in archive_rows:
            print(
                f"suggest-archive {row.path} ({row.classify()}, {row.repo}; explicit archive --path required)"
            )
        for row in aged_rows:
            print(
                f"aged-lock {row.path} (age {lock_age_hours(row):.1f}h; reason={row.lock or '(no reason given)'}; suggestion only)"
            )
        for row, caches in strip_plan:
            sizes = " ".join(
                f"{c.relative_to(row.path).as_posix()}={_du(c) if with_size else '?'}"
                for c in caches
            )
            print(f"would-strip {row.path} {sizes}")
        for path, age_h in pytest_plan:
            print(f"would-prune-pytest {path} (idle {age_h:.1f}h)")
        n_safe = sum(1 for r in all_rows if r.safe)
        n_fresh = sum(1 for r in all_rows if r.classify() == "SAFE-fresh")
        n_dup = sum(1 for r in all_rows if r.classify() == "DUP")
        n_unmerged = sum(1 for r in all_rows if r.classify() == "unmerged")
        print(
            f"\n{len(all_rows)} worktrees; {n_safe} SAFE (default apply); "
            f"{n_fresh} SAFE-fresh (kept by --safe-idle-min {args.safe_idle_min:g})"
        )
        if n_dup:
            print(
                f"  {n_dup} DUP (patches already on main) — reap: --include-unmerged --prune-branches"
            )
        if n_unmerged:
            print(
                f"  {n_unmerged} GENUINE unmerged+clean — LAND these; --include-unmerged drops dir but keeps branch"
            )
        n_locked = sum(1 for r in all_rows if r.lock_live)
        n_stale_lock = sum(1 for r in all_rows if r.lock_stale)
        if n_locked or n_stale_lock:
            print(
                f"  {n_locked} LOCKED ({len(aged_rows)} aged-lock; all kept); "
                f"{n_stale_lock} stale-lock (released right before a removal)"
            )
        if idle_rows:
            print(
                f"  {len(idle_rows)} would-reap-idle "
                f"(--unmerged-idle-hours {args.unmerged_idle_hours:g}; branches kept)"
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
        blocked = removal_hold(row)
        if blocked:
            print(f"SKIP {row.path}: {blocked}")
            continue
        try:
            if not (args.include_unmerged or args.force_stale or args.force_all):
                head = run(
                    ["git", "rev-parse", "HEAD"], cwd=row.path, check=True
                ).stdout.strip()
                if not is_ancestor(row.repo_root, head):
                    print(
                        f"SKIP {row.path}: HEAD now has unlanded commits; use suggest"
                    )
                    continue
            remove_worktree(
                row.repo_root, row.path, force=args.force_stale or args.force_all
            )
            print(f"removed {row.path}")
            removed += 1
            if args.prune_branches and row.branch and (row.stale or row.dup):
                run(["git", "branch", "-D", row.branch], cwd=row.repo_root)
                print(f"  branch -D {row.branch}")
        except (subprocess.CalledProcessError, RuntimeError, OSError) as e:
            print(
                f"FAIL {row.path}: {getattr(e, 'stderr', None) or e}", file=sys.stderr
            )

    # Only DUP trees may be age-reaped. Refresh patch evidence; --force is never used.
    reaped_idle = 0
    for row in idle_rows:
        if row.path in seen:
            continue
        seen.add(row.path)
        blocked = removal_hold(row)
        if blocked:
            print(f"SKIP {row.path}: {blocked}")
            continue
        try:
            head = run(
                ["git", "rev-parse", "HEAD"], cwd=row.path, check=True
            ).stdout.strip()
            if not all_patches_on_main(row.repo_root, head):
                print(f"SKIP {row.path}: HEAD now has unlanded commits; use suggest")
                continue
            remove_worktree(row.repo_root, row.path, force=False)
        except (subprocess.CalledProcessError, RuntimeError) as e:
            why = (
                (e.stderr or "").strip()
                if isinstance(e, subprocess.CalledProcessError)
                else e
            )
            print(
                f"SKIP {row.path}: git refused a clean removal ({why})", file=sys.stderr
            )
            continue
        print(
            f"REAPED-IDLE {row.path} (branch {row.branch} keeps {row.ahead} commit(s))"
        )
        reaped_idle += 1

    archived = 0

    stripped = 0
    for row, caches in strip_plan:
        sizes = strip_idle_caches(row.path, caches)
        if sizes:
            print(
                f"STRIPPED {row.path} " + " ".join(f"{k}={v}" for k, v in sizes.items())
            )
            stripped += 1

    pruned_pytest = 0
    for path, age_h in pytest_plan:
        size = _du(path) if with_size else "?"
        if delete_tree(path):
            print(f"PRUNED-PYTEST {path} ({size}, idle {age_h:.1f}h)")
            pruned_pytest += 1
        else:
            print(f"FAIL pytest temp {path}: still on disk", file=sys.stderr)

    # Lost administration means lost original HEAD; a clean comparison with the owner's
    # current HEAD cannot prove these leftovers have no unlanded work. Suggest only.
    reclaimed = 0
    for s in stranded:
        if not s.reclaimable:
            continue
        print(f"SUGGEST stranded {s.path} ({s.size}): kept; original HEAD unavailable")

    # A registration whose directory is already gone is the mirror image of a stranded
    # tree, and it is what makes `worktree list` report paths that do not exist.
    for repo in [] if pruning else repos:
        run(["git", "worktree", "prune"], cwd=repo)

    parts = (
        []
        if pruning
        else [
            f"removed {removed}/{len(to_remove)} worktrees",
            f"reclaimed {reclaimed} stranded",
        ]
    )
    if args.unmerged_idle_hours is not None and not pruning:
        parts.append(
            f"reaped idle-unmerged {reaped_idle}/{len(idle_rows)} (branches kept)"
        )
    if args.archive_stale_days is not None and not pruning:
        parts.append(f"archived {archived}/{len(archive_rows)} (under {ARCHIVE_ROOT})")
    if args.strip_idle_caches_min is not None:
        parts.append(f"stripped {stripped}/{len(strip_plan)} trees' caches")
    if args.prune_pytest_hours is not None:
        parts.append(f"pruned {pruned_pytest}/{len(pytest_plan)} pytest temp dirs")
    print("\n" + "; ".join(parts))
    # Janitor effect-receipt (observe 2026-08-11 B3): principal = trees removed+reclaimed;
    # in prune mode, trees stripped + pytest dirs pruned.
    try:
        from janitor_receipt import write_receipt

        write_receipt(
            args.receipt_motor,
            principal_metric=(
                stripped + pruned_pytest
                if pruning
                else removed + reclaimed + archived + reaped_idle
            ),
            error_class=None if mapping_known else "mapped_scan_unknown",
            detail=(
                f"removed={removed} reclaimed_stranded={reclaimed} reaped_idle={reaped_idle} "
                f"archived={archived} stripped={stripped} pruned_pytest={pruned_pytest} "
                f"archive_root={ARCHIVE_ROOT}"
            ),
        )
    except Exception as e:  # noqa: BLE001 — receipt writes must never fail the GC
        print(f"janitor_receipt write skipped: {e}", file=sys.stderr)
    return 0 if mapping_known else 2


if __name__ == "__main__":
    sys.exit(main())
