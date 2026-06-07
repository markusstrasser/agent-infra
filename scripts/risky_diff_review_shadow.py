#!/usr/bin/env python3
"""Risky-diff-review SHADOW detector — REPORT-ONLY git-history analyzer.

Measures (does NOT enforce) how often a HIGH-BLAST-RADIUS diff lands with NO
cheap verifier (no accompanying test) AND no review signal in its session. This
is the demand probe for "should we auto-trigger the existing reviewer
(fresh-eyes-review / /critique) on risky diffs?" — the only genuine delta the
writer/reviewer-separation idea offers us (the capability already exists 6x; see
decisions/2026-06-07 guardian-angels + the verifier-conditioned amendment).

Per the verifier-conditioned regime (CLAUDE.md Generative Principle): clear-verifier
code (has tests) needs no separate reviewer — the tests ARE the reviewer. The
signal worth counting is the OTHER regime: irreversible / high-blast-radius diffs
with no cheap verifier. This detector counts exactly those that also went
unreviewed.

SHADOW: logs only. No blocking, no surface change. Consumer = the promote/cut
decision (see `--report`), default review date 2026-06-21 (~2 weeks). Promote to
an auto-review gate ONLY if it fires often AND those commits correlate with later
fixes; cut if it rarely fires (Opus 4.8 self-review-degeneracy did NOT reproduce,
decisions/2026-06-03-verifier-bound-autonomy.md, so a low rate is the live hypothesis).

Callable:
    uv run python3 scripts/risky_diff_review_shadow.py --days 30           # scan + print
    uv run python3 scripts/risky_diff_review_shadow.py --days 30 --log     # + append JSONL
    uv run python3 scripts/risky_diff_review_shadow.py --report            # consumer summary
and importable (for gov.py):
    from risky_diff_review_shadow import find_unreviewed_risky
    findings = find_unreviewed_risky(days=14)  # list[dict]

ALL git reads use `git --no-pager ... --no-ext-diff` (external differs inject
control bytes — ~/.claude/CLAUDE.md <environment>).
"""

# Gov-ID: hook:risky-diff-review-shadow
# goal: measure unreviewed high-blast-radius diffs (report-only, shadow)
# verifier: null
# blast_radius: local

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHADOW_LOG = Path.home() / ".claude" / "risky-diff-shadow.jsonl"

# --- High-blast-radius classification (path -> reason) ---------------------
# Each (regex, reason). A commit is risky if ANY changed path matches.
_BLAST_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(^|/)CLAUDE\.md$|(^|/)GOALS\.md$"), "constitution/goals"),
    (re.compile(r"(^|/)\.claude/rules/.*\.md$"), "behavioral-rule"),
    (re.compile(r"(^|/)hooks/|(-|_)guard\.(sh|py)$|(^|/).*hook.*\.(sh|py)$"), "hook"),
    (re.compile(r"\.sql$|(^|/)migrations?/|schema"), "schema/contract"),
    (re.compile(r"(^|/)\.claude/settings\.json$|(^|/)\.mcp\.json$"), "settings/mcp"),
]
# Test presence = a cheap verifier accompanied the change.
_TEST_RE = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.py)$|(^|/)tests?/")
# Review signal in a commit subject (best-effort; cross-referenced per session).
_REVIEW_RE = re.compile(
    r"\b(review(ed|s)?|critique|cross.?model|fresh.?eyes|adversaria|model-review)\b", re.I
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "--no-pager", *args, "--no-ext-diff"] if args and args[0] in {"log", "show", "diff"} else ["git", *args],
        cwd=REPO, capture_output=True, text=True,
    ).stdout


def read_commits(days: int) -> list[str]:
    """SHAs in the window, newest first. Sole commit-list git point."""
    out = _git("log", f"--since={days} days ago", "--no-merges", "--format=%H")
    return [s for s in out.splitlines() if s.strip()]


def commit_info(sha: str) -> dict:
    """Metadata + changed files for one commit. Sole per-commit git point."""
    meta = _git(
        "show", "--no-patch",
        "--format=%aI%x1f%s%x1f%(trailers:key=Session-ID,valueonly)%x1f%b", sha,
    ).strip().split("\x1f")
    date = meta[0] if len(meta) > 0 else ""
    subject = meta[1] if len(meta) > 1 else ""
    session = (meta[2].strip() if len(meta) > 2 else "") or "unknown"
    # Review signal often lives in the BODY (e.g. "Cross-model review (Gemini +
    # GPT-5.5)…"), not the subject. Scan both.
    body = meta[3] if len(meta) > 3 else ""
    files = [f for f in _git("show", "--name-only", "--format=", sha).splitlines() if f.strip()]
    return {"sha": sha, "date": date, "subject": subject, "session": session,
            "msg": f"{subject}\n{body}", "files": files}


