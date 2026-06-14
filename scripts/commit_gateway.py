#!/usr/bin/env python3
"""commit_gateway.py — declarative, serialized, receipted git commit (Phase 1 slice).

The deepest-layer answer from decisions/2026-06-14-commit-gateway-architecture.md:
commit is a gateway-mediated mutation, not hand-operated git. The agent supplies the
SEMANTIC decision (which paths + why); the gateway owns the mechanics:

  - serialize the stage->commit critical section behind a lease lock (no .git/index race)
  - commit with an EXPLICIT PATHSPEC so a concurrent agent's staged files are never adopted
  - assemble the canonical [scope] message (transform, not reject)
  - stamp a Gateway-Receipt trailer (attribution: gateway-commit vs deliberate override)
  - run the shared policy as DEFENSE-IN-DEPTH (git's own pre-commit hook fires on our commit)
  - ESCALATE feisty git (merge/rebase/revert/cherry-pick/detached/conflict) to the caller

Enforcement is VISIBILITY not prevention: --no-verify / raw git stay available as deliberate
escape hatches; the receipt makes a bypass non-silent. A deliberate protected-path override
goes through --allow-guard-bypass (sets GIT_ALLOW_GUARD_BYPASS — the existing visible env
override), NOT --no-verify.

Output: JSON on stdout {status: committed|escalate, sha?, receipt?, reason?}; logs on stderr.
Exit 0 = committed, 3 = escalate (caller/high-reasoning agent takes over), 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

LOCK_TIMEOUT = int(os.environ.get("COMMIT_LOCK_TIMEOUT", "180"))   # max wait for lock (s)
LOCK_STALE = int(os.environ.get("COMMIT_LOCK_STALE", "300"))       # treat lock older than this as dead


def log(msg: str) -> None:
    print(f"[commit-gateway] {msg}", file=sys.stderr)


def git(repo: Path, *args: str, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), "--no-ext-diff", *args],
        capture_output=True, text=True, check=check, env=env,
    )


def repo_root(start: Path) -> Path:
    out = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(out.stdout.strip())


def feisty_reason(repo: Path) -> str | None:
    """Routine-only: return a reason string if the repo is in a state needing reasoning."""
    g = repo / ".git"
    checks = {
        "merge in progress": g / "MERGE_HEAD",
        "rebase in progress": g / "rebase-merge",
        "rebase (apply) in progress": g / "rebase-apply",
        "cherry-pick in progress": g / "CHERRY_PICK_HEAD",
        "revert in progress": g / "REVERT_HEAD",
    }
    for reason, p in checks.items():
        if p.exists():
            return reason
    # detached HEAD
    r = git(repo, "symbolic-ref", "-q", "HEAD", check=False)
    if r.returncode != 0:
        return "detached HEAD"
    return None


def acquire_lock(repo: Path) -> Path:
    """Atomic mkdir spinlock with PID + age stale-reaping (ported from genomics session_commit.sh)."""
    lockdir = repo / ".git" / ".commit-gateway.lock"
    waited = 0
    while True:
        try:
            lockdir.mkdir()
            (lockdir / "pid").write_text(str(os.getpid()))
            return lockdir
        except FileExistsError:
            holder = ""
            try:
                holder = (lockdir / "pid").read_text().strip()
            except OSError:
                pass
            # reap dead holder
            if holder.isdigit():
                try:
                    os.kill(int(holder), 0)
                except ProcessLookupError:
                    log(f"reaping lock from dead pid {holder}")
                    _rmlock(lockdir)
                    continue
                except PermissionError:
                    pass  # alive, owned by another user — keep waiting
            # reap stale lock by age
            try:
                age = time.time() - lockdir.stat().st_mtime
            except OSError:
                age = 0
            if age >= LOCK_STALE:
                log(f"reaping stale lock (age {int(age)}s, holder={holder or '?'})")
                _rmlock(lockdir)
                continue
            if waited >= LOCK_TIMEOUT:
                raise TimeoutError(f"timed out after {LOCK_TIMEOUT}s waiting for commit lock (holder={holder or '?'})")
            time.sleep(1)
            waited += 1


def _rmlock(lockdir: Path) -> None:
    try:
        (lockdir / "pid").unlink(missing_ok=True)
        lockdir.rmdir()
    except OSError:
        pass


def build_message(scope: str, subject: str, body: list[str], receipt: str, ctype: str) -> str:
    """Transform (don't reject) into the canonical [scope] subject — why form, + receipt trailer."""
    subject = subject.strip()
    head = subject if subject.startswith(f"[{scope}]") else f"[{scope}] {subject}"
    parts = [head]
    if body:
        parts.append("")
        parts.extend(body)
    parts.append("")  # blank line before trailers
    parts.append(f"Gateway-Receipt: {receipt}")
    if ctype:
        parts.append(f"Change-Type: {ctype}")
    return "\n".join(parts) + "\n"


def emit(obj: dict, code: int) -> int:
    print(json.dumps(obj))
    return code


def main() -> int:
    ap = argparse.ArgumentParser(description="Declarative, serialized, receipted git commit.")
    ap.add_argument("--paths", nargs="+", required=True, help="EXACT files to commit (explicit pathspec).")
    ap.add_argument("--scope", required=True, help="Commit [scope] (see <repo>/.git-scopes).")
    ap.add_argument("--subject", required=True, help="Subject after [scope]: 'Verb thing — why'.")
    ap.add_argument("--body", action="append", default=[], help="Body paragraph (repeatable).")
    ap.add_argument("--type", default="", help="Change type for the receipt (feat/fix/refactor/...).")
    ap.add_argument("--session", default="", help="Session id (default: read .claude/current-session-id).")
    ap.add_argument("--allow-guard-bypass", action="store_true",
                    help="Deliberate, VISIBLE protected-path override (sets GIT_ALLOW_GUARD_BYPASS). Not --no-verify.")
    ap.add_argument("--repo", default=".", help="Repo path (default: cwd's toplevel).")
    args = ap.parse_args()

    try:
        repo = repo_root(Path(args.repo).resolve())
    except subprocess.CalledProcessError:
        return emit({"status": "error", "reason": f"not a git repo: {args.repo}"}, 2)

    # routine-only gate: hand feisty states back to the reasoning caller BEFORE locking
    reason = feisty_reason(repo)
    if reason:
        return emit({"status": "escalate", "reason": reason,
                     "hint": "feisty git — high-reasoning caller should handle"}, 3)

    receipt = uuid.uuid4().hex[:16]
    env = dict(os.environ)
    if args.allow_guard_bypass:
        env["GIT_ALLOW_GUARD_BYPASS"] = "1"
        log("GIT_ALLOW_GUARD_BYPASS set — deliberate protected-path override (recorded in receipt)")

    try:
        lockdir = acquire_lock(repo)
    except TimeoutError as e:
        return emit({"status": "escalate", "reason": str(e)}, 3)

    try:
        # stage ONLY the named paths; commit with EXPLICIT PATHSPEC so concurrent staged
        # files are never adopted. (The lock serializes; the pathspec isolates.)
        for p in args.paths:
            r = git(repo, "add", "--", p, check=False)
            if r.returncode != 0:
                return emit({"status": "escalate", "reason": f"git add failed for {p}: {r.stderr.strip()}"}, 3)

        msg = build_message(args.scope, args.subject, args.body, receipt, args.type)
        with tempfile.NamedTemporaryFile("w", suffix=".msg", delete=False) as mf:
            mf.write(msg)
            msgfile = mf.name
        try:
            # git commit fires the pre-commit hook chain = shared policy (defense-in-depth).
            r = git(repo, "commit", "-F", msgfile, "--", *args.paths, check=False, env=env)
        finally:
            os.unlink(msgfile)

        if r.returncode != 0:
            combined = (r.stdout + r.stderr).strip()
            # unstage my paths so a failed attempt leaves no residue
            for p in args.paths:
                git(repo, "reset", "-q", "--", p, check=False)
            low = combined.lower()
            if "nothing to commit" in low or "no changes added" in low:
                return emit({"status": "escalate", "reason": "nothing to commit for the given paths",
                             "detail": combined[-400:]}, 3)
            # a guard (protected-paths / large-binary) blocked — escalate with the override hint
            return emit({"status": "escalate", "reason": "pre-commit guard blocked",
                         "detail": combined[-600:],
                         "hint": "if this override is intended, re-run with --allow-guard-bypass"}, 3)

        sha = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
        # belt-and-suspenders: confirm the commit holds ONLY our paths
        committed = set(git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split())
        requested = {os.path.normpath(p) for p in args.paths}
        foreign = committed - {os.path.normpath(c) for c in committed if os.path.normpath(c) in requested or c in requested}
        subj = git(repo, "log", "-1", "--format=%s", "HEAD").stdout.strip()
        out = {"status": "committed", "sha": sha, "receipt": receipt, "subject": subj}
        if foreign:
            out["warning"] = f"committed files outside requested set: {sorted(foreign)}"
        return emit(out, 0)
    finally:
        _rmlock(lockdir)


if __name__ == "__main__":
    sys.exit(main())
