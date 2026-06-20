#!/usr/bin/env python3
"""register_implementations.py — the RSI closing-force registration trigger.

The documented missing half of the prediction ledger (research/2026-06-14-leverage-hunt-
rsi-system.md WIN 2: "the prediction ledger is half of AHE already shipped — it just lacks
the registration trigger"). improvement-log status flips are MANUAL markdown edits, so there
is no inline write site to hook (probe-the-write, 2026-06-18) — the trigger is instead a
git-diff scan over recent commits, run daily by drift-sentinel.

What it does: for every finding that newly reaches `[x]` (implemented) in improvement-log.md,
auto-register a skeleton prediction with a +30d check_date. 30 days later it surfaces in the
Questions-for-you VIEW (questions_view.py) as a DUE earn-its-keep verdict — closing the loop so
no implemented scaffold escapes the "does this still need to exist?" question (gov telos: the
governance corpus SHRINKS as model IQ rises). This is the AUTONOMOUS, append-only, reversible
piece; auto-RETIREMENT (gov.py route() local+verifier-pass+0-reverts) stays human-gated until
this trigger has built a track record.

Idempotent + stateless: the prediction id is a deterministic hash of (commit, finding line),
so re-runs and overlapping windows dedup for free — no last-processed marker file needed.

Scheduled: pulse tick sense phase (daily, $0). Manual: uv run python3 scripts/register_implementations.py
"""
from __future__ import annotations

import datetime
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import predictions

REPO = Path(__file__).resolve().parent.parent
LOG = "improvement-log.md"
CHECK_HORIZON_DAYS = 30  # matches Constitution Pre-Registered Test #3 (findings→implemented 30d)

# A finding line that newly reached [x] in a diff: leading '+' (added), then the
# '- [x]' marker. [~]/[>]/[-] are already-terminal (retired/superseded/rejected) — only
# [x] (implemented) schedules an earn-its-keep re-check. Bold title is captured for the change text.
_ADDED_IMPL = re.compile(r"^\+\s*-?\s*\[x\]\s*(.+?)\s*$")


def _run(*args: str) -> str:
    p = subprocess.run(["git", "-C", str(REPO), *args],
                       capture_output=True, text=True, timeout=60)
    return p.stdout if p.returncode == 0 else ""


def _commits_since(window: str) -> list[str]:
    out = _run("log", f"--since={window}", "--format=%H", "--", LOG)
    return [c for c in out.splitlines() if c.strip()]


def _added_impl_lines(sha: str) -> list[str]:
    """Finding texts that this commit ADDED as [x] (implemented) in improvement-log.md."""
    diff = _run("show", "--no-ext-diff", "--format=", sha, "--", LOG)
    found: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++"):
            continue
        m = _ADDED_IMPL.match(line)
        if m:
            text = re.sub(r"\s+", " ", m.group(1)).strip()
            if text:
                found.append(text)
    return found


def _pid(sha: str, text: str) -> str:
    h = hashlib.sha1(f"{sha}::{text}".encode()).hexdigest()[:8]
    return f"impl-{sha[:8]}-{h}"


def scan(window: str = "4.days.ago") -> dict:
    """Register an earn-its-keep prediction for each newly-implemented finding in the window.

    Default 4-day lookback overlaps the daily cadence (nothing missed); idempotent dedup makes
    the overlap free. Returns {registered, skipped} counts."""
    check_date = (datetime.date.today()
                  + datetime.timedelta(days=CHECK_HORIZON_DAYS)).isoformat()
    registered, skipped = 0, 0
    for sha in _commits_since(window):
        for text in _added_impl_lines(sha):
            pid = _pid(sha, text)
            new = predictions.register_prediction(
                change=text[:200],
                prediction=("still earns its place at check_date — verifier passes AND "
                            "would still pass with the scaffold removed (else retire-eligible)"),
                metric="gov-shrink verdict if Gov-ID/verifier present, else manual earn-its-keep verdict",
                check_date=check_date,
                commit=sha[:8],
                pid=pid,
                source="register_implementations",
            )
            if new:
                registered += 1
                print(f"  + {pid}  {text[:80]}")
            else:
                skipped += 1
    return {"registered": registered, "skipped": skipped}


def main() -> int:
    window = "4.days.ago"
    args = sys.argv[1:]
    if "--since" in args:
        window = args[args.index("--since") + 1]
    elif "--all" in args:
        window = "20.years.ago"  # backfill (one-off); idempotent so safe to re-run
    r = scan(window)
    if r["registered"]:
        print(f"[register-impl] registered {r['registered']} earn-its-keep check(s) "
              f"(+{CHECK_HORIZON_DAYS}d), {r['skipped']} already present")
    else:
        print(f"[register-impl] no new implementations in window ({r['skipped']} already present)")
    # Closing force: the same daily pass that REGISTERS predictions also auto-resolves
    # the proxy-free subset (refute reverted commits). Without this the ledger is
    # write-only — registration fires daily, resolution never does. See predictions.py
    # cmd_auto_resolve. The semantic remainder stays operator-gated via questions_view.
    predictions.cmd_auto_resolve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