def blast_reasons(files: list[str]) -> list[str]:
    reasons = []
    for rx, reason in _BLAST_RULES:
        if any(rx.search(f) for f in files) and reason not in reasons:
            reasons.append(reason)
    return reasons


def classify(days: int) -> list[dict]:
    """All commits in window, annotated. Risky ones flagged for review status."""
    commits = [commit_info(s) for s in read_commits(days)]
    # Build per-session review signal: a session is "reviewed" if ANY of its
    # commits in-window has a review subject (best-effort proxy for /critique
    # or fresh-eyes-review having fired that session).
    reviewed_sessions = {
        c["session"] for c in commits if _REVIEW_RE.search(c["msg"])
    }
    findings = []
    for c in commits:
        reasons = blast_reasons(c["files"])
        if not reasons:
            continue
        had_test = any(_TEST_RE.search(f) for f in c["files"])
        had_review = bool(_REVIEW_RE.search(c["msg"])) or c["session"] in reviewed_sessions
        verdict = (
            "UNREVIEWED_RISKY" if not had_test and not had_review
            else "covered"
        )
        findings.append({
            "sha": c["sha"][:10],
            "date": c["date"][:10],
            "session": c["session"][:8],
            "subject": c["subject"][:80],
            "blast_reasons": reasons,
            "had_test": had_test,
            "had_review": had_review,
            "verdict": verdict,
        })
    return findings


def find_unreviewed_risky(days: int = 14) -> list[dict]:
    """Importable entrypoint for gov.py — only the UNREVIEWED_RISKY findings."""
    return [f for f in classify(days) if f["verdict"] == "UNREVIEWED_RISKY"]


def append_log(findings: list[dict]) -> int:
    """Append findings to the shadow JSONL, deduped by sha. Returns new rows."""
    seen = set()
    if SHADOW_LOG.exists():
        for line in SHADOW_LOG.read_text().splitlines():
            try:
                seen.add(json.loads(line)["sha"])
            except Exception:
                continue
    new = [f for f in findings if f["sha"] not in seen]
    if new:
        SHADOW_LOG.parent.mkdir(parents=True, exist_ok=True)
        with SHADOW_LOG.open("a") as fh:
            for f in new:
                fh.write(json.dumps(f) + "\n")
    return len(new)


def report() -> dict:
    """Consumer summary over the accumulated shadow log (the promote/cut input)."""
    rows = []
    if SHADOW_LOG.exists():
        for line in SHADOW_LOG.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    risky = rows  # every logged row is risky by construction
    unrev = [r for r in risky if r["verdict"] == "UNREVIEWED_RISKY"]
    reasons = Counter(reason for r in unrev for reason in r["blast_reasons"])
    return {
        "logged_risky": len(risky),
        "unreviewed_risky": len(unrev),
        "rate": round(len(unrev) / len(risky), 2) if risky else 0.0,
        "by_reason": dict(reasons.most_common()),
        "unreviewed_shas": [r["sha"] for r in unrev],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=30, help="scan window (default 30)")
    ap.add_argument("--log", action="store_true", help="append findings to shadow JSONL")
    ap.add_argument("--report", action="store_true", help="print consumer summary over accumulated log")
    ap.add_argument("--json", action="store_true", help="JSON output")
    a = ap.parse_args()

    if a.report:
        rep = report()
        print(json.dumps(rep, indent=2) if a.json else (
            f"[risky-diff shadow] logged_risky={rep['logged_risky']} "
            f"unreviewed_risky={rep['unreviewed_risky']} rate={rep['rate']}\n"
            f"  by_reason: {rep['by_reason']}\n"
            f"  unreviewed: {', '.join(rep['unreviewed_shas']) or '(none)'}"
        ))
        return 0

    findings = classify(a.days)
    risky = len(findings)
    unrev = sum(1 for f in findings if f["verdict"] == "UNREVIEWED_RISKY")
    if a.log:
        added = append_log(findings)
        print(f"  ✓ logged {added} new rows to {SHADOW_LOG}")
    if a.json:
        print(json.dumps(findings, indent=2))
    else:
        print(f"[risky-diff shadow] window={a.days}d  risky={risky}  unreviewed_risky={unrev}")
        for f in findings:
            mark = "✗" if f["verdict"] == "UNREVIEWED_RISKY" else "·"
            print(f"  {mark} {f['sha']} {f['date']} [{','.join(f['blast_reasons'])}]"
                  f" test={'Y' if f['had_test'] else 'n'} rev={'Y' if f['had_review'] else 'n'}"
                  f" — {f['subject']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
