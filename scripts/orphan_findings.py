#!/usr/bin/env python3
"""orphan_findings.py — the orphaned-FINDINGS ratchet (report-only).

Sibling to orphan_check.py. That one catches orphaned *generators* (a script
nothing calls); this one catches orphaned *findings* — an adopt-grade research
verdict that never reached the loop's read path (improvement-log.md), so
/improve maintain never sees it and it dies in the memo.

This is the disease named in decisions/2026-06-04-consumption-over-autonomy.md
Finding 1: "a research finding with no consumer is equivalent to no verifier."
Generation is cheap; consumption is the bottleneck. trending-scout ran 11x over
~3 months and only 2 of ~33 adopt-grade verdicts were ever routed.

SCOPE: structured per-finding verdict memos only — `research/trending-scout-*.md`
(`### N. Title` + `| Verdict | **Adopt/Evaluate/Extract/Act now** |`). Sweep
memos are research synthesis (they inform future decisions, not discrete actions)
and are deliberately OUT of scope — forcing them through a [ ] gate would inflate
the actionable count (the F1 2026-06-08 miscount lesson).

ROUTED is a DETERMINISTIC signal, not a fuzzy text match: a memo's findings are
"routed" iff the memo PATH is cited in improvement-log.md (the explicit
`Source: research/<memo>` link convention). Fuzzy back-matching of free-text
titles against the corpus was tried and rejected — it produced false negatives
(a memo's own creation commit cites its filename in git; `agent`+`context` token
pairs match everywhere), and a finding-with-no-consumer hidden by a spurious
match is exactly the silent loss we are preventing.

So a memo is FLAGGED (un-harvested) when it has ≥1 actionable verdict
(Adopt/Act now/Extract/Evaluate) AND its path is not cited in improvement-log.
This OVER-reports (a finding adopted inline without a log entry still flags) — by
design: report-only, a human / the harvest step re-verifies and promotes the
genuinely-live ones to [ ] (Watch/Ignore/done-inline/stale stay out). The
going-forward fix is finding-side routing (trending-scout Pipeline Output step 3
+ improve harvest), which makes citation the norm so this signal stays clean.

ROUTED is finding-level (fixed 2026-06-14 after cross-model critique flagged that
memo-level clearing + source-routing = a false-all-clear generator: citing one
finding cleared the whole memo). A finding is routed iff EITHER its memo is in an
explicit RECONCILIATION log entry (bulk-triage assertion — the only whole-memo
clear) OR ≥2 distinctive tokens of its title appear in the (small, curated)
improvement-log. Title-token matching is scoped to the log ONLY — never the whole
git/decisions corpus (that gave false negatives; see git note below).

KNOWN LIMITATIONS (deliberately un-fixed — measured ~0 backlog, one operator, so
heavier machinery is over-engineering; revisit on the stated trigger). The
cross-model panel (2026-06-14) proposed stable finding IDs + a consumption ledger
+ auto-ingestion; DECLINED — finding-level token-match against the curated log
closes the silent-recurrence hole without new ID grammar, and auto-promotion
would reintroduce the F1 [ ]-inflation risk (promotion needs judgment):
  - Scope = trending-scout only (the one generator we KNOW leaked). Other
    generators (sweeps deliberately excluded; /leverage; research proposals) are
    not covered. Trigger to generalize: a second generator is found leaking.
  - Consumption is still instruction-driven (harvest 2f / source routing); only
    DETECTION is deterministic (this script in doctor). If the doctor line gets
    rubber-stamped, promote from advisory to a maintain-tick gate.
Drift guard: tests/test_orphan_findings.py asserts the parser still matches a real
memo (format drift would otherwise return 0 = silent false all-clear).

Usage:
    uv run python3 scripts/orphan_findings.py            # recent (90d) human report
    uv run python3 scripts/orphan_findings.py --all      # full catch-up reconciliation
    uv run python3 scripts/orphan_findings.py --json
"""
from __future__ import annotations

# Gov-ID: tool:orphan-findings
# goal: prevent silent generation-without-consumption — an adopt-grade research
#       finding that never reaches the loop's read path (improvement-log).
# verifier: scripts/tests/test_orphan_findings.py
# blast_radius: local
# kill-criterion: this is a SCAFFOLD, not durable infra. The disease it guards had
#   measured backlog ≈ 0 at build (2026-06-13); it earns its place only while it
#   catches real un-routed findings. Retire (delete tool + harvest 2f + the doctor
#   check, revert to documenting the gap) if `global:orphan-findings` produces ZERO
#   genuine promotions by 2026-08-13 (60d). gov-shrink owns the re-check; do not let
#   a report-only ratchet become a permanent ignored line (the alert-fatigue trap).

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESEARCH = REPO / "research"
LOG = REPO / "improvement-log.md"

ACTIONABLE = ("adopt", "act now", "extract", "evaluate")  # verdict substrings
NONACTIONABLE = ("watch", "ignore", "fyi")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_STOP = set(
    "the a an and or of to in for on with new now via and/or claude code anthropic "
    "openai google sdk cli api mode default model paper cluster deltas release".split()
)


