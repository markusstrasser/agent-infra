#!/usr/bin/env python3
"""Test-health sentinel — watch whether each repo's test suite still COMPLETES.

A non-completing suite produces NO regression signal, and a single flaky hard
crash can silently disable the entire suite for days. It did: a certificates
SIGSEGV (~2/20) aborted `pytest tests/` and masked FOUR clusters of cross-repo
contract drift for ~6 days (2026-06-01). `doctor.py` checks hooks/config; nothing
watched whether the suites themselves run. This is that watcher — the
error-correction loop's self-monitor.

Local, zero-API, report-only. For each configured repo it runs the suite (slow
tests excluded) under a timeout and records, appended to
``~/.claude/test-health.jsonl`` for trend:

  outcome ∈ {passed, failed,                      # COMPLETED — normal signal
             collection_error, internal_error,    # DID NOT COMPLETE — high signal
             usage_error, no_tests, crashed, timeout}

The load-bearing distinction is COMPLETED vs DID-NOT-COMPLETE: "5 failed" is a
normal regression you'll see anyway; "crashed / collection_error / timeout" means
the suite can't even produce a verdict — the blind spot this exists to catch.

Run: ``just test-health`` (or the daily launchd job com.agent-infra.test-health).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYTHONUNBUFFERED", "1")

HOME = Path.home()
STATUS_LOG = Path(os.environ.get("TEST_HEALTH_LOG", HOME / ".claude" / "test-health.jsonl"))

# Per-repo suite invocation. Only repos with a VERIFIED pytest layout are listed
# — a wrong command would misfire as a false "crashed", which is exactly the
# iatrogenic noise this tool must not produce. `args` are passed to pytest; slow
# tests are excluded so the daily run stays cheap. (intel has no tests/ dir →
# deliberately omitted until its layout is verified.)
@dataclass(frozen=True)
class RepoSuite:
    repo: str
    path: Path
    args: tuple[str, ...]
    timeout_s: int = 900


SUITES: tuple[RepoSuite, ...] = (
    RepoSuite("phenome", HOME / "Projects" / "phenome", ("tests/", "-m", "not slow")),
    RepoSuite("agent-infra", HOME / "Projects" / "agent-infra",
              ("tests/", "scripts/tests/", "-m", "not slow")),
    # Deliberately NOT monitored:
    #   genomics — no wholesale-runnable suite by design (the justfile runs
    #     curated subsets; ~20 modal test modules read GENOMICS_SAMPLE_ID at
    #     import and abort a full `pytest tests/`). With no "completes" baseline
    #     to protect, monitoring it would false-alarm daily — pure noise. Add it
    #     only if genomics gains a canonical full-suite entrypoint.
    #   intel — no tests/ directory.
)

# COMPLETED outcomes produce a real verdict; everything else means the suite
# could not even run to a verdict (the high-signal alarm).
_COMPLETED = {"passed", "failed"}
_EXIT_OUTCOME = {
    0: "passed", 1: "failed", 2: "collection_error",
    3: "internal_error", 4: "usage_error", 5: "no_tests",
}


def classify_outcome(returncode: int, *, timed_out: bool) -> str:
    """Map a pytest run to an outcome. Pure (unit-tested)."""
    if timed_out:
        return "timeout"
    if returncode in _EXIT_OUTCOME:
        return _EXIT_OUTCOME[returncode]
    # Killed by a signal (139=SIGSEGV, 134=SIGABRT, …) → 128+N, or negative via
    # subprocess. The certificates SIGSEGV landed here.
    return "crashed"


_COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped|xfailed|xpassed|deselected)")


def parse_counts(summary_tail: str) -> dict[str, int]:
    """Extract counts from pytest's final summary line. Pure (unit-tested)."""
    counts: dict[str, int] = {}
    for n, label in _COUNT_RE.findall(summary_tail):
        key = "errors" if label == "error" else label
        counts[key] = counts.get(key, 0) + int(n)
    return counts


def is_regression(current: dict, previous: dict | None) -> tuple[bool, str]:
    """Did the suite get WORSE than its previous run? Pure (unit-tested).

    The completion check answers "is the signal alive"; this answers "did it
    regress" — the common drift mode where a suite still RUNS but more tests
    fail. Regression = a previously-completing suite stopped completing, OR a
    completing suite gained failures/errors. No previous run → never a regression
    (nothing to compare). "Fewer passes" alone is NOT flagged — that's ambiguous
    (tests can be legitimately removed); only an INCREASE in failing tests is.
    """
    if not previous:
        return False, ""
    if previous.get("completed") and not current.get("completed"):
        return True, f"stopped completing → {current.get('outcome')}"
    if current.get("completed") and previous.get("completed"):
        cur = current.get("counts") or {}
        prev = previous.get("counts") or {}
        cur_bad = cur.get("failed", 0) + cur.get("errors", 0)
        prev_bad = prev.get("failed", 0) + prev.get("errors", 0)
        if cur_bad > prev_bad:
            return True, f"failing {prev_bad}→{cur_bad}"
    return False, ""


def load_prior(log_path: Path, repos: set[str]) -> dict[str, dict]:
    """Latest prior record per repo from the JSONL (append-ordered → last wins).
    Read BEFORE this run's records are written, so it is the previous baseline."""
    prior: dict[str, dict] = {}
    if not log_path.exists():
        return prior
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("repo") in repos:
            prior[rec["repo"]] = rec
    return prior


