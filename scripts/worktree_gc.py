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
  landed         — dirty, but all commits, tracked changes and untracked bytes are
                   durable at their paths on the default branch (tip or history);
                   opt-in archive only
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
apply --archive-landed-idle-hours N: archive and remove landed dirty trees idle >= N
  hours, after repeating landing/liveness checks and a settled archive-manifest check
audit/suggest --lock-max-age-hours N: label old pid-less locks aged-lock, read-only
suggest [--json]: size-ranked reclaim suggestions, never changes anything
archive --path TREE: explicitly archive, pin HEAD and remove this one tree
apply --force-stale: also stale (ahead==0) with dirty trees (discards wt edits)
apply --force-all: everything except --keep, held, and live-locked trees (dangerous)
apply --strip-idle-caches-min N: also delete the derived caches (.venv, .uv-cache,
  .claude/cache/index-trees, .claude/cache/source-epochs) of any tree with no process
  inside and nothing touched for N minutes; a live lock keeps the tree, never its
  caches (audit marks would-strip)
apply --prune-pytest-hours N: also delete pytest-of-<user> basetemp dirs untouched for N
  hours whose pytest has exited (audit marks would-prune-pytest)
prune: only those two steps; never removes a worktree (the low-disk guard's mode)

Evidence: standing #g metafix — worktree leak is harness hygiene, not telos.

Linked-worktree content inventory (landed removal and explicit archive):
  Tracked working files    PROVEN-LANDED by exact mode/blob; PRESERVED by HEAD+patch.
  Untracked working files  PROVEN-LANDED by exact mode/blob; PRESERVED by untracked.tgz.
  Ignored working files    Non-cache work HOLD automatically; archive PRESERVED in
                           ignored.tgz, including large files, symlinks, empty dirs,
                           venvs/index-trees/source-epochs. Cache names are never a
                           content proof.
                           The exact regular current-session-id UUID marker is
                           archive-only metadata; other ignored content still HOLDs.
  Index entries/blobs      PROVEN-LANDED individually; staged-then-overwritten HOLD
                           if either entry is unproven. Archive write-tree on a COPY of saved index,
                           check every entry, commit-tree parent HEAD, pin separately
                           at refs/wt-archive/*-index-* (index-ref.txt). Raw git-index
                           preserves flags. Unmerged/intent-to-add/split index HOLD.
  Index extensions         HOLD resolve-undo, unknown extensions and unsupported v4;
                           only TREE (checked via exact write-tree), EOIE/IEOT offsets
                           are accepted. No extension may hide unpinned object roots.
  HEAD literal/symref/SHA  Proof captures all three; final manifest and removal bind
                           exact values. Archive HEAD pinned at refs/wt-archive/*.
  Checked-out branch/SHA  Same exact binding; shared branch survives (optional branch
                           pruning HOLDs shared logs/config; otherwise uses SHA-CAS).
                           Symbolic chains HOLD.
  refs/worktree/*          PROVEN-LANDED only for commit ancestors of default, else HOLD.
  refs/bisect/*            Same (pending bisect state separately HOLD).
  refs/rewritten/*         Same (pending rebase state separately HOLD).
  Other local refs        HOLD; unknown storage/backend never silently omitted.
  Per-worktree reflogs     Both old/new objects must be default ancestors or reachable
                           from HEAD (PRESERVED by HEAD pin), else HOLD. Raw log/ref
                           bytes PRESERVED in git-state.tgz for archive routes.
  Stash entries            HOLD unless every valid entry names an exact branch currently
                           checked out only in another live worktree of this repository.
  Pending operations       HOLD rebase/merge/cherry-pick/revert/sequencer/bisect/
                           autostash, including pseudorefs and lock files.
  config.worktree          Regular file, Git-parsed without includes; only allowlisted
                           agent.session-id and Codex's exact __none__ environment
                           marker accepted. Raw bytes archived; other values HOLD.
  codex-thread.json        Regular JSON object: exactly version=1 and UUID ownerThreadId;
                           raw bytes archived. App ownership is suggestion-only: only
                           explicit archive --path may remove the tree, even if landed.
  Sparse-checkout          HOLD info/sparse-checkout or sparse configuration/index flags.
  Submodules/gitlinks      HOLD initialized/populated; empty gitlinks must be unchanged.
  Nested repositories      HOLD, ignored caches included (child refs/objects unknown),
                           except inside a real, ignored, untracked strip-class
                           .claude/cache tree (index-trees, source-epochs): rebuilt from
                           Git tree OIDs and stripped wholesale; archive keeps the bytes.
                           .venv/.uv-cache repositories still HOLD (editable checkouts).
                           The exact empty regular .uv-cache/sdists-v9/.git marker
                           carries no Git roots and is preserved as ordinary content.
  Notes                    Shared loose/packed refs/notes and their objects survive removal.
  Shared ref storage       HOLD symlinked paths/parents under the common directory or
                           candidate-contained refs/notes, packed-refs, refs/stash,
                           and logs/refs (including all descendant refs/reflogs).
  LFS objects/pointers     HOLD storage/config/.lfsconfig/pointers; Git pins no LFS payload.
                           Shared lock metadata without any object payloads survives
                           outside the checkout; candidate-contained/symlinked storage HOLDs.
  Other pseudorefs/admin   ORIG_HEAD must be a default ancestor; raw bytes archived.
                           HOLD FETCH_HEAD/AUTO_MERGE/etc and unknown admin paths.
  Rerere state             Empty MERGE_RR has no object roots; raw bytes archived.
                           Nonempty MERGE_RR HOLD (resolution roots not inventoried).
  Commit message draft     COMMIT_EDITMSG must equal HEAD's raw commit message;
                           then PROVEN in HEAD's graph/raw bytes archived, else HOLD.
  Object storage/proof     HOLD alternates/shallow/grafts/replace refs or filters: borrowed
                           storage/rewritten ancestry/transformed blobs not proven.
                           HOLD Git storage overrides, promisor stores, symlinked
                           object storage or a common directory inside this checkout.
  Missing checkout         HOLD registration; never blanket-prune another admin directory.
  Structural admin files  commondir/gitdir are linkage, regenerated by worktree repair;
                           locked uses existing veto; dead-pid lock bytes are saved
                           under ARCHIVE_ROOT/<repo>/locks before authorized unlock.
                           HEAD/index/logs/known local
                           refs are the only accepted content-bearing admin paths.
  Unsupported/unreadable   HOLD special files, symlinked admin state, unknown Git evidence.

Shared ordinary refs/tags/remotes and their reflogs/config/objects remain in the
common Git directory; removal never deletes them. Unreachable objects with no
index/ref/reflog/operation root have Git's ordinary retention, not a worktree
restoration promise. The separate explicitly requested cache-strip mode discards
derived caches; it is not a landed proof or archive. Writes after the final
manifest/identity read remain the documented deletion race.
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
import hashlib
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
import uuid
from bisect import bisect_left
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
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
    landed: bool = False  # complete dirty work proven present on the default branch
    hold_reason: str | None = None  # evidence outside the parent landing/archive proof
    blocking_paths: tuple[str, ...] = ()  # exact same-path landing evidence missing
    codex_owner_thread: str | None = None  # app liveness signal; removal is manual

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
        if self.held or self.daemon_held or self.lock_live or self.hold_reason:
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
        return self.ahead > 0 and self.dirty == 0 and not self.hold_reason

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
        if self.hold_reason:
            return "HOLD"
        if self.blocking_paths:
            return "HOLD"
        if self.dirty and self.landed:
            return "landed"
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
    # A lock reason can include unique human text. Preserve its bytes before an
    # otherwise-authorized stale unlock, including ordinary nonarchive removal.
    try:
        marker = _linked_admin(row.path) / "locked"
        with os.fdopen(os.open(marker, os.O_RDONLY | os.O_NOFOLLOW), "rb") as source:
            payload = source.read()
        dest = _fresh_dir(ARCHIVE_ROOT / row.repo / "locks" / _archive_name(row))
        saved = dest / "locked"
        saved.write_bytes(payload)
        with os.fdopen(os.open(marker, os.O_RDONLY | os.O_NOFOLLOW), "rb") as source:
            unchanged = source.read() == payload
        if (
            saved.read_bytes() != payload
            or not unchanged
            or current_lock(row.repo_root, row.path) != lock
        ):
            return "stale lock changed while preserving its bytes"
    except (RuntimeError, OSError) as error:
        return f"stale lock could not be preserved: {error}"
    out = run(["git", "worktree", "unlock", str(row.path)], cwd=row.repo_root)
    if out.returncode != 0:
        return f"stale lock could not be released: {out.stderr.strip()[:160]}"
    print(f"unlocked {row.path} (stale lock: {lock})")
    return None


def removal_hold(row: WorktreeRow, *, operator_archive: bool = False) -> str | None:
    """Refresh cwd and lock vetoes immediately before a registered-tree removal."""
    blocked = _worktree_state_hold(row.path)
    if blocked:
        return blocked
    if not operator_archive and _codex_owner_thread(row.path):
        return "codex-app-owned"
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


def all_patches_on_main(repo: Path, branch: str, *, base: str | None = None) -> bool:
    """True if every commit on `branch` has an equivalent patch already on main.

    `git cherry main <branch>` prints '- <sha>' for commits whose patch is
    already upstream, '+ <sha>' for genuinely-unmerged ones. All '-' (and at
    least one line) => the branch is a pure duplicate, safe to reap even though
    `ahead>0`. This is the cherry-picked/rebased-then-stranded case.
    """
    try:
        base = default_branch(repo) if base is None else base
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


DERIVED_CACHE_ALLOWLIST: tuple[str, ...] = (
    ".claude/cache",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    ".uv-cache",
)


def _under_derived_cache(rel: str) -> bool:
    parts = Path(rel).parts
    return any(
        parts[i : i + len(Path(cache).parts)] == Path(cache).parts
        for cache in DERIVED_CACHE_ALLOWLIST
        for i in range(len(parts))
    )


def _archived_session_marker(wt: Path, rel: str) -> bool:
    """Recognize only the generated UUID file; every byte still needs an archive."""
    if rel != ".claude/current-session-id":
        return False
    marker = wt / rel
    metadata = marker.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size not in (36, 37):
        return False
    return bool(
        re.fullmatch(
            rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\n?",
            marker.read_bytes(),
        )
    )


def _hidden_work(wt: Path, *, exclude_archived_caches: bool = False) -> tuple[int, int]:
    """Ignored bytes are work; only a verified archive may cover cache exclusions."""
    flags = run(["git", "ls-files", "-v", "-z"], cwd=wt, check=True).stdout
    flagged = sum(
        bool(entry) and (entry[0].islower() or entry[0] == "S")
        for entry in flags.split("\0")
    )
    ignored: set[str] = set()
    for extra in ([], ["--directory"]):
        paths = run(
            [
                "git",
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "-z",
                *extra,
            ],
            cwd=wt,
            check=True,
        ).stdout.split("\0")
        if extra:
            # --directory may collapse an unignored container whose contents are
            # all ignored (e.g. .claude/ containing only cache/). Confirm which
            # directories themselves are ignored; the file enumeration is exact.
            checked = subprocess.run(
                ["git", "check-ignore", "--stdin", "-z"],
                cwd=wt,
                input="\0".join(p for p in paths if p).encode(),
                capture_output=True,
                check=False,
            )
            if checked.returncode not in (0, 1):
                raise RuntimeError("ignored-directory evidence unknown")
            paths = os.fsdecode(checked.stdout).split("\0")
        ignored.update(
            p
            for p in paths
            if p
            and not (
                exclude_archived_caches
                and (_under_derived_cache(p) or _archived_session_marker(wt, p))
            )
        )
    return flagged, len(ignored)


def _tree_entries(
    wt: Path, ref: str, *, path: str | None = None
) -> dict[str, tuple[str, str]]:
    output = subprocess.run(
        ["git", "ls-tree", "-r", "-z", ref]
        + (["--", f":(literal){path}"] if path is not None else []),
        cwd=wt,
        capture_output=True,
        check=True,
    ).stdout
    entries = {}
    for entry in output.split(b"\0"):
        if entry:
            metadata, name = entry.split(b"\t", 1)
            mode, _kind, blob = metadata.decode().split()
            entries[os.fsdecode(name)] = (mode, blob)
    return entries


def _git_operation_hold(wt: Path) -> str | None:
    """Pending Git operations own state/objects the ordinary archive cannot restore."""
    try:
        admin = _linked_admin(wt)
        names = set(os.listdir(admin))
        operations = {
            "rebase-merge",
            "rebase-apply",
            "MERGE_HEAD",
            "CHERRY_PICK_HEAD",
            "REVERT_HEAD",
            "sequencer",
            "BISECT_LOG",
        }
        pending = names & operations
        pending.update(name for name in names if "autostash" in name.lower())
        refs = run(
            ["git", "for-each-ref", "--format=%(refname)"], cwd=wt, check=True
        ).stdout.splitlines()
        pending.update(ref for ref in refs if "autostash" in ref.lower())
        if pending:
            return f"unfinished Git operation: {', '.join(sorted(pending))}"
    except (OSError, subprocess.CalledProcessError) as error:
        return f"[DEGRADED] Git operation state unknown: {error}"
    return None


def _submodule_hold(wt: Path) -> str | None:
    """Parent Git cannot prove or archive bytes inside populated gitlinks."""
    paths = {
        rel for rel, (mode, _) in _tree_entries(wt, "HEAD").items() if mode == "160000"
    }
    output = run(["git", "ls-files", "--stage", "-z"], cwd=wt, check=True).stdout
    for entry in output.split("\0"):
        if entry:
            metadata, rel = entry.split("\t", 1)
            if metadata.split()[0] == "160000":
                paths.add(rel)
    for rel in sorted(paths):
        child = wt / rel
        marker = child / ".git"
        if marker.exists() or marker.is_symlink():
            return (
                f"initialized submodule {rel!r}: child work is not proven or archived"
            )
        if child.is_dir():
            with os.scandir(child) as entries:
                if next(entries, None) is not None:
                    return (
                        f"populated uninitialized submodule {rel!r}: "
                        "child work is not proven or archived"
                    )
    return None


LOCAL_REF_PREFIXES = ("refs/worktree/", "refs/bisect/", "refs/rewritten/")
ADMIN_FILES = (
    "HEAD",
    "index",
    "ORIG_HEAD",
    "MERGE_RR",
    "COMMIT_EDITMSG",
    "commondir",
    "gitdir",
    "locked",
    "config.worktree",
    "codex-thread.json",
)
ADMIN_DIRS = ("logs", "refs")
ADMIN_NAMES = frozenset((*ADMIN_FILES, *ADMIN_DIRS))
WORKTREE_CONFIG_KEYS = frozenset({"agent.session-id"})


def _worktree_config_hold(path: Path, wt: Path) -> str | None:
    # --file disables includes by default. In particular, include.path is itself
    # rejected rather than allowing its target to influence this inventory.
    result = subprocess.run(
        ["git", "config", "--file", str(path), "--null", "--list"],
        cwd=wt,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return "unparsable worktree administrative configuration: config.worktree"
    for entry in result.stdout.split(b"\0"):
        if entry:
            raw_key, separator, value = entry.partition(b"\n")
            key = os.fsdecode(raw_key)
            if (
                key == "codex.localenvironmentconfigpath"
                and separator
                and value == b"__none__"
            ):
                continue
            if key not in WORKTREE_CONFIG_KEYS:
                return f"unsupported config.worktree key: {key}"
    return None


def _codex_owner_thread(wt: Path) -> str | None:
    """Return validated app ownership; malformed/present metadata never means absent."""
    path = _linked_admin(wt) / "codex-thread.json"
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("unsupported administrative type: codex-thread.json")

    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate codex-thread.json key: {key}")
            result[key] = value
        return result

    try:
        with os.fdopen(
            os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb"
        ) as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("codex-thread.json is no longer a regular file")
            data = json.load(source, object_pairs_hook=unique_object)
        if not isinstance(data, dict) or set(data) != {"version", "ownerThreadId"}:
            raise ValueError("expected exactly version and ownerThreadId")
        if type(data["version"]) is not int or data["version"] != 1:
            raise ValueError("expected version 1")
        owner = data["ownerThreadId"]
        if not isinstance(owner, str):
            raise TypeError("ownerThreadId must be a UUID string")
        uuid.UUID(owner)
        return owner
    except (TypeError, ValueError, UnicodeError) as error:
        raise ValueError(f"invalid codex-thread.json: {error}") from error


def _head_identity(wt: Path) -> dict[str, object]:
    """Bind the literal HEAD, its symbolic target, and both resolved object IDs."""
    admin = _linked_admin(wt)
    raw = (admin / "HEAD").read_bytes()
    symbolic = run(["git", "symbolic-ref", "--quiet", "HEAD"], cwd=wt)
    if symbolic.returncode not in (0, 1):
        raise RuntimeError("HEAD symbolic-ref evidence unknown")
    branch = symbolic.stdout.strip() if symbolic.returncode == 0 else None
    head = run(
        ["git", "rev-parse", "--verify", "HEAD^{commit}"], cwd=wt, check=True
    ).stdout.strip()
    branch_sha = None
    if branch:
        if raw != f"ref: {branch}\n".encode() or not branch.startswith("refs/heads/"):
            raise RuntimeError("unsupported symbolic HEAD chain/target")
        branch_sha = run(
            ["git", "rev-parse", "--verify", branch], cwd=wt, check=True
        ).stdout.strip()
        if branch_sha != head:
            raise RuntimeError("HEAD and checked-out branch moved during identity read")
    elif raw != f"{head}\n".encode():
        raise RuntimeError("unsupported noncanonical/noncommit detached HEAD")
    if (admin / "HEAD").read_bytes() != raw:
        raise RuntimeError("HEAD moved during identity read")
    return {
        "type": "git-head",
        "literal": os.fsdecode(raw),
        "symbolic_ref": branch,
        "head_sha": head,
        "branch_sha": branch_sha,
    }


def _default_identity(repo: Path) -> dict[str, object]:
    ref = default_branch(repo)
    sha = run(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=repo, check=True
    ).stdout.strip()
    return {"type": "git-default", "ref": ref, "sha": sha}


def _walk_error(error: OSError) -> None:
    raise error


def _local_refs(wt: Path) -> dict[str, str]:
    refs = run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname) %(objectname)",
            *LOCAL_REF_PREFIXES,
        ],
        cwd=wt,
        check=True,
    ).stdout
    return dict(line.split(" ", 1) for line in refs.splitlines())


def _index_state_hold(
    wt: Path, admin: Path, oid_bytes: int, *, raw: bytes | None = None
) -> str | None:
    """Closed index envelope; native ls-files omits resolve-undo/extension roots.

    Git's index-format specification defines v2/v3 entry alignment and extension
    envelopes. Unknown/v4 layouts HOLD, not guessed offsets. TREE roots must also
    survive the archive's exact native write-tree verification.
    """
    raw = (admin / "index").read_bytes() if raw is None else raw
    limit = len(raw) - oid_bytes
    if raw[:4] != b"DIRC" or limit < 12:
        return "unreadable index format"
    version, count = int.from_bytes(raw[4:8], "big"), int.from_bytes(raw[8:12], "big")
    if version not in (2, 3):
        return f"unsupported index version: {version}"
    digest = hashlib.new("sha1" if oid_bytes == 20 else "sha256", raw[:limit]).digest()
    if digest != raw[limit:]:
        return "index checksum differs"
    offset = 12
    entries = {}
    for _ in range(count):
        start = offset
        flags_at = start + 40 + oid_bytes
        if flags_at + 2 > limit:
            return "truncated index entry"
        flags = int.from_bytes(raw[flags_at : flags_at + 2], "big")
        if flags & 0x3000:
            return "unmerged index has unpreserved stage roots"
        offset = flags_at + 2
        if flags & 0x4000:
            if version != 3:
                return "unsupported extended index flags"
            offset += 2
        end = raw.find(b"\0", offset, limit)
        if end < 0:
            return "unterminated index path"
        mode = int.from_bytes(raw[start + 24 : start + 28], "big")
        entries[os.fsdecode(raw[offset:end])] = (
            f"{mode:o}",
            raw[start + 40 : flags_at].hex(),
        )
        offset = start + ((end + 1 - start + 7) // 8) * 8
    cached_trees: list[tuple[str, int, str]] = []
    while offset < limit:
        if offset + 8 > limit:
            return "truncated index extension"
        signature = raw[offset : offset + 4]
        size = int.from_bytes(raw[offset + 4 : offset + 8], "big")
        payload = raw[offset + 8 : offset + 8 + size]
        offset += 8 + size
        if offset > limit:
            return "truncated index extension payload"
        if signature not in (b"TREE", b"EOIE", b"IEOT"):
            return f"unpreserved index extension: {signature!r}"
        if signature == b"TREE":
            cursor = 0

            def check_tree(parent: str, tree_payload: bytes = payload) -> None:
                nonlocal cursor
                end_name = tree_payload.index(b"\0", cursor)
                name = os.fsdecode(tree_payload[cursor:end_name])
                prefix = f"{parent}{name}/" if name else parent
                end_header = tree_payload.index(b"\n", end_name + 1)
                count, children = map(
                    int, tree_payload[end_name + 1 : end_header].split(b" ")
                )
                if count < -1 or children < 0:
                    raise ValueError("invalid TREE cache counts")
                cursor = end_header + 1
                if count >= 0:
                    if cursor + oid_bytes > len(tree_payload):
                        raise ValueError("truncated TREE cache object id")
                    oid = tree_payload[cursor : cursor + oid_bytes].hex()
                    cursor += oid_bytes
                    cached_trees.append((prefix, count, oid))
                for _ in range(children):
                    check_tree(prefix)

            check_tree("")
            if cursor != len(payload):
                return "TREE cache has unparsed bytes"
    if offset != limit:
        return "index entry/extension boundary unknown"
    _check_index_tree_cache(wt, entries, cached_trees, oid_bytes)
    return None


def _validate_native_tree_names(wt: Path, oids: list[str], oid_bytes: int) -> None:
    """Reject ambiguous raw components in one batch, before sharing tree views."""
    output = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=wt,
        input=("\n".join(oids) + "\n").encode("ascii"),
        capture_output=True,
        check=True,
    ).stdout
    cursor = 0
    for oid in oids:
        header_end = output.index(b"\n", cursor)
        object_id, kind, size = output[cursor:header_end].split(b" ")
        if object_id != oid.encode("ascii") or kind != b"tree":
            raise ValueError("TREE cache does not match native tree objects")
        length = int(size)
        start = header_end + 1
        end = start + length
        if length < 0 or end >= len(output) or output[end : end + 1] != b"\n":
            raise ValueError("TREE cache has truncated native tree evidence")
        tree = output[start:end]
        cursor = end + 1
        offset = 0
        while offset < len(tree):
            mode_end = tree.index(b" ", offset)
            mode = tree[offset:mode_end]
            if not mode or any(byte not in b"01234567" for byte in mode):
                raise ValueError("TREE cache has malformed native tree entry")
            name_end = tree.index(b"\0", mode_end + 1)
            name = tree[mode_end + 1 : name_end]
            if not name or name in (b".", b"..") or b"/" in name or b"\0" in name:
                raise ValueError(f"TREE cache has invalid native tree name: {name!r}")
            offset = name_end + 1 + oid_bytes
            if offset > len(tree):
                raise ValueError("TREE cache has truncated native tree entry")
    if cursor != len(output):
        raise ValueError("TREE cache has unparsed native tree evidence")


def _check_index_tree_cache(
    wt: Path,
    entries: dict[str, tuple[str, str]],
    cached_trees: list[tuple[str, int, str]],
    oid_bytes: int,
) -> None:
    """Prove every cached subtree against native evidence without repeated walks.

    Recursive ls-tree includes directory OIDs, so descendants share one sorted
    leaf listing after raw entry names are validated. Invalidated parents have
    no OID; their valid children still get independent native listings.
    Evidence is local to this index snapshot.
    """
    if not cached_trees:
        return
    oids = list(dict.fromkeys(oid for _, _, oid in cached_trees))
    tree_oids = dict.fromkeys(oids)
    listed_oids: set[str] = set()
    listings = []
    for oid in oids:
        if oid not in listed_oids:
            output = subprocess.run(
                ["git", "ls-tree", "-r", "-t", "-z", oid],
                cwd=wt,
                capture_output=True,
                check=True,
            ).stdout
            leaves: dict[str, tuple[str, str]] = {}
            subtrees = [(oid, "")]
            seen_paths: set[str] = set()
            for record in output.split(b"\0"):
                if not record:
                    continue
                metadata, name = record.split(b"\t", 1)
                mode, kind, object_id = metadata.decode().split()
                rel = os.fsdecode(name)
                if rel in seen_paths:
                    raise ValueError(
                        f"TREE cache has duplicate native tree path: {rel!r}"
                    )
                seen_paths.add(rel)
                if kind == "tree":
                    subtrees.append((object_id, rel + "/"))
                else:
                    leaves[rel] = (mode, object_id)
            native_paths = sorted(leaves)
            for subtree_oid, _ in subtrees:
                tree_oids[subtree_oid] = None
                listed_oids.add(subtree_oid)
            listings.append((native_paths, leaves, subtrees))

    # A flattened path can hide a literal slash in any ancestor, including an
    # uncached tree. Validate all listed tree objects before publishing views.
    _validate_native_tree_names(wt, list(tree_oids), oid_bytes)
    views: dict[str, tuple[list[str], dict[str, tuple[str, str]], str]] = {}
    for native_paths, leaves, subtrees in listings:
        for subtree_oid, native_prefix in subtrees:
            views.setdefault(subtree_oid, (native_paths, leaves, native_prefix))

    paths = sorted(entries)

    def bounds(names: list[str], prefix: str) -> tuple[int, int]:
        # Every nonempty prefix ends in '/'; '0' is its immediate successor.
        return (
            (bisect_left(names, prefix), bisect_left(names, prefix[:-1] + "0"))
            if prefix
            else (0, len(names))
        )

    for prefix, count, oid in cached_trees:
        first, last = bounds(paths, prefix)
        if count != last - first:
            raise ValueError("TREE cache does not match index entries")
        native_paths, leaves, native_prefix = views[oid]
        native_first, native_last = bounds(native_paths, native_prefix)
        if count != native_last - native_first:
            raise ValueError("TREE cache does not match index entries")
        for i in range(count):
            path, native_path = paths[first + i], native_paths[native_first + i]
            if (
                path.removeprefix(prefix) != native_path.removeprefix(native_prefix)
                or entries[path] != leaves[native_path]
            ):
                raise ValueError("TREE cache does not match index entries")


def _live_peer_branches(wt: Path, common: Path) -> set[str]:
    """Exact branch refs backed by a different, existing checkout of this repository."""
    records = run(
        ["git", "worktree", "list", "--porcelain", "-z"], cwd=wt, check=True
    ).stdout
    branches: set[str] = set()
    for record in records.split("\0\0"):
        if not record:
            continue
        fields = record.split("\0")
        if not fields[0].startswith("worktree "):
            raise RuntimeError("stash peer worktree inventory malformed")
        refs = [
            field.removeprefix("branch ")
            for field in fields
            if field.startswith("branch ")
        ]
        if not refs:
            continue
        if len(refs) != 1:
            raise RuntimeError("stash peer branch inventory ambiguous")
        peer = Path(fields[0].removeprefix("worktree "))
        if peer.resolve() == wt.resolve() or not peer.is_dir():
            continue
        location = run(
            [
                "git",
                "rev-parse",
                "--path-format=absolute",
                "--show-toplevel",
                "--git-common-dir",
            ],
            cwd=peer,
            check=True,
        ).stdout.splitlines()
        if len(location) != 2:
            raise RuntimeError("stash peer repository location unknown")
        if (
            Path(location[0]).resolve() != peer.resolve()
            or Path(location[1]).resolve() != common.resolve()
        ):
            continue
        current = run(["git", "symbolic-ref", "--quiet", "HEAD"], cwd=peer)
        if current.returncode not in (0, 1):
            raise RuntimeError("stash peer HEAD evidence unknown")
        if current.returncode == 0 and current.stdout.strip() == refs[0]:
            branches.add(refs[0])
    return branches


def _ref_storage_hold(path: Path, common: Path, candidate: Path) -> str | None:
    """Check the storage tree and its ancestors within the common directory."""

    def storage_paths() -> Iterator[Path]:
        for ancestor in (path, *path.parents):
            if not ancestor.is_relative_to(common):
                break
            yield ancestor
        if path.is_dir():
            for directory, dirs, files in os.walk(
                path, followlinks=False, onerror=_walk_error
            ):
                yield from (Path(directory) / name for name in dirs + files)

    for storage in storage_paths():
        if storage.is_symlink() or storage.resolve().is_relative_to(candidate):
            return f"undurable shared ref storage: {path} via {storage}"
    return None


def _shared_refs_hold(wt: Path, common: Path, branch: str | None) -> str | None:
    """External notes survive; proof-altering refs and stashes without live peers hold."""
    candidate = wt.resolve()
    for relative in ("refs/notes", "packed-refs", "refs/stash", "logs/refs"):
        blocked = _ref_storage_hold(common / relative, common, candidate)
        if blocked:
            return blocked
    output = run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname) %(objectname)",
            "refs/stash",
            "refs/replace",
        ],
        cwd=wt,
        check=True,
    ).stdout
    refs = dict(line.split(" ", 1) for line in output.splitlines())
    replacements = [ref for ref in refs if ref.startswith("refs/replace/")]
    if replacements:
        return f"proof-altering refs: {', '.join(replacements)}"
    tip = refs.pop("refs/stash", None)
    if refs:
        return f"unattributed stash/proof refs: {', '.join(refs)}"
    log = common / "logs/refs/stash"
    if tip is None and not log.exists():
        return None
    if tip is None or not log.is_file():
        return "unattributed stash: missing ref or regular reflog"
    raw = log.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        return "unattributed stash: empty or unterminated reflog"
    peers = _live_peer_branches(wt, common)
    oid = rb"[0-9a-f]{%d}" % len(tip)
    record_pattern = re.compile(
        rb"(" + oid + rb") (" + oid + rb") "
        rb"[^<>\x00-\x20](?:[^<>\x00-\x1f]*[^<>\x00-\x20])? "
        rb"<[^<>\x00-\x20]+> [0-9]+ "
        rb"[+-](?:[01][0-9]|2[0-3])[0-5][0-9]\t([^\x00\r\n]*)"
    )
    entries: list[tuple[str, str]] = []
    for line in raw[:-1].split(b"\n"):
        record = record_pattern.fullmatch(line)
        if record is None:
            return "unattributed stash: unreadable reflog entry"
        old, new = (value.decode("ascii") for value in record.group(1, 2))
        origin = re.fullmatch(rb"(?:WIP on|On) ([^\s:]+): .*", record[3])
        if origin is None:
            return "unattributed stash entry in refs/stash"
        origin_ref = "refs/heads/" + os.fsdecode(origin[1])
        if run(["git", "check-ref-format", origin_ref], cwd=wt).returncode != 0:
            return "unattributed stash: invalid branch in reflog"
        if origin_ref == branch:
            return f"stash attributed to worktree branch: {origin_ref}"
        if origin_ref not in peers:
            return f"unattributed stash: no different live worktree for {origin_ref}"
        entries.append((old, new))
    # A missing entry or ref/log mismatch could hide this worktree's stash. Check
    # both reflog roots; old-only objects have no branch-bearing entry to inspect.
    known = {new for _, new in entries}
    if (
        entries[-1][1] != tip
        or "0" * len(tip) in known
        or any(old != "0" * len(tip) and old not in known for old, _ in entries)
    ):
        return "unattributed stash: inconsistent ref/reflog roots"
    return None


def _worktree_state_hold(wt: Path) -> str | None:
    """Closed inventory: every unhandled admin/storage state holds all removal routes."""
    try:
        overrides = {
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_NAMESPACE",
            "GIT_SHALLOW_FILE",
            "GIT_REPLACE_REF_BASE",
        } & os.environ.keys()
        if overrides:
            return f"unsupported Git storage override: {', '.join(sorted(overrides))}"
        blocked = _git_operation_hold(wt) or _submodule_hold(wt)
        if blocked:
            return blocked
        admin = _linked_admin(wt)
        common = Path(
            run(
                ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                cwd=wt,
                check=True,
            ).stdout.strip()
        )
        if common.resolve().is_relative_to(wt.resolve()):
            return "common Git storage lies inside the removed worktree"
        for name, target in (("gitdir", wt / ".git"), ("commondir", common)):
            data = (admin / name).read_bytes()
            if len(data.splitlines()) != 1 or not data.endswith(b"\n"):
                return f"uncovered structural administrative bytes: {name}"
            link = Path(os.fsdecode(data[:-1]))
            if not link.is_absolute():
                link = admin / link
            if link.resolve() != target.resolve():
                return f"unexpected administrative linkage: {name}"
        identity = _head_identity(wt)
        branch = identity["symbolic_ref"]
        blocked = _shared_refs_hold(wt, common, str(branch) if branch else None)
        if blocked:
            return blocked
        head = str(identity["head_sha"])
        base = run(
            ["git", "rev-parse", "--verify", f"{default_branch(wt)}^{{commit}}"],
            cwd=wt,
            check=True,
        ).stdout.strip()
        allowed = ADMIN_NAMES
        for path in admin.iterdir():
            if path.is_symlink() or path.name not in allowed:
                return f"uncovered worktree administrative state: {path.name}"
            if path.name not in ADMIN_DIRS and not path.is_file():
                return f"unsupported worktree administrative type: {path.name}"
            if path.name == "config.worktree":
                blocked = _worktree_config_hold(path, wt)
                if blocked:
                    return blocked
            if path.name == "codex-thread.json":
                _codex_owner_thread(wt)
            if path.name == "MERGE_RR" and path.stat().st_size:
                return "uncovered rerere resolution state: MERGE_RR"
            if path.name == "COMMIT_EDITMSG":
                commit = subprocess.run(
                    ["git", "cat-file", "commit", head],
                    cwd=wt,
                    capture_output=True,
                    check=True,
                ).stdout
                if path.read_bytes() != commit.split(b"\n\n", 1)[1]:
                    return "unpreserved commit-message draft: COMMIT_EDITMSG"
            if path.name == "ORIG_HEAD":
                oid = path.read_text().strip()
                if (
                    not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid)
                    or run(
                        ["git", "merge-base", "--is-ancestor", oid, base], cwd=wt
                    ).returncode
                    != 0
                ):
                    return "unlanded or unreadable worktree-local ref: ORIG_HEAD"
        # Cheap closed admin rejection precedes potentially many cached-tree
        # queries; unknown metadata needs no expensive index proof.
        blocked = _index_state_hold(wt, admin, len(head) // 2)
        if blocked:
            return blocked
        reachable: dict[str, bool] = {head: True, base: True}
        for root_name in ("refs", "logs"):
            root = admin / root_name
            if not root.exists():
                continue
            if not root.is_dir():
                return f"unsupported worktree administrative type: {root_name}"
            for directory, dirs, files in os.walk(
                root, followlinks=False, onerror=_walk_error
            ):
                for name in dirs + files:
                    path = Path(directory) / name
                    rel = path.relative_to(admin).as_posix()
                    ref = rel.removeprefix("logs/")
                    containers = {
                        "refs",
                        "refs/worktree",
                        "refs/bisect",
                        "refs/rewritten",
                    }
                    if path.is_symlink() or (
                        ref != "HEAD"
                        and ref not in containers
                        and not ref.startswith(LOCAL_REF_PREFIXES)
                    ):
                        return f"uncovered worktree administrative state: {rel}"
                    if path.is_dir():
                        continue
                    if not path.is_file():
                        return f"unsupported worktree administrative type: {rel}"
                    if root_name == "logs":
                        for line in path.read_bytes().splitlines():
                            fields = line.split(b" ", 2)
                            if len(fields) != 3:
                                return f"unreadable worktree reflog: {rel}"
                            for oid in fields[:2]:
                                sha = oid.decode("ascii")
                                if len(sha) != len(head) or not re.fullmatch(
                                    r"[0-9a-f]+", sha
                                ):
                                    return f"invalid worktree reflog object: {rel}"
                                if set(sha) == {"0"}:
                                    continue
                                # HEAD's reachable history is preserved by its pin;
                                # abandoned commits/blobs have no durable root.
                                if sha not in reachable:
                                    kind = run(
                                        ["git", "cat-file", "-t", sha],
                                        cwd=wt,
                                        check=True,
                                    ).stdout.strip()
                                    reachable[sha] = kind == "commit" and any(
                                        run(
                                            [
                                                "git",
                                                "merge-base",
                                                "--is-ancestor",
                                                sha,
                                                tip,
                                            ],
                                            cwd=wt,
                                        ).returncode
                                        == 0
                                        for tip in (base, head)
                                    )
                                if not reachable[sha]:
                                    return f"unpreserved worktree reflog object: {rel} {sha}"
        local = _local_refs(wt)
        for ref, oid in local.items():
            kind = run(
                ["git", "cat-file", "-t", oid], cwd=wt, check=True
            ).stdout.strip()
            if (
                kind != "commit"
                or run(
                    ["git", "merge-base", "--is-ancestor", oid, base], cwd=wt
                ).returncode
                != 0
            ):
                return f"unlanded worktree-local ref: {ref} {oid}"
        # Catch invalid loose refs which for-each-ref may warn about and omit.
        root = admin / "refs"
        if root.exists():
            for path in root.rglob("*"):
                if path.is_file() and path.relative_to(admin).as_posix() not in local:
                    return f"unreadable worktree-local ref: {path.relative_to(admin)}"
        for rel in ("objects/info/alternates", "info/grafts", "shallow"):
            if (common / rel).exists() or (common / rel).is_symlink():
                return f"unsupported shared object storage/proof: {rel}"
        lfs = common / "lfs"
        if lfs.exists() or lfs.is_symlink():
            blocked = _ref_storage_hold(lfs, common, wt.resolve())
            if blocked:
                return blocked
            objects = lfs / "objects"
            if not lfs.is_dir() or (
                objects.exists()
                and (
                    not objects.is_dir()
                    or any(
                        files
                        for _directory, _dirs, files in os.walk(
                            objects, onerror=_walk_error
                        )
                    )
                )
            ):
                return "unsupported shared object storage/proof: lfs"
        for directory, dirs, files in os.walk(
            common / "objects", followlinks=False, onerror=_walk_error
        ):
            if Path(directory).is_symlink() or any(
                (Path(directory) / name).is_symlink() for name in dirs + files
            ):
                return "symlinked Git object storage is not durably inventoried"
            if any(name.endswith(".promisor") for name in files):
                return "promisor object storage is not fully local"
        config = run(
            [
                "git",
                "config",
                "--get-regexp",
                r"^(lfs\.|filter\.|core\.sparsecheckout|extensions\.(refstorage|partialclone)|remote\..*\.promisor)",
            ],
            cwd=wt,
        )
        if config.returncode not in (0, 1):
            return "[DEGRADED] storage/config evidence unknown"
        # Merely installing the global LFS driver does not create LFS content.
        # Storage settings/custom filters hold; pointers below hold independently
        # in HEAD, index and working files (including overwritten staged pointers).
        unsupported_config = [
            line
            for line in config.stdout.splitlines()
            if not line.startswith("filter.lfs.")
            and line != "lfs.repositoryformatversion 0"
        ]
        if unsupported_config or (wt / ".lfsconfig").exists():
            return "unsupported LFS/filter/sparse/ref-storage configuration"
        for args in (("--cached",), (head,)):
            pointers = run(
                [
                    "git",
                    "grep",
                    "--quiet",
                    "--fixed-strings",
                    "-e",
                    "version https://git-lfs.github.com/spec/v1",
                    *args,
                ],
                cwd=wt,
            )
            if pointers.returncode == 0:
                return "LFS pointer in HEAD/index has unpreserved payload"
            if pointers.returncode != 1:
                return "[DEGRADED] LFS pointer evidence unknown"
        if run(
            ["git", "rev-parse", "--shared-index-path"], cwd=wt, check=True
        ).stdout.strip():
            return "split index depends on unarchived sharedindex"
        # Materialized .claude/cache trees are rebuilt from Git tree OIDs and stripped
        # wholesale, so a repository inside one (each genomics source-epoch tree) is
        # cache content; archive keeps its bytes. A tracked or unignored cache is no
        # candidate. .venv/.uv-cache repositories still HOLD: package managers put
        # editable checkouts there (`pip install -e git+...` clones into .venv/src).
        derived = [
            cache
            for cache in strip_candidates(wt)
            if cache.relative_to(wt).as_posix() in _CACHE_STRIP_DIRS
        ]
        for directory, dirs, files in os.walk(
            wt, followlinks=False, onerror=_walk_error
        ):
            if directory != str(wt) and ".git" in dirs + files:
                relative = Path(directory).relative_to(wt)
                marker = (Path(directory) / ".git").lstat()
                if not (
                    relative.parts == (".uv-cache", "sdists-v9")
                    and stat.S_ISREG(marker.st_mode)
                    and marker.st_size == 0
                ) and not any(Path(directory).is_relative_to(c) for c in derived):
                    return f"nested repository: {relative}"
            for name in files:
                path = Path(directory) / name
                if not stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink():
                    return f"unsupported working-file type: {path.relative_to(wt)}"
                if path.is_file() and not path.is_symlink():
                    with path.open("rb") as source:
                        if source.read(43).startswith(
                            b"version https://git-lfs.github.com/spec/v1"
                        ):
                            return f"LFS pointer with unpreserved payload: {path.relative_to(wt)}"
    except (
        RuntimeError,
        OSError,
        ValueError,
        UnicodeError,
        subprocess.CalledProcessError,
    ) as error:
        return f"[DEGRADED] worktree inventory unknown: {error}"
    return None


def _working_entry(wt: Path, rel: str, object_format: str) -> tuple[str, str] | None:
    path = wt / rel
    try:
        info = path.lstat()
    except (FileNotFoundError, NotADirectoryError):
        return None
    if stat.S_ISDIR(info.st_mode):
        # A former tracked file is absent; index/untracked loops prove descendants.
        return None
    if stat.S_ISLNK(info.st_mode):
        mode, data = "120000", os.fsencode(os.readlink(path))
    elif stat.S_ISREG(info.st_mode):
        mode = "100755" if info.st_mode & stat.S_IXUSR else "100644"
        data = path.read_bytes()
    else:
        raise ValueError(f"unsupported working-file type: {path}")
    # Raw Git blob identity, without filters or one Git subprocess per file.
    blob = hashlib.new(object_format, f"blob {len(data)}\0".encode() + data).hexdigest()
    return mode, blob


def _historical_path_entries(
    repo: Path, start: str, default: str, rel: str
) -> set[tuple[str, str] | None]:
    """Exact entries at one literal path in the pinned default branch's history.

    Full history includes side branches and merges; never follow renames to a
    different path. None is a deletion, also valid when replaced by a directory.
    """
    commits = run(
        [
            "git",
            "log",
            "--full-history",
            "--format=%H",
            f"{start}..{default}",
            "--",
            f":(literal){rel}",
        ],
        cwd=repo,
        check=True,
    ).stdout.splitlines()
    return {_tree_entries(repo, commit, path=rel).get(rel) for commit in commits}


def dirty_work_on_default(
    repo: Path,
    wt: Path,
    *,
    expected_head: dict[str, object] | None = None,
    blocking_paths: list[str] | None = None,
) -> bool:
    """Prove exact index AND working content for every locally changed path.

    Accept the exact default tip entry, or the exact entry at the same path in
    default history since the lane's merge-base. An unchanged HEAD entry is
    already durable when HEAD is an ancestor; newly staged/index-only entries
    must independently pass the same proof as working content.
    Pin the default tree by SHA for one consistent proof. Disable optional index
    refreshes: even a read-only diff must not reset the real worktree's idle clock.
    Unknown evidence holds the tree, including missing or unreadable files.
    """
    try:
        identity = _head_identity(wt)
        default_identity = _default_identity(repo)
        if expected_head is not None and identity != expected_head:
            return False
        if _worktree_state_hold(wt) or any(
            _hidden_work(wt, exclude_archived_caches=True)
        ):
            return False
        status = run(
            [
                "git",
                "--no-optional-locks",
                "status",
                "--porcelain=v2",
                "-z",
                "--ignore-submodules=none",
                "--untracked-files=all",
            ],
            cwd=wt,
            check=True,
        ).stdout
        # Parent patches and ls-files omit untracked/modified content inside a
        # submodule. Such work has neither a landing proof nor a restorable archive.
        records = iter(status.split("\0"))
        for entry in records:
            if entry.startswith(("1 ", "2 ", "u ")):
                # v2 -z type-2 records have TWO NUL-delimited paths. The source
                # name is arbitrary data, even when it looks like a status record.
                fields = entry.split(" ", {"1": 8, "2": 9, "u": 10}[entry[0]])
                if len(fields) != {"1": 9, "2": 10, "u": 11}[entry[0]]:
                    raise ValueError("malformed porcelain-v2 status record")
                if entry.startswith("2 ") and not next(records, None):
                    raise ValueError("rename status is missing its original path")
                sub = fields[2]
                if sub.startswith("S") and sub[1:] != "...":
                    return False
        base = str(default_identity["sha"])
        head = str(identity["head_sha"])
        if len(head) not in (40, 64):
            raise ValueError("unknown Git object format")
        object_format = "sha1" if len(head) == 40 else "sha256"
        commits = run(
            ["git", "rev-list", f"{base}..{head}"], cwd=repo, check=True
        ).stdout
        if commits and not all_patches_on_main(repo, head, base=base):
            return False
        baseline = _tree_entries(wt, head)
        landed = _tree_entries(repo, base)
        history: dict[str, set[tuple[str, str] | None]] = {}
        start = None

        def proven(rel: str, entry: tuple[str, str] | None) -> bool:
            nonlocal start
            if entry == landed.get(rel):
                return True
            # No new work in this entry; its exact HEAD tree is already reachable.
            if not commits and entry == baseline.get(rel):
                return True
            if rel not in history:
                if start is None:
                    bases = run(
                        ["git", "merge-base", "--all", head, base],
                        cwd=repo,
                        check=True,
                    ).stdout.splitlines()
                    if len(bases) != 1:
                        raise ValueError("ambiguous lane/default merge-base")
                    start = bases[0]
                history[rel] = _historical_path_entries(repo, start, base, rel)
            return entry in history[rel]

        blocked: set[str] = set()
        output = subprocess.run(
            ["git", "ls-files", "--stage", "-z"],
            cwd=wt,
            capture_output=True,
            check=True,
        ).stdout
        index = {}
        for entry in output.split(b"\0"):
            if not entry:
                continue
            metadata, name = entry.split(b"\t", 1)
            mode, blob, stage = metadata.decode().split()
            if stage != "0":
                return False
            index[os.fsdecode(name)] = (mode, blob)
        for rel in baseline.keys() | index.keys():
            original, staged = baseline.get(rel), index.get(rel)
            # Dirty submodules were vetoed above. A changed gitlink has no raw
            # working-file blob and must stay rather than borrowing a parent proof.
            if any(e and e[0] == "160000" for e in (original, staged)):
                if original != staged:
                    return False
                continue
            working = _working_entry(wt, rel, object_format)
            if (original != staged or original != working) and (
                not proven(rel, staged) or not proven(rel, working)
            ):
                blocked.add(rel)
        others = run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=wt,
            check=True,
        ).stdout.split("\0")
        for rel in others:
            if not rel or _under_derived_cache(rel):
                continue
            working = _working_entry(wt, rel, object_format)
            if working is None or not proven(rel, working):
                blocked.add(rel)
        if blocking_paths is not None:
            blocking_paths.extend(sorted(blocked))
        return (
            not blocked
            and _head_identity(wt) == identity
            and _default_identity(repo) == default_identity
        )
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"[DEGRADED] landed evidence unknown for {wt}: {error}", file=sys.stderr)
        return False


def audit_repo(
    repo: Path,
    with_size: bool = True,
    safe_idle_min: float = 60.0,
    *,
    on_row: Callable[[WorktreeRow], None] | None = None,
    only_path: Path | None = None,
    check_landing: bool = True,
) -> list[WorktreeRow]:
    """Inventory safety state; skipped landing checks never grant landed status."""
    name = repo.name
    rows: list[WorktreeRow] = []
    for wt, branch, lock in parse_worktrees(repo):
        if only_path is not None and wt.resolve() != only_path.resolve():
            continue
        if any(s in str(wt) for s in SKIP_PATH_SUBSTR):
            continue
        if not wt.exists():
            # Registered but the directory is gone (e.g. a scratchpad worktree whose
            # session dir was deleted out from under git). No cwd exists to run
            # anything in — subprocess with a missing cwd raises FileNotFoundError,
            # which killed the whole nightly GC 10 nights running (2026-08). The
            # Admin state may own unique objects; automatic prune is forbidden.
            print(
                f"  (HOLD prunable registration: {wt} — directory gone; admin state unproven)",
                flush=True,
            )
            continue
        # --no-optional-locks: a plain `git status` rewrites the index stat cache,
        # which would reset the idle clock (index mtime) on every nightly audit.
        st = run(
            [
                "git",
                "--no-optional-locks",
                "status",
                "--porcelain",
                "--ignore-submodules=none",
            ],
            cwd=wt,
            check=True,
        )
        tracked_dirty = sum(
            1 for ln in st.stdout.splitlines() if not ln.startswith("??")
        )
        # Porcelain already omits ignored paths (.venv, caches), so every `??` line is a
        # real file somebody put here on purpose.
        untracked_work = sum(1 for ln in st.stdout.splitlines() if ln.startswith("??"))
        flagged, ignored = _hidden_work(wt)
        hold_reason = _worktree_state_hold(wt)
        try:
            codex_owner_thread = _codex_owner_thread(wt)
        except (RuntimeError, OSError, ValueError) as error:
            codex_owner_thread = None
            hold_reason = hold_reason or f"unreadable codex-thread.json: {error}"
        tracked_dirty += flagged
        untracked_work += ignored
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
            if ahead > 0:
                dup = all_patches_on_main(repo, sha)
        blocking_paths: list[str] = []
        landed = (
            check_landing
            and not hold_reason
            and bool(tracked_dirty or untracked_work)
            and dirty_work_on_default(repo, wt, blocking_paths=blocking_paths)
        )
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
                hold_reason=hold_reason,
                landed=landed,
                blocking_paths=tuple(blocking_paths),
                codex_owner_thread=codex_owner_thread,
            )
        )
        if on_row is not None:
            on_row(rows[-1])
    return rows


def print_audit_row(
    row: WorktreeRow, *, remove: bool = False, aged_lock: bool = False
) -> None:
    cls = row.classify()
    mark = "→" if remove else " "
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
        if aged_lock:
            extra += f" (aged-lock, age {lock_age_hours(row):.1f}h)"
    elif row.hold_reason:
        extra = f"  ← {row.hold_reason}"
    elif row.blocking_paths:
        extra = f"  ← unproven paths: {json.dumps(row.blocking_paths)}"
    elif cls == "SAFE-fresh":
        extra = (
            f"  ← idle {row.idle_days * 1440:.1f}m < "
            f"--safe-idle-min {row.safe_idle_min:g} (unknown clock counts as fresh)"
        )
    elif row.branch and row.ahead > 0:
        extra = f"  commits: {commit_preview(row.repo_root, row.branch)}"
    if row.lock_stale:
        extra += f"  stale-lock ({row.lock})"
    if row.codex_owner_thread:
        extra += f"  codex-app-owned (owner thread {row.codex_owner_thread}; manual archive only)"
    print(
        f"{mark} {row.repo:15} {br:42} ahead={row.ahead:>3} "
        f"dirty={row.dirty:>3} {cls:9} {row.age:>14} {row.size:>6}  {row.path}{extra}",
        flush=True,
    )


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
    if row.lock_live or row.hold_reason or row.codex_owner_thread:
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


def remove_worktree(
    repo: Path,
    wt: Path,
    force: bool = True,
    *,
    manifest: dict[str, dict[str, object]] | None = None,
    expected_head: dict[str, object] | None = None,
    operator_archive: bool = False,
) -> None:
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
    blocked = _worktree_state_hold(wt)
    if blocked:
        raise RuntimeError(blocked)
    if not operator_archive and _codex_owner_thread(wt):
        raise RuntimeError("codex-app-owned")
    if manifest is None and any(_hidden_work(wt)):
        raise RuntimeError("unarchived ignored bytes or index flags: HOLD")
    identity = _head_identity(wt)
    if expected_head is not None and identity != expected_head:
        raise RuntimeError("HEAD/branch differs from the proven removal identity")
    if manifest is not None and identity != manifest.get(".git/resolved-HEAD"):
        raise RuntimeError("HEAD/branch differs from the proven archive identity")
    head = str(identity["head_sha"])
    if not is_ancestor(repo, head):
        ref = _pin_ref(repo, wt.name, time.strftime("%Y%m%d"), head)
        print(f"pinned {wt} HEAD={head} at {ref}")
    cmd = ["git", "worktree", "remove", *(["--force"] if force else []), str(wt)]

    def checked_remove() -> None:
        blocked = _worktree_state_hold(wt)
        if blocked:
            raise RuntimeError(blocked)
        if not operator_archive and _codex_owner_thread(wt):
            raise RuntimeError("codex-app-owned")
        if manifest is None and any(_hidden_work(wt)):
            raise RuntimeError("unarchived ignored bytes or index flags: HOLD")
        if (
            manifest is None
            and force
            and run(
                [
                    "git",
                    "--no-optional-locks",
                    "status",
                    "--porcelain",
                    "--ignore-submodules=none",
                    "--untracked-files=all",
                ],
                cwd=wt,
                check=True,
            ).stdout
        ):
            raise RuntimeError("unarchived working/index bytes: HOLD")
        # Never pin a newly resolved HEAD in place of the SHA proven above.
        if manifest is not None and _content_manifest(wt) != manifest:
            raise RuntimeError("quarantined content manifest differs from archive")
        if _head_identity(wt) != identity:
            raise RuntimeError("HEAD/branch moved before removal")
        if manifest is not None and _default_identity(wt) != manifest.get(
            ".git/default-branch"
        ):
            raise RuntimeError("default branch moved before removal")
        # Read-only derived trees (source-epochs) stop `git worktree remove` partway,
        # after Git unregistered the tree, and the manifest route then refuses to
        # finish. Proof is complete here; only cache directories gain owner rwx.
        for cache in strip_candidates(wt):
            make_writable(cache)
        run(cmd, cwd=repo, check=True)

    try:
        checked_remove()
    except subprocess.CalledProcessError as first:
        if "permission denied" in (first.stderr or "").lower() and wt.exists():
            print(
                f"RETRY {wt}: permission denied; owner-writable directories, retry once"
            )
            # Unlink needs parent permissions, never a regular file's write bit.
            make_writable(wt)
            admin = _admin_dir_of(wt)
            # Git may have already unregistered this checked tree. Retry only a
            # still-registered tree; otherwise use the half-removal recovery below.
            if (wt / ".git").exists() and (not admin or (wt / admin).exists()):
                try:
                    checked_remove()
                except subprocess.CalledProcessError:
                    if wt.exists() and (wt / ".git").exists():
                        admin = _admin_dir_of(wt)
                        if not admin or (wt / admin).exists():
                            raise
                else:
                    if not wt.exists():
                        return
        # Half-removed is not a state to leave behind. If git already unregistered
        # it, the directory is now inert and only wastes disk; delete it and prune.
        if manifest is not None:
            # A failed guarded deletion may have partially removed the tree.
            # Preserve the remainder; never widen the race with a blind rmtree.
            raise
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
    if wt.exists():
        raise RuntimeError(f"{wt} still on disk after removal")


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
QUARANTINE_SETTLE_SECONDS = 1.0
MAX_ARCHIVED_CACHE_BYTES = 20 * 1024 * 1024
CACHE_DIRS: tuple[str, ...] = (".venv", ".uv-cache", "node_modules")
# Rederivable, git-ignored caches a lane builds inside its own tree: `uv run` from the tree
# root syncs a ~735 MB .venv, and the genomics pre-commit materializes the staged index
# read-only under .claude/cache/index-trees (~430 MB). Across 27 lane trees these, plus 7 GB
# of pytest basetemps, took the data volume to 334 MB free on 2026-09-29 06:05, the second
# ENOSPC in two days. Genomics' .claude/cache/source-epochs holds read-only materialized
# source trees (~200 MB each, every one a self-contained nested repository) rebuilt from
# their Git tree OID; on 2026-10-19 their nested repositories blocked archive for 12
# genomics trees.
STRIP_DIRS: tuple[str, ...] = (
    ".venv",
    ".uv-cache",
    ".claude/cache/index-trees",
    ".claude/cache/source-epochs",
)
# Strip-class trees inside .claude/cache: the small-report ignored-cache.tgz skips them;
# the lossless ignored.tgz still carries their bytes, like .venv's.
_CACHE_STRIP_DIRS: tuple[str, ...] = tuple(
    rel for rel in STRIP_DIRS if rel.startswith(".claude/cache/")
)


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
        [
            "git",
            "--no-optional-locks",
            "status",
            "--porcelain",
            "-z",
            "-uall",
            "--ignore-submodules=none",
        ],
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


def _tracked_patch(wt: Path, *, cached: bool = False) -> bytes:
    # --no-ext-diff: the operator's diff.external=difft writes non-patches otherwise.
    return subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-c",
            "diff.autoRefreshIndex=false",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--binary",
            "--ignore-submodules=none",
            *(["--cached"] if cached else []),
            "HEAD",
        ],
        cwd=wt,
        capture_output=True,
        check=True,
    ).stdout


def _write_patch(wt: Path, dest: Path) -> None:
    dest.write_bytes(_tracked_patch(wt))


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
        if cur == head:
            return ref
        if not cur:
            created = run(["git", "update-ref", ref, head, "0" * len(head)], cwd=repo)
            if created.returncode == 0:
                return ref
            if not run(
                ["git", "rev-parse", "--verify", "-q", ref], cwd=repo
            ).stdout.strip():
                raise subprocess.CalledProcessError(
                    created.returncode, created.args, created.stdout, created.stderr
                )
        n += 1
        ref = f"{base}-{n}"


def _prune_branch(repo: Path, branch: str, proven_sha: str) -> None:
    """Never delete moved refs or common branch metadata outside this archive."""
    ref = f"refs/heads/{branch}"
    log = Path(
        run(
            ["git", "rev-parse", "--path-format=absolute", "--git-path", f"logs/{ref}"],
            cwd=repo,
            check=True,
        ).stdout.strip()
    )
    config = run(
        ["git", "config", "--get-regexp", rf"^branch\.{re.escape(branch)}\."], cwd=repo
    )
    if log.exists() or log.is_symlink() or config.returncode != 1:
        print(f"HOLD branch {branch}: shared reflog/config not archived")
        return
    # Pin before dropping even an ancestor ref: default may change later. Native
    # compare-and-delete refuses a concurrent branch movement atomically.
    _pin_ref(repo, branch.replace("/", "-"), time.strftime("%Y%m%d"), proven_sha)
    result = run(["git", "update-ref", "-d", ref, proven_sha], cwd=repo)
    if result.returncode:
        print(f"HOLD branch {branch}: ref moved or deletion failed")
    else:
        print(f"pruned branch {branch} at proven {proven_sha}")


@dataclass
class ArchiveResult:
    dir: Path
    ok: bool
    reason: str = ""
    patch_bytes: int = 0
    untracked: int = 0
    ref: str = ""
    index_ref: str = ""
    ignored_cache_files: int = 0
    ignored_cache_bytes: int = 0


def _linked_admin(wt: Path) -> Path:
    if (wt / ".git").is_symlink():
        raise RuntimeError("symlinked worktree Git marker")
    admin = _admin_dir_of(wt)
    if not admin:
        raise RuntimeError("manifest requires a linked worktree's Git directory")
    path = Path(admin) if Path(admin).is_absolute() else wt / admin
    if path.is_symlink():
        raise RuntimeError("symlinked worktree Git directory")
    return path


def _content_manifest(wt: Path) -> dict[str, dict[str, object]]:
    """Hash every path, including ignored caches; never follow a symlink.

    Directory-relative, no-follow opens prevent a swapped symlink from redirecting
    traversal. In-flight changes and unsupported file types hold rather than omit
    entries. mtimes are stability evidence during a scan, never content identity.
    Logical .git/HEAD and .git/index entries cover the external Git state.
    """
    manifest: dict[str, dict[str, object]] = {}
    head_identity = _head_identity(wt)
    default_identity = _default_identity(wt)
    local_refs = _local_refs(wt)

    def identity(info: os.stat_result) -> tuple[int, ...]:
        return (
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )

    def file_entry(fd: int, name: str, path: str, info: os.stat_result) -> None:
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError(f"manifest expected regular file: {path}")
        with os.fdopen(
            os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd),
            "rb",
        ) as source:
            if identity(info) != identity(os.fstat(source.fileno())):
                raise RuntimeError(f"manifest file changed: {path}")
            digest = hashlib.file_digest(source, "sha256").hexdigest()
            if identity(info) != identity(os.fstat(source.fileno())):
                raise RuntimeError(f"manifest file changed while hashing: {path}")
        manifest[path] = {
            "type": "file",
            "mode": stat.S_IMODE(info.st_mode),
            "size": info.st_size,
            "sha256": digest,
        }
        if identity(info) != identity(os.stat(name, dir_fd=fd, follow_symlinks=False)):
            raise RuntimeError(f"manifest path changed: {path}")

    def walk(fd: int, rel: str) -> None:
        before = os.fstat(fd)
        manifest[rel] = {
            "type": "directory",
            "mode": stat.S_IMODE(before.st_mode),
            "size": 0,
            "sha256": None,
        }
        with os.scandir(fd) as entries:
            names = sorted(entry.name for entry in entries)
        for name in names:
            path = f"{rel}/{name}" if rel != "." else name
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(
                    name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
                )
                try:
                    if identity(info) != identity(os.fstat(child)):
                        raise RuntimeError(f"manifest directory changed: {path}")
                    walk(child, path)
                finally:
                    os.close(child)
            elif stat.S_ISREG(info.st_mode):
                file_entry(fd, name, path, info)
            elif stat.S_ISLNK(info.st_mode):
                data = os.fsencode(os.readlink(name, dir_fd=fd))
                manifest[path] = {
                    "type": "symlink",
                    "mode": stat.S_IMODE(info.st_mode),
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            else:
                raise RuntimeError(f"manifest unsupported file type: {path}")
            if identity(info) != identity(
                os.stat(name, dir_fd=fd, follow_symlinks=False)
            ):
                raise RuntimeError(f"manifest path changed: {path}")
        if identity(before) != identity(os.fstat(fd)):
            raise RuntimeError(f"manifest directory changed while scanning: {rel}")

    root_fd = os.open(wt, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        walk(root_fd, ".")
    finally:
        os.close(root_fd)
    # .git is only a pointer. Bind the external staged state and HEAD too;
    # quarantine repair's administrative gitdir file is deliberately excluded.
    admin_fd = os.open(_linked_admin(wt), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        admin_before = os.fstat(admin_fd)
        names = set(os.listdir(admin_fd))
        if names - ADMIN_NAMES:
            raise RuntimeError(
                f"uncovered administrative state during manifest: {sorted(names - ADMIN_NAMES)}"
            )
        manifest[".git/admin-names"] = {"type": "git-admin", "names": sorted(names)}
        for name in ("HEAD", "index"):
            info = os.stat(name, dir_fd=admin_fd, follow_symlinks=False)
            file_entry(admin_fd, name, f".git/{name}", info)
        for name in ADMIN_FILES:
            if name in {"HEAD", "index", "gitdir"}:
                continue
            try:
                info = os.stat(name, dir_fd=admin_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            file_entry(admin_fd, name, f".git/{name}", info)
        for name in ("logs", "refs"):
            try:
                child = os.open(
                    name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=admin_fd
                )
            except FileNotFoundError:
                continue
            try:
                walk(child, f".git/{name}")
            finally:
                os.close(child)
        if identity(admin_before) != identity(os.fstat(admin_fd)):
            raise RuntimeError("administrative directory changed during manifest")
    finally:
        os.close(admin_fd)
    if (
        _head_identity(wt) != head_identity
        or _local_refs(wt) != local_refs
        or _default_identity(wt) != default_identity
    ):
        raise RuntimeError("HEAD/branch/local refs moved during manifest capture")
    manifest[".git/resolved-HEAD"] = head_identity
    manifest[".git/default-branch"] = default_identity
    manifest[".git/local-refs"] = {"type": "git-refs", "refs": local_refs}
    return manifest


def _verify_archive_payloads(
    archive_path: Path, manifest: dict[str, dict[str, object]], required: set[str]
) -> None:
    """Bind actual tar payloads to captured state, even if source bytes revert."""
    have = set()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive:
            have.add(member.name.rstrip("/"))
            expected = manifest.get(member.name.rstrip("/"))
            if expected is None:
                raise RuntimeError(f"archive manifest has no entry: {member.name}")
            if member.isdir():
                kind, size, digest = "directory", 0, None
            elif member.issym():
                data = os.fsencode(member.linkname)
                kind, size, digest = (
                    "symlink",
                    len(data),
                    hashlib.sha256(data).hexdigest(),
                )
            elif member.isfile() or member.islnk():
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError(f"archive payload unreadable: {member.name}")
                with source:
                    digest = hashlib.file_digest(source, "sha256").hexdigest()
                kind = "file"
                size = (
                    manifest.get(member.linkname, {}).get("size")
                    if member.islnk()
                    else member.size
                )
            else:
                raise RuntimeError(f"unsupported archive member: {member.name}")
            if expected != {
                "type": kind,
                "mode": member.mode,
                "size": size,
                "sha256": digest,
            }:
                raise RuntimeError(
                    f"archive payload differs from manifest: {member.name}"
                )
    if have != required:
        raise RuntimeError(
            f"archive manifest coverage differs: missing={sorted(required - have)!r}, "
            f"unexpected={sorted(have - required)!r}"
        )


def _verify_tracked_payload(
    wt: Path, dest: Path, head: str, manifest: dict[str, dict[str, object]]
) -> set[str]:
    """Rebuild HEAD plus the saved patch without touching the source index/files.

    Captured index paths also cover staged additions omitted from the patch.
    Compare restored content, types and Git's executable bit to the captured
    manifest, rather than accepting a merely reverse-applicable patch subset.
    """
    with tempfile.TemporaryDirectory(prefix="wt-archive-check-") as temporary:
        root = Path(temporary)
        index = root / "index"
        shutil.copyfile(dest / "git-index", index)
        env = {**os.environ, "GIT_INDEX_FILE": str(index)}

        def git(*args: str) -> bytes:
            return subprocess.run(
                ["git", *args], cwd=wt, env=env, capture_output=True, check=True
            ).stdout

        captured = {
            os.fsdecode(rel) for rel in git("ls-files", "-z").split(b"\0") if rel
        }
        baseline = _tree_entries(wt, head)
        git("read-tree", head)
        patch = dest / "tracked.patch"
        if patch.stat().st_size:
            git("apply", "--cached", str(patch))
        restored = {
            os.fsdecode(rel) for rel in git("ls-files", "-z").split(b"\0") if rel
        }
        checkout = root / "checkout"
        checkout.mkdir()
        git("checkout-index", "--all", f"--prefix={checkout}/")
        for rel in baseline.keys() | captured | restored:
            expected = manifest.get(rel)
            if baseline.get(rel, (None,))[0] == "160000" and (
                expected is None or expected["type"] == "directory"
            ):
                continue
            path = checkout / rel
            if rel not in restored:
                if expected and expected["type"] != "directory":
                    raise RuntimeError(
                        f"tracked payload missing from manifest restore: {rel}"
                    )
                continue
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                data = os.fsencode(os.readlink(path))
                kind, size = "symlink", len(data)
                digest = hashlib.sha256(data).hexdigest()
            elif stat.S_ISREG(info.st_mode):
                kind, size = "file", info.st_size
                with path.open("rb") as source:
                    digest = hashlib.file_digest(source, "sha256").hexdigest()
            else:
                raise RuntimeError(f"tracked restore has unsupported type: {rel}")
            if (
                expected is None
                or (kind, size, digest)
                != (expected["type"], expected["size"], expected["sha256"])
                or (
                    kind == "file"
                    and bool(info.st_mode & stat.S_IXUSR)
                    != bool(expected["mode"] & stat.S_IXUSR)
                )
            ):
                raise RuntimeError(f"tracked payload differs from manifest: {rel}")
        return restored


def _required_untracked_payloads(
    wt: Path, manifest: dict[str, dict[str, object]], restored: set[str]
) -> set[str]:
    """Required payloads come from captured content and proven Git restoration.

    Query ignore rules for these manifest paths, never re-enumerate files on disk:
    a transiently missing path must still require a matching archived payload.
    """
    candidates = {
        rel
        for rel, entry in manifest.items()
        if entry["type"] != "directory"
        and rel != ".git"
        and not rel.startswith(".git/")
        and rel not in restored
        and not _under_cache(rel)
    }
    if not candidates:
        return set()
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin", "-z"],
        cwd=wt,
        input=b"\0".join(os.fsencode(rel) for rel in sorted(candidates)) + b"\0",
        capture_output=True,
        check=False,
    )
    if ignored.returncode not in (0, 1):
        raise RuntimeError("untracked archive coverage ignore evidence unknown")
    return candidates - {os.fsdecode(rel) for rel in ignored.stdout.split(b"\0") if rel}


def _archive_ignored_cache(wt: Path, dest: Path) -> tuple[int, int]:
    """Save small regular cache files; exclude strip-class trees and all symlinks."""
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
                and (Path(directory) / d).relative_to(wt).as_posix()
                not in _CACHE_STRIP_DIRS
            ]
            for name in sorted(files):
                path = Path(directory) / name
                st = path.lstat()
                if (
                    not stat.S_ISREG(st.st_mode)
                    or st.st_size > MAX_ARCHIVED_CACHE_BYTES
                ):
                    continue
                with os.fdopen(
                    os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb"
                ) as source:
                    st = os.fstat(source.fileno())
                    if (
                        not stat.S_ISREG(st.st_mode)
                        or st.st_size > MAX_ARCHIVED_CACHE_BYTES
                    ):
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


def _verify_git_state_roots(
    wt: Path, dest: Path, manifest: dict[str, dict[str, object]], head: str
) -> None:
    """Validate object roots from verified archived bytes, never a later live view."""
    base = str(manifest[".git/default-branch"]["sha"])
    known = {head: "commit", base: "commit"}
    landed: dict[str, bool] = {base: True}
    reachable: dict[str, bool] = {head: True, base: True}
    refs = manifest[".git/local-refs"]["refs"]

    def check_oid(oid: str, *, default_only: bool) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid):
            raise RuntimeError("invalid captured Git object ID")
        if oid not in known:
            known[oid] = run(
                ["git", "cat-file", "-t", oid], cwd=wt, check=True
            ).stdout.strip()
        if known[oid] != "commit":
            raise RuntimeError(f"noncommit captured Git root: {oid}")
        cache, tips = (landed, (base,)) if default_only else (reachable, (base, head))
        if oid not in cache:
            cache[oid] = any(
                run(["git", "merge-base", "--is-ancestor", oid, tip], cwd=wt).returncode
                == 0
                for tip in tips
            )
        if not cache[oid]:
            raise RuntimeError(f"unpreserved captured Git root: {oid}")

    with tarfile.open(dest / "git-state.tgz", "r:gz") as archive:
        seen_refs = set()
        for member in archive:
            rel = member.name.removeprefix(".git/").rstrip("/")
            if rel.startswith(("refs/", "logs/")):
                ref_name = rel.removeprefix("logs/")
                containers = {"refs", "refs/worktree", "refs/bisect", "refs/rewritten"}
                if (
                    ref_name != "HEAD"
                    and ref_name not in containers
                    and not ref_name.startswith(LOCAL_REF_PREFIXES)
                ):
                    raise RuntimeError(f"unhandled captured local ref namespace: {rel}")
            if not member.isfile():
                continue
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError(f"captured Git state unreadable: {rel}")
            with source:
                data = source.read()
            if rel.startswith("refs/"):
                oid = refs.get(rel)
                if oid is None or data != f"{oid}\n".encode():
                    raise RuntimeError(f"captured ref bytes/resolved SHA differ: {rel}")
                check_oid(oid, default_only=True)
                seen_refs.add(rel)
            elif rel == "ORIG_HEAD":
                check_oid(data.decode().strip(), default_only=True)
            elif rel.startswith("logs/"):
                for line in data.splitlines():
                    fields = line.split(b" ", 2)
                    if len(fields) != 3:
                        raise RuntimeError(f"malformed captured reflog: {rel}")
                    for raw_oid in fields[:2]:
                        oid = raw_oid.decode("ascii")
                        if len(oid) == len(head) and set(oid) == {"0"}:
                            continue
                        check_oid(oid, default_only=False)
            elif rel == "MERGE_RR" and data:
                raise RuntimeError("nonempty captured rerere state")
            elif rel == "COMMIT_EDITMSG":
                commit = subprocess.run(
                    ["git", "cat-file", "commit", head],
                    cwd=wt,
                    capture_output=True,
                    check=True,
                ).stdout
                if data != commit.split(b"\n\n", 1)[1]:
                    raise RuntimeError("unpreserved captured commit-message draft")
        if seen_refs != set(refs):
            raise RuntimeError("captured local refs lack complete raw coverage")


def _archive_manifest_paths(wt: Path, dest: Path, paths: set[str]) -> None:
    """No exclusions: cover every selected manifest entry without following links."""
    admin = _linked_admin(wt)
    with tarfile.open(dest, "w:gz", dereference=False) as archive:
        for rel in sorted(paths):
            source = (
                admin / rel.removeprefix(".git/")
                if rel.startswith(".git/")
                else wt / rel
            )
            archive.add(source, arcname=rel, recursive=False)


def _archive_index_tree(wt: Path, dest: Path, head: str, expected_sha256: str) -> str:
    """write-tree the saved index, never the live one; prove no entry was omitted."""
    with tempfile.TemporaryDirectory(prefix="wt-index-pin-") as temporary:
        index = Path(temporary) / "index"
        raw = (dest / "git-index").read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise RuntimeError("captured index payload differs from manifest")
        blocked = _index_state_hold(wt, _linked_admin(wt), len(head) // 2, raw=raw)
        if blocked:
            raise RuntimeError(f"captured index: {blocked}")
        index.write_bytes(raw)
        env = {**os.environ, "GIT_INDEX_FILE": str(index)}

        def git(*args: str) -> str:
            return subprocess.run(
                ["git", *args],
                cwd=wt,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            ).stdout

        entries = {}
        for entry in git("ls-files", "--stage", "-z").split("\0"):
            if entry:
                metadata, rel = entry.split("\t", 1)
                mode, oid, stage = metadata.split()
                if stage != "0":
                    raise RuntimeError(
                        "unmerged index cannot be archived by write-tree"
                    )
                entries[rel] = (mode, oid)
        tree = git("write-tree").strip()
        if _tree_entries(wt, tree) != entries:
            raise RuntimeError(
                "write-tree omits index entries (intent-to-add or unsupported index)"
            )
        env.update(
            {
                "GIT_AUTHOR_NAME": "worktree archive",
                "GIT_AUTHOR_EMAIL": "archive@localhost",
                "GIT_COMMITTER_NAME": "worktree archive",
                "GIT_COMMITTER_EMAIL": "archive@localhost",
            }
        )
        commit = git(
            "commit-tree", tree, "-p", head, "-m", "Preserved worktree index"
        ).strip()
        if _tree_entries(wt, commit) != entries:
            raise RuntimeError("index commit differs from captured index entries")
        (dest / "index-tree.txt").write_text(tree + "\n")
        (dest / "index-commit.txt").write_text(commit + "\n")
        return commit


def archive_worktree(
    row: WorktreeRow, now: float | None = None, root: Path | None = None
) -> ArchiveResult:
    """Write a restorable archive of ``row`` and self-check it. Never removes.

    Preserve all working bytes and rooted index objects; uncovered state HOLDs.
    """
    now = time.time() if now is None else now
    root = ARCHIVE_ROOT if root is None else root
    wt = row.path
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    name = _archive_name(row)
    dest = _fresh_dir(root / row.repo / day / name)
    blocked = _worktree_state_hold(wt)
    if blocked:
        return ArchiveResult(dir=dest, ok=False, reason=blocked)
    manifest = _content_manifest(wt)
    (dest / "content-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    for state_name in ("HEAD", "index"):
        with os.fdopen(
            os.open(_linked_admin(wt) / state_name, os.O_RDONLY | os.O_NOFOLLOW), "rb"
        ) as source:
            data = source.read()
        if hashlib.sha256(data).hexdigest() != manifest[f".git/{state_name}"]["sha256"]:
            raise RuntimeError(f"Git {state_name} changed during archive")
        (dest / f"git-{state_name}").write_bytes(data)
    head = str(manifest[".git/resolved-HEAD"]["head_sha"])
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
        # Match the manifest owner used for ignored/Git-state payloads. macOS tar
        # invents AppleDouble members outside the file-byte manifest contract.
        _archive_manifest_paths(wt, tgz, set(files))
    ignored_tgz = dest / "ignored-cache.tgz"
    ignored_count, ignored_bytes = _archive_ignored_cache(wt, ignored_tgz)
    (dest / "RESTORE.md").write_text(
        f"# Restore {wt}\n\nArchived {day} from repo `{row.repo_root}`.\n\n```sh\n"
        f"git -C {row.repo_root} worktree add --detach {wt} {head}\n"
        f"git -C {wt} apply {patch}\n"
        + (f"tar -xzf {tgz} -C {wt}\n" if files else "")
        + f"tar -xzf {ignored_tgz} -C {wt}\n"
        + "```\n\n"
        + "`content-manifest.json` inventories all content, including ignored caches; "
        + "`ignored.tgz` also preserves every excluded ignored file/directory/link. Logical `.git/HEAD` "
        + "and `.git/index` describe external worktree state saved as `git-HEAD` and "
        + "`git-index`. The normal restore above recreates the working files.\n"
        + f"Restore remaining files/modes with `tar -xzf {dest / 'ignored.tgz'} -C {wt}`. "
        + "The index commit is pinned separately (see `index-ref.txt`), so its blobs "
        + "survive pruning. Copy `git-index` into the restored worktree's Git index "
        + "to restore staging without overwriting working files. `git-state.tgz` "
        + "preserves raw HEAD/index/local refs/reflog bytes; restore into that new "
        + "worktree's admin directory, never the common .git directory.\n"
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
    if _content_manifest(wt) != manifest:
        res.reason = "content manifest changed during archive"
        return res
    try:
        index_commit = _archive_index_tree(
            wt, dest, head, str(manifest[".git/index"]["sha256"])
        )
        restored = _verify_tracked_payload(wt, dest, head, manifest)
        required = _required_untracked_payloads(wt, manifest, restored)
        if required and not tgz.is_file():
            raise RuntimeError(
                f"untracked archive coverage missing: {sorted(required)!r}"
            )
        if required or tgz.exists():
            _verify_archive_payloads(tgz, manifest, required)
        cache_members = {
            rel
            for rel, entry in manifest.items()
            if rel.startswith(".claude/cache/")
            and not any(rel.startswith(f"{strip}/") for strip in _CACHE_STRIP_DIRS)
            and entry["type"] == "file"
            and entry["size"] <= MAX_ARCHIVED_CACHE_BYTES
        }
        _verify_archive_payloads(ignored_tgz, manifest, cache_members)
        # Legacy small-cache/untracked artifacts remain readable. This supplemental
        # payload closes ALL exclusions, and retains empty directories and modes.
        remaining = {
            rel
            for rel, entry in manifest.items()
            if rel != ".git"
            and not rel.startswith(".git/")
            and rel not in restored
            and rel not in required
        }
        _archive_manifest_paths(wt, dest / "ignored.tgz", remaining)
        _verify_archive_payloads(dest / "ignored.tgz", manifest, remaining)
        git_state = {
            rel
            for rel, entry in manifest.items()
            if rel.startswith(".git/")
            and entry["type"] in {"file", "directory", "symlink"}
        }
        _archive_manifest_paths(wt, dest / "git-state.tgz", git_state)
        _verify_archive_payloads(dest / "git-state.tgz", manifest, git_state)
        _verify_git_state_roots(wt, dest, manifest, head)
    except (
        tarfile.TarError,
        RuntimeError,
        OSError,
        ValueError,
        subprocess.CalledProcessError,
    ) as error:
        res.reason = f"archive manifest verification failed: {error}"
        return res
    blocked = _worktree_state_hold(wt)
    if blocked:
        res.reason = blocked
        return res
    res.ref = _pin_ref(
        row.repo_root, name, time.strftime("%Y%m%d", time.localtime(now)), head
    )
    res.index_ref = _pin_ref(
        row.repo_root,
        name + "-index",
        time.strftime("%Y%m%d", time.localtime(now)),
        index_commit,
    )
    (dest / "index-ref.txt").write_text(res.index_ref + "\n")
    if _content_manifest(wt) != manifest:
        res.reason = "content manifest changed while pinning archive"
        return res
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
    try:
        if _codex_owner_thread(wt):
            print(f"SKIP {wt}: codex-app-owned")
            return {}
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"HOLD {wt}: app ownership unknown: {error}", file=sys.stderr)
        return {}
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
    """Suggest idle dirty trees for explicit archive; age is never removal authority."""
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
            or (row.blocking_paths and not row.hold_reason)
        ) and idle_age_days(row.path, now) >= archive_days:
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
        if row.held or row.daemon_held or row.codex_owner_thread:
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
        if row.held or row.daemon_held or row.lock_live or row.codex_owner_thread:
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


def plan_landed_archive(
    rows: list[WorktreeRow],
    idle_hours: float | None,
    keep: set[str],
    exclude: list[WorktreeRow],
) -> list[WorktreeRow]:
    if idle_hours is None:
        return []
    return [
        row
        for row in rows
        if row.classify() == "landed"
        and not row.codex_owner_thread
        and row not in exclude
        and not any(k in str(row.path) for k in keep)
        and row.path.exists()
        and idle_age_days(row.path) * 24 >= idle_hours
    ]


def remove_landed_from_quarantine(
    row: WorktreeRow, idle_hours: float, archive_dir: Path
) -> bool:
    """Rename first; only evidence collected at that name may authorize deletion.

    Repair Git's registration to match the rename, restoring both on any failure.
    This excludes opens through the original name, but Git exposes the quarantine
    and existing descriptors remain writable. After settling, compare every path,
    size and SHA-256 against the archive immediately before removal. This detects
    intervening changes, not exclusion: writes after their final hash or during
    deletion remain a residual race. No finite settle interval eliminates it.
    """
    original = row.path
    quarantine: Path | None = None
    moved = False
    try:
        if _codex_owner_thread(original):
            raise RuntimeError("codex-app-owned")
        manifest = json.loads((archive_dir / "content-manifest.json").read_text())
        if not isinstance(manifest, dict) or "." not in manifest:
            raise ValueError("invalid archive content manifest")
        if original.is_symlink() or not original.is_dir():
            raise RuntimeError("worktree is no longer a real directory")
        quarantine = Path(
            tempfile.mkdtemp(
                prefix=f"gc-quarantine-{original.name}-", dir=original.parent
            )
        )
        original.rename(quarantine)
        moved = True
        run(
            ["git", "worktree", "repair", str(quarantine)],
            cwd=row.repo_root,
            check=True,
        )
        candidate = replace(row, path=quarantine)
        default_ref = default_branch(row.repo_root)
        default_sha = run(
            ["git", "rev-parse", "--verify", f"{default_ref}^{{commit}}"],
            cwd=row.repo_root,
            check=True,
        ).stdout.strip()
        expected_head = manifest.get(".git/resolved-HEAD")
        if not isinstance(expected_head, dict) or not dirty_work_on_default(
            row.repo_root, quarantine, expected_head=expected_head
        ):
            raise RuntimeError("quarantined work no longer fully landed")

        def check_removal_ready() -> None:
            if idle_age_days(quarantine) * 24 < idle_hours:
                raise RuntimeError("quarantined work clock now fresh")
            blocked = removal_hold(candidate)
            if blocked:
                raise RuntimeError(blocked)
            # A holder may have been reported before or after the rename.
            for holders in (live_cwd_holders(), live_mapped_holders()):
                if not liveness_known(holders):
                    raise RuntimeError("quarantine holder evidence unknown")
                if holders_for(original, holders) or holders_for(quarantine, holders):
                    raise RuntimeError("live holder at original or quarantine path")
            if original.exists() or original.is_symlink():
                raise RuntimeError("original path was recreated during quarantine")

        check_removal_ready()
        time.sleep(QUARANTINE_SETTLE_SECONDS)
        settled_ref = default_branch(row.repo_root)
        settled_sha = run(
            ["git", "rev-parse", "--verify", f"{settled_ref}^{{commit}}"],
            cwd=row.repo_root,
            check=True,
        ).stdout.strip()
        still_landed = dirty_work_on_default(
            row.repo_root, quarantine, expected_head=expected_head
        )
        if (settled_ref, settled_sha) != (default_ref, default_sha):
            raise RuntimeError("default branch moved during quarantine settling")
        if not still_landed:
            raise RuntimeError("settled quarantined work no longer fully landed")
        verified_sha = run(
            ["git", "rev-parse", "--verify", f"{settled_ref}^{{commit}}"],
            cwd=row.repo_root,
            check=True,
        ).stdout.strip()
        if verified_sha != settled_sha or default_branch(row.repo_root) != settled_ref:
            raise RuntimeError("default branch moved during settled landing proof")
        check_removal_ready()
        remove_worktree(row.repo_root, quarantine, manifest=manifest)
        return True
    except (subprocess.CalledProcessError, RuntimeError, OSError, ValueError) as error:
        recovery = ""
        if moved and quarantine is not None and quarantine.exists():
            try:
                if original.exists() or original.is_symlink():
                    raise RuntimeError(
                        f"original path occupied; preserved at {quarantine}"
                    )
                quarantine.rename(original)
                run(
                    ["git", "worktree", "repair", str(original)],
                    cwd=row.repo_root,
                    check=True,
                )
            except (subprocess.CalledProcessError, RuntimeError, OSError) as rollback:
                recovery = f"; rollback failed: {rollback}"
        elif not moved and quarantine is not None:
            try:
                quarantine.rmdir()
            except OSError as rollback:
                recovery = f"; empty quarantine cleanup failed: {rollback}"
        print(
            f"[DEGRADED] HOLD {original}: quarantine removal failed: {error}{recovery}",
            file=sys.stderr,
        )
        return False


def default_branch(repo: Path) -> str:
    """Use the remote's declared default, then the local main/master convention."""
    # One native enumeration replaces multiple fork/exec queries in every safety
    # scan. No evidence is cached across scans (refs may move at any boundary).
    result = run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname) %(symref)",
            "refs/heads",
            "refs/remotes/origin/HEAD",
        ],
        cwd=repo,
        check=True,
    )
    refs = dict(line.split(" ", 1) for line in result.stdout.splitlines())
    ref = refs.get("refs/remotes/origin/HEAD")
    if ref:
        local = "refs/heads/" + ref.removeprefix("refs/remotes/origin/")
        if local in refs:
            return local  # Landed local work may be ahead of the last remote fetch.
        return ref
    for branch in ("main", "master"):
        if f"refs/heads/{branch}" in refs:
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
        if row.hold_reason:
            reasons.append(row.hold_reason)
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
            "blocking_paths": list(row.blocking_paths),
            "codex_owner_thread": row.codex_owner_thread,
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
            if record["codex_owner_thread"] is not None:
                print(f"  codex-app-owned: owner thread {record['codex_owner_thread']}")
            if record["not_candidate_reasons"]:
                print(f"  held: {'; '.join(record['not_candidate_reasons'])}")
            if record["blocking_paths"]:
                print(f"  unproven paths: {json.dumps(record['blocking_paths'])}")
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
            (
                r
                for r in audit_repo(
                    root, with_size=False, only_path=path, check_landing=False
                )
                if r.path.resolve() == path
            ),
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
        blocked = removal_hold(row, operator_archive=True)
        if blocked:
            print(
                f"HOLD {path}: {blocked}; archive complete, tree kept. Unlocking a pid-less lock requires a separate explicit decision."
            )
            return 2
        manifest = json.loads((res.dir / "content-manifest.json").read_text())
        remove_worktree(root, path, manifest=manifest, operator_archive=True)
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
        "--archive-landed-idle-hours",
        type=float,
        default=None,
        metavar="N",
        help="archive and remove only dirty trees whose entire work is already on the default branch, idle >= N hours",
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
        help="delete real, git-ignored .venv, .uv-cache, .claude/cache/index-trees and "
        ".claude/cache/source-epochs dirs (never symlinks, never tracked files) of any "
        "tree with no process inside and nothing touched for N minutes, live-locked "
        "trees included; audit marks would-strip",
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
    if args.archive_landed_idle_hours is not None and (
        not math.isfinite(args.archive_landed_idle_hours)
        or args.archive_landed_idle_hours <= 0
    ):
        ap.error("--archive-landed-idle-hours must be a positive finite number")
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
    keep = set(args.keep)
    stream_audit = args.mode == "audit" and not args.check

    def scan_liveness() -> dict[str, list[int]]:
        holders = live_cwd_holders()
        if not liveness_known(holders):
            # Say WHY the scan is empty: the nightly apply has exited 2 here every
            # night since 2026-08-27 with a bare message, so the receipt could not
            # tell a timeout from a missing binary from a genuinely empty parse.
            print(
                "[DEGRADED] liveness unknown — lsof reported no cwd holders at all; "
                f"every removal is refused until the scan works ({LAST_SCAN_DIAG})",
                file=sys.stderr,
            )
        return holders

    # Read-only audit rows need liveness before they can be printed. Mutating
    # routes and hook checks still scan last, after all Git proofs finish.
    cwd_holders = scan_liveness() if stream_audit else {}
    daemons = (
        daemon_pids({pid for pids in cwd_holders.values() for pid in pids})
        if stream_audit
        else set()
    )

    def set_liveness(row: WorktreeRow) -> None:
        pids = holders_for(row.path, cwd_holders)
        row.daemon_pids = tuple(sorted(pid for pid in pids if pid in daemons))
        row.daemon_held = len(row.daemon_pids)
        row.held = len(pids) - row.daemon_held

    def emit_audit_row(row: WorktreeRow) -> None:
        set_liveness(row)
        print_audit_row(
            row,
            remove=should_remove(
                row, args.include_unmerged, args.force_stale, args.force_all, keep
            ),
            aged_lock=bool(
                liveness_known(cwd_holders)
                and plan_aged_locks([row], args.lock_max_age_hours, keep)
            ),
        )

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
                    on_row=emit_audit_row if stream_audit else None,
                )
            )

    if not stream_audit:
        cwd_holders = scan_liveness()
        daemons = daemon_pids(
            {pid for row in all_rows for pid in holders_for(row.path, cwd_holders)}
        )
        for row in all_rows:
            set_liveness(row)

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
    landed_rows = (
        []
        if pruning
        else plan_landed_archive(
            all_rows,
            args.archive_landed_idle_hours,
            keep,
            exclude=to_remove + idle_rows,
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
                exclude=to_remove + idle_rows + archive_rows + landed_rows,
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

    if not pruning and not stream_audit:
        for row in all_rows:
            print_audit_row(row, remove=row in to_remove, aged_lock=row in aged_rows)

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
        for row in landed_rows:
            print(f"would-archive-landed {row.path} (idle {row.idle_days * 24:.1f}h)")
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
            proven_head = _head_identity(row.path)
            if not (args.include_unmerged or args.force_stale or args.force_all):
                head = str(proven_head["head_sha"])
                if not is_ancestor(row.repo_root, head):
                    print(
                        f"SKIP {row.path}: HEAD now has unlanded commits; use suggest"
                    )
                    continue
            remove_worktree(
                row.repo_root,
                row.path,
                force=args.force_stale or args.force_all,
                expected_head=proven_head,
            )
            print(f"removed {row.path}")
            removed += 1
            if args.prune_branches and row.branch and (row.stale or row.dup):
                _prune_branch(row.repo_root, row.branch, str(proven_head["head_sha"]))
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
            proven_head = _head_identity(row.path)
            head = str(proven_head["head_sha"])
            if not all_patches_on_main(row.repo_root, head):
                print(f"SKIP {row.path}: HEAD now has unlanded commits; use suggest")
                continue
            remove_worktree(
                row.repo_root, row.path, force=False, expected_head=proven_head
            )
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
    for row in landed_rows:
        if row.path in seen:
            continue
        seen.add(row.path)
        try:
            # Repeat before the archive and again at removal: planning is not authority.
            if not dirty_work_on_default(row.repo_root, row.path):
                print(f"HOLD {row.path}: work no longer fully landed")
                continue
            if idle_age_days(row.path) * 24 < args.archive_landed_idle_hours:
                print(f"HOLD {row.path}: work clock now fresh")
                continue
            blocked = removal_hold(row)
            if blocked:
                print(f"HOLD {row.path}: {blocked}")
                continue
            res = archive_worktree(row)
            if not res.ok:
                print(
                    f"HOLD {row.path}: archive self-check failed: {res.reason}",
                    file=sys.stderr,
                )
                continue
            if not remove_landed_from_quarantine(
                row, args.archive_landed_idle_hours, res.dir
            ):
                continue
            archived += 1
            print(f"ARCHIVED-LANDED {row.path} -> {res.dir} (pin {res.ref})")
        except (subprocess.CalledProcessError, RuntimeError, OSError) as error:
            print(f"HOLD {row.path}: landed archive failed: {error}", file=sys.stderr)

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
    # Missing-path registrations can still own unique index/ref/reflog objects.
    # Successful remove unregisters its target; blanket prune has no safe proof.

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
        parts.append(f"archived 0/{len(archive_rows)} (under {ARCHIVE_ROOT})")
    if args.archive_landed_idle_hours is not None and not pruning:
        parts.append(
            f"archived landed {archived}/{len(landed_rows)} (under {ARCHIVE_ROOT})"
        )
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
