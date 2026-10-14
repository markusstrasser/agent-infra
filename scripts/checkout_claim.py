#!/usr/bin/env python3
"""Per-checkout session claim-lock — precise peer detection.

The single primitive behind isolate-by-default
(decisions/2026-06-16-shared-checkout-isolation-by-default.md). Replaces the
imprecise global `pgrep -x claude` (which counts ALL claude processes on ANY
checkout) with a precise per-checkout signal: *who holds THIS working tree, and is
that process still alive?*

Lock file (gitignored runtime state): <checkout>/.claude/checkout-claim.json
    {"pid": int, "session_id": str, "started_at": iso8601, "host": str,
     "proc_start": str}

Design invariants (see ADR):
  - A lock whose pid is DEAD is STALE → reclaimable. Never a deadlock.
  - A pid counts as the holder only while it has the start time recorded at claim
    (`proc_start`). macOS recycles pids, so a bare existence probe takes whatever
    process got the number next for a live peer (2026-10-14: SafariLaunchAgent).
  - Fail-open: a missing/corrupt lock means "no holder", never an error.
  - Per *physical checkout dir* — worktrees have separate working trees, hence
    separate locks (which is exactly what makes isolation work).
  - Inspectable: `checkout_claim.py status` prints the holder + liveness.

This module is a pure library + CLI. It is NOT wired into any hook yet — the
consumers (launch wrapper; sessionstart-peer-session-warn) are gated on a quiet
checkout per the ADR. Building/validating the primitive first is deliberate
(probe the mechanism at 1/10 the blast radius before integrating).
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

LOCK_REL = Path(".claude") / "checkout-claim.json"


@dataclass
class Claim:
    pid: int
    session_id: str
    started_at: str
    host: str
    proc_start: str = ""


def _lock_path(checkout: Path) -> Path:
    return checkout / LOCK_REL


def _pid_alive(pid: int) -> bool:
    """True iff a process with this pid exists. signal 0 = existence probe."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user
    return True


def _proc_start(pid: int) -> str:
    """The process's start time as `ps` prints it; "" if no such process.

    exec keeps it, so the launcher's value still matches once the launcher has
    become claude; a recycled pid gives a different value.
    """
    if pid <= 0:
        return ""
    try:
        r = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True,
                           text=True, timeout=5, env={**os.environ, "LC_ALL": "C"})
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def _holder_alive(c: Claim) -> bool:
    """True iff the claimed process still runs: the pid exists with the recorded start.

    A lock without `proc_start` predates the check and recorded the claim helper's
    own pid, which exits at once, so it cannot name a live holder.
    """
    if not c.proc_start or not _pid_alive(c.pid):
        return False
    return _proc_start(c.pid) == c.proc_start


def read_claim(checkout: Path) -> Claim | None:
    """The claim as written, no liveness filter. None if absent/corrupt (fail-open)."""
    try:
        d = json.loads(_lock_path(checkout).read_text(encoding="utf-8"))
        return Claim(int(d["pid"]), str(d["session_id"]),
                     str(d["started_at"]), str(d.get("host", "")),
                     str(d.get("proc_start", "")))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def live_holder(checkout: Path) -> Claim | None:
    """The claim IFF its process is alive. A stale (dead or reused pid) claim returns None."""
    c = read_claim(checkout)
    return c if (c is not None and _holder_alive(c)) else None


def peer_held(checkout: Path, my_session_id: str) -> Claim | None:
    """A LIVE holder that is NOT me — the precise 'should I isolate?' signal.

    Returns the peer Claim, or None if the tree is free / stale / mine.
    """
    c = live_holder(checkout)
    if c is None or c.session_id == my_session_id:
        return None
    return c


def claim(checkout: Path, session_id: str, *, pid: int | None = None,
          started_at: str | None = None) -> Claim:
    """Take the lock for this session (overwrites a stale or own claim).

    Caller decides isolation BEFORE claiming (check `peer_held` first); this just
    records ownership. `started_at` is injectable for deterministic tests.
    """
    pid = pid if pid is not None else os.getpid()
    c = Claim(
        pid=pid,
        session_id=session_id,
        started_at=started_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        host=socket.gethostname(),
        proc_start=_proc_start(pid),
    )
    p = _lock_path(checkout)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(c), indent=2), encoding="utf-8")
    return c


def release(checkout: Path, session_id: str) -> bool:
    """Remove the lock IFF this session owns it. True if removed."""
    c = read_claim(checkout)
    if c is not None and c.session_id == session_id:
        try:
            _lock_path(checkout).unlink()
            return True
        except OSError:
            return False
    return False


def _resolve_checkout(arg: str | None) -> Path:
    return Path(arg).resolve() if arg else Path.cwd()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="checkout_claim", description=(__doc__ or "").splitlines()[0])
    p.add_argument("-C", "--checkout", default=None, help="Checkout dir (default: cwd)")  # git-style, before subcommand
    # --json lives in a parent so it is accepted AFTER the subcommand (`status --json`),
    # where argparse would otherwise reject a top-level optional.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="Machine-readable output")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", parents=[common], help="Show the current holder + liveness")
    sc = sub.add_parser("claim", parents=[common], help="Take the lock for a session")
    sc.add_argument("--session", required=True)
    # Required: this CLI's own pid exits as soon as the claim is written.
    sc.add_argument("--pid", type=int, required=True,
                    help="Pid of the session process (the launcher's $$, which exec makes claude)")
    sr = sub.add_parser("release", parents=[common], help="Release the lock if owned")
    sr.add_argument("--session", required=True)
    sp = sub.add_parser("peer", parents=[common], help="Exit 0 if a LIVE peer holds it (else 1)")
    sp.add_argument("--session", required=True)
    args = p.parse_args(argv)
    checkout = _resolve_checkout(args.checkout)

    if args.cmd == "status":
        c = read_claim(checkout)
        alive = bool(c and _holder_alive(c))
        if args.json:
            print(json.dumps({"holder": asdict(c) if c else None, "alive": alive,
                              "checkout": str(checkout)}))
        elif c is None:
            print(f"  ✓ {checkout}: unclaimed")
        else:
            mark = "●" if alive else "○ (stale — reclaimable)"
            print(f"  {mark} held by pid={c.pid} session={c.session_id[:8]} "
                  f"since {c.started_at} on {c.host}")
        return 0

    if args.cmd == "claim":
        if not _proc_start(args.pid):
            print(f"checkout_claim: pid {args.pid} is not running; nothing claimed",
                  file=sys.stderr)
            return 3
        c = claim(checkout, args.session, pid=args.pid)
        print(json.dumps(asdict(c)) if args.json else f"  ✓ claimed by {c.session_id[:8]} (pid {c.pid})")
        return 0

    if args.cmd == "release":
        ok = release(checkout, args.session)
        print(("released" if ok else "not owned — nothing released") if not args.json
              else json.dumps({"released": ok}))
        return 0

    if args.cmd == "peer":
        peer = peer_held(checkout, args.session)
        if args.json:
            print(json.dumps({"peer": asdict(peer) if peer else None}))
        elif peer:
            print(f"  ! live peer: pid={peer.pid} session={peer.session_id[:8]}")
        else:
            print("  ✓ no live peer")
        return 0 if peer else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