@dataclass
class SuiteResult:
    ts: str
    repo: str
    outcome: str
    completed: bool
    exit_code: int | None
    duration_s: float
    counts: dict
    detail: str


def run_suite(suite: RepoSuite, *, now: str) -> SuiteResult:
    if not suite.path.exists():
        return SuiteResult(now, suite.repo, "no_repo", False, None, 0.0, {},
                           f"repo path missing: {suite.path}")
    # `python3 -m pytest` (not the `pytest` console-script): the latter fails to
    # spawn from some repo roots, e.g. agent-infra — which would misfire as a
    # false "crashed". The module form runs wherever pytest is importable.
    cmd = ["uv", "run", "python3", "-m", "pytest", *suite.args,
           "-p", "no:cacheprovider", "-q", "--tb=no"]
    start = _monotonic()
    timed_out = False
    rc: int | None = None
    out_text = ""
    try:
        proc = subprocess.run(
            cmd, cwd=suite.path, capture_output=True, text=True, timeout=suite.timeout_s
        )
        rc = proc.returncode
        out_text = f"{proc.stdout or ''}{proc.stderr or ''}"
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        raw = exc.stdout
        if isinstance(raw, bytes):
            out_text = raw.decode("utf-8", "replace")
        elif isinstance(raw, str):
            out_text = raw
    duration = round(_monotonic() - start, 1)
    outcome = "timeout" if timed_out else classify_outcome(rc if rc is not None else 0,
                                                            timed_out=timed_out)
    # pytest's count summary is near the end, but warnings/errors can print
    # AFTER it — scan upward for the first line that actually carries counts,
    # falling back to the last non-empty line for the detail string.
    lines = [ln for ln in out_text.splitlines() if ln.strip()]
    tail = next((ln for ln in reversed(lines) if _COUNT_RE.search(ln)),
                lines[-1] if lines else "")
    counts = parse_counts(tail)
    return SuiteResult(
        ts=now, repo=suite.repo, outcome=outcome,
        completed=outcome in _COMPLETED, exit_code=rc, duration_s=duration,
        counts=counts, detail=tail[:300],
    )


def _monotonic() -> float:
    import time
    return time.monotonic()


def _icon_rec(rec: dict) -> str:
    if not rec["completed"] and rec["outcome"] != "no_repo":
        return "✗"  # did not complete — the alarm
    if rec.get("regressed"):
        return "⤓"  # completing, but worse than last run
    if rec["outcome"] == "passed":
        return "✓"
    return "!"      # completed with (unchanged) failures — report-only


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-repo test-suite health sentinel.")
    ap.add_argument("--json", action="store_true", help="emit JSON only (for launchd/dashboard)")
    ap.add_argument("--repo", help="run a single repo by name")
    args = ap.parse_args()

    now = datetime.now(timezone.utc).isoformat()
    suites = [s for s in SUITES if not args.repo or s.repo == args.repo]
    prior = load_prior(STATUS_LOG, {s.repo for s in suites})  # BEFORE we append
    results = [run_suite(s, now=now) for s in suites]

    # Augment each record with its regression verdict vs the previous run, then
    # persist (so the flag rides in the trend + is readable by `doctor`).
    records: list[dict] = []
    for r in results:
        rec = asdict(r)
        regressed, note = is_regression(rec, prior.get(r.repo))
        rec["regressed"] = regressed
        rec["regression_note"] = note
        records.append(rec)

    STATUS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with STATUS_LOG.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

    did_not_complete = [rec for rec in records
                        if not rec["completed"] and rec["outcome"] != "no_repo"]
    # A regression in a still-COMPLETING suite — the drift case the completion
    # check alone misses (suite runs, but more tests fail than last time).
    regressions = [rec for rec in records if rec["regressed"] and rec["completed"]]
    alarm = bool(did_not_complete or regressions)

    if args.json:
        print(json.dumps({
            "ts": now, "results": records,
            "did_not_complete": [r["repo"] for r in did_not_complete],
            "regressions": [{"repo": r["repo"], "note": r["regression_note"]} for r in regressions],
            "alarm": alarm,
        }, indent=2))
    else:
        print("[test-health]")
        for rec in records:
            c = rec["counts"]
            tally = " ".join(f"{c[k]}{k[0]}" for k in ("passed", "failed", "errors", "skipped") if c.get(k))
            flag = "  ⤓ REGRESSED: " + rec["regression_note"] if rec["regressed"] else ""
            print(f"  {_icon_rec(rec)} {rec['repo']:14} {rec['outcome']:16} {tally or '—':24} {rec['duration_s']:>6}s{flag}")
        if did_not_complete:
            print(f"\n  ✗ ALARM: {len(did_not_complete)} suite(s) did not complete: "
                  f"{', '.join(r['repo'] for r in did_not_complete)}")
            print("    A non-completing suite produces NO regression signal — investigate.")
        if regressions:
            print(f"\n  ⤓ ALARM: {len(regressions)} suite(s) regressed since last run: "
                  + ", ".join(f"{r['repo']} ({r['regression_note']})" for r in regressions))
        if not alarm:
            print("\n  ✓ all suites completed, none regressed")

    # Exit non-zero on a DID-NOT-COMPLETE (signal dead) OR a regression (signal
    # got worse). Standing pre-existing failures that are UNCHANGED don't alarm —
    # only a transition does, so this fires on the edge, not as a daily nag.
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(main())