def title_tokens(title: str) -> set[str]:
    """Distinctive lowercase tokens from a finding title (drop versions/stopwords)."""
    t = re.sub(r"\(.*?\)", " ", title.lower())   # drop parentheticals (versions/scores)
    t = re.sub(r"\bv?\d[\d.]*\b", " ", t)         # version numbers
    t = re.sub(r"[`*/_,.:→—–-]", " ", t)
    return {w for w in t.split() if len(w) >= 4 and w not in _STOP}


def reconciled_stems(log_text: str, memos: list[Path]) -> set[str]:
    """Memo stems explicitly bulk-triaged: mentioned inside a RECONCILIATION entry.
    This is the ONLY whole-memo clear — an explicit assertion that every finding was
    dispositioned. Incidental [ ] citations clear only the specific finding (below)."""
    out: set[str] = set()
    for entry in re.split(r"(?m)^#{2,4}\s", log_text):
        header = entry.split("\n", 1)[0].lower()
        if "reconcil" in header:
            el = entry.lower()
            out.update(m.stem.lower() for m in memos if m.stem.lower() in el)
    return out


def extract_findings(memo: Path) -> list[dict]:
    """Pull (title, verdict) pairs: a `### N. Title` heading + its nearest Verdict cell."""
    lines = memo.read_text(errors="ignore").splitlines()
    out: list[dict] = []
    cur_title = None
    for ln in lines:
        h = re.match(r"^###\s+\d+\.\s+(.*)", ln)
        if h:
            cur_title = h.group(1).strip()
            continue
        v = re.match(r"^\|\s*Verdict\s*\|\s*(.+?)\s*\|", ln)
        if v and cur_title:
            verdict = v.group(1).strip()
            vl = verdict.lower()
            actionable = any(a in vl for a in ACTIONABLE) and not any(
                vl.startswith(n) for n in NONACTIONABLE
            )
            out.append(
                {
                    "memo": memo.name,
                    "title": cur_title,
                    "verdict": verdict,
                    "actionable": actionable,
                }
            )
            cur_title = None
    return out


def scan(since_days: int = 90, all_memos: bool = False) -> dict:
    memos = sorted(RESEARCH.glob("trending-scout-*.md"))
    if not all_memos:
        cutoff = (datetime.now() - timedelta(days=since_days)).strftime("%Y-%m-%d")
        def _date(m: Path) -> str:
            mm = DATE_RE.search(m.name)
            return mm.group(1) if mm else "0"
        memos = [m for m in memos if _date(m) >= cutoff]
    log_text = LOG.read_text(errors="ignore") if LOG.exists() else ""
    log_low = log_text.lower()
    reconciled = reconciled_stems(log_text, memos)

    total = actionable = 0
    flagged: list[dict] = []  # one entry per memo with ≥1 un-routed finding
    for memo in memos:
        findings = extract_findings(memo)
        acts = [f for f in findings if f["actionable"]]
        total += len(findings)
        actionable += len(acts)
        if not acts:
            continue
        bulk = memo.stem.lower() in reconciled  # whole-memo clear ONLY via explicit reconciliation
        unrouted = []
        for f in acts:
            if bulk:
                continue
            # finding-level: ≥2 distinctive title tokens present in the (small, curated) log.
            # Closes the partial-citation hole — citing one finding no longer clears siblings.
            toks = title_tokens(f["title"])
            if len(toks) >= 2 and sum(1 for t in toks if t in log_low) >= 2:
                continue
            unrouted.append(f)
        if unrouted:
            flagged.append(
                {
                    "memo": memo.name,
                    "actionable_count": len(unrouted),
                    "findings": [{"title": f["title"], "verdict": f["verdict"]} for f in unrouted],
                }
            )
    return {
        "total_findings": total,
        "actionable": actionable,
        "memos_scanned": len(memos),
        "flagged_memos": flagged,
        "orphaned_findings": sum(m["actionable_count"] for m in flagged),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="scan all memos (full reconciliation)")
    ap.add_argument("--since", type=int, default=90, help="recency window in days (default 90)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rep = scan(since_days=a.since, all_memos=a.all)
    if a.json:
        print(json.dumps(rep, indent=2))
        return 0
    scope = "all memos" if a.all else f"last {a.since}d"
    print(f"orphan_findings ({scope}): {rep['memos_scanned']} trending memos, "
          f"{rep['actionable']} actionable verdicts, "
          f"{rep['orphaned_findings']} un-harvested in {len(rep['flagged_memos'])} memo(s)")
    for m in rep["flagged_memos"]:
        print(f"\n  ▸ {m['memo']} — {m['actionable_count']} actionable, not cited in improvement-log:")
        for f in m["findings"]:
            print(f"      · {f['title']}  [{f['verdict']}]")
    if rep["flagged_memos"]:
        print("\nReport-only (over-reports: done-inline findings still flag). Re-verify each, "
              "then promote genuinely-live ones to improvement-log.md as [ ] citing the memo "
              "path (Watch/Ignore/done/stale stay out).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
