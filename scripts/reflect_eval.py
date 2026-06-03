#!/usr/bin/env python3
"""reflect_eval.py — grade the learning loop against its pre-registered tests.

The plan (4d40085a) committed a 2-week shadow window then a go/cut decision. This
computes the DETERMINISTIC metrics from local shadow data and surfaces the
HUMAN-judgment items. It runs the classify pass (auto-records evidence to existing
FMs — authorized low-blast bookkeeping) then measures. It NEVER enables an omission
surface or applies an enforcer — go/cut and surface-enablement are human calls.

Pre-registered tests graded:
  1. COMPACTION  — unique proposals / captured incidents <= 0.35; attach >= 80% / mint <= 20%
  3. OMISSION PPV — surfaced for human labeling; surface stays OFF until PPV >= 60%
  4. THROUGHPUT  — quarantine pending count, p90 age <= 7d; backlog slope <= 0 (needs >=2 runs)

Usage: reflect_eval.py [--report]   (--report also writes artifacts/reflect-eval/<date>.md)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reflect  # noqa: E402  (pulls in fm transitively)

REPO = Path(__file__).resolve().parent.parent
HISTORY = Path.home() / ".claude" / "reflect-eval-history.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _age_days(ts: str) -> float:
    try:
        t = datetime.fromisoformat(ts)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - t).total_seconds() / 86400
    except (ValueError, TypeError):
        return 0.0


def evaluate(dry: bool = False) -> dict:
    # 1. process accumulated shadow data (auto-records evidence; quarantines proposals)
    classify = reflect.run_classify(dry_run=dry)

    capture = reflect.load_capture()
    incidents = len(capture)
    kinds = Counter(s.get("kind", "?") for s in capture)
    omissions_by_subtype = Counter(
        s.get("subtype", "?") for s in capture if s.get("kind") == "omission")

    pending = reflect._load_pending()
    proposals = [p for _, _, p in pending]
    actions = Counter(p.get("action") for p in proposals)
    attach_enf = sum(1 for p in proposals if p.get("action") not in ("mint", "needs-review"))
    mint_like = actions.get("mint", 0) + actions.get("needs-review", 0)
    total_props = len(proposals)

    # Test 1 — compaction
    ratio = (total_props / incidents) if incidents else 0.0
    attach_share = (attach_enf / total_props) if total_props else None
    t1_ratio_pass = incidents == 0 or ratio <= 0.35
    t1_attach_pass = attach_share is None or attach_share >= 0.80

    # Test 4 — throughput
    ages = [_age_days(p.get("ts", "")) for p in proposals]
    p90_age = sorted(ages)[int(0.9 * (len(ages) - 1))] if ages else 0.0
    t4_age_pass = p90_age <= 7
    prev = _last_history()
    slope = (len(proposals) - prev["pending"]) if prev else None  # >=2 runs needed

    result = {
        "ts": _utc(),
        "incidents": incidents, "kinds": dict(kinds),
        "proposals": total_props, "attach_enf": attach_enf, "mint_like": mint_like,
        "compaction_ratio": round(ratio, 3), "attach_share": attach_share,
        "omissions_by_subtype": dict(omissions_by_subtype),
        "pending": total_props, "p90_age_days": round(p90_age, 1), "backlog_slope": slope,
        "this_run": {"auto_recorded": len(classify["auto_recorded"]),
                     "quarantined": len(classify["quarantined"]),
                     "suppressed": classify.get("suppressed", 0)},
        "tests": {
            "T1_compaction": "PASS" if (t1_ratio_pass and t1_attach_pass) else "REVIEW",
            "T3_omission_ppv": "HUMAN — label firings; surface OFF until PPV>=60%",
            "T4_throughput": "PASS" if t4_age_pass and (slope is None or slope <= 0) else "REVIEW",
        },
    }
    if not dry:
        _append_history({"ts": result["ts"], "pending": total_props, "incidents": incidents})
    return result


def _last_history() -> dict | None:
    if not HISTORY.exists():
        return None
    rows = [l for l in HISTORY.read_text().splitlines() if l.strip()]
    for line in reversed(rows):
        try:
            return json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _append_history(row: dict) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def render(r: dict) -> str:
    L = [f"# Reflect-loop evaluation — {r['ts'][:10]}", "",
         f"Captured incidents: {r['incidents']} {r['kinds']}",
         f"Proposals (quarantine pending): {r['proposals']} "
         f"(attach/enforcer={r['attach_enf']}, mint/needs-review={r['mint_like']})",
         f"This run: +{r['this_run']['auto_recorded']} auto-recorded, "
         f"+{r['this_run']['quarantined']} quarantined, "
         f"{r['this_run']['suppressed']} cap-suppressed", "",
         "## Pre-registered tests", "",
         f"- **T1 compaction** [{r['tests']['T1_compaction']}] — ratio={r['compaction_ratio']} "
         f"(target ≤0.35), attach_share={r['attach_share']} (target ≥0.80)",
         f"- **T3 omission PPV** [{r['tests']['T3_omission_ppv']}] — firings by probe: "
         f"{r['omissions_by_subtype'] or '(none yet)'}",
         f"- **T4 throughput** [{r['tests']['T4_throughput']}] — pending={r['pending']}, "
         f"p90_age={r['p90_age_days']}d (target ≤7), backlog_slope={r['backlog_slope']}", "",
         "## Your decision (the loop has a built-in kill switch — cut, don't tune)", "",
         "1. T1/T4 REVIEW or red → recommend CUTTING that part, not tuning.",
         "2. T3: label a sample of the omission firings above. Only if PPV≥60% should you add "
         "the subtype to reflect.PPV_CLEARED (enables its surface). Until then it stays shadow.",
         "3. Net-maintenance: did the loop prevent more correction-sessions than its review cost?",
         "", "See plan .claude/plans/4d40085a-recursive-session-learning-loop.md (tests 1-6)."]
    return "\n".join(L)


def main() -> int:
    r = evaluate(dry="--dry" in sys.argv)
    report = render(r)
    print(report)
    if "--report" in sys.argv:
        out_dir = REPO / "artifacts" / "reflect-eval"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{r['ts'][:10]}.md"
        path.write_text(report + "\n", encoding="utf-8")
        print(f"\n[report] {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
