#!/usr/bin/env python3
"""Hook outcome correlator — join hook triggers with session receipts.

Correlates hook fire events with session outcomes (cost, duration, context%)
to measure whether hooks actually improve sessions.

Per-hook outputs:
  - Fire rate (triggers/session)
  - Block rate (blocks/triggers)
  - Outcome delta: avg cost/duration when hook fired vs not
  - Effectiveness score and promotion/demotion proposals

Usage:
  uv run python3 scripts/hook-outcome-correlator.py [--days N] [--verbose]
  uv run python3 scripts/hook-outcome-correlator.py --effectiveness [--days N]
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from common.paths import TRIGGERS_FILE, RECEIPTS_PATH as RECEIPTS_FILE
from common.io import load_jsonl


# Hook deployment dates — when each hook was first deployed.
# Used for before/after effectiveness measurement.
# Derived from: git -C ~/Projects/skills log --format="%ai %s" -- hooks/
HOOK_DEPLOY_DATES: dict[str, str] = {
    "commit-check": "2026-03-01",
    "search-burst": "2026-03-01",
    "subagent-gate": "2026-03-01",
    "source-check": "2026-03-02",
    "spinning": "2026-03-08",
    "bash-failure-loop": "2026-03-17",
    "dup-read": "2026-03-26",
    "bash-poll": "2026-03-29",
    "multiagent-commit": "2026-04-03",
}


def effectiveness_report(days: int):
    """Before/after effectiveness analysis per hook deployment date.

    For each hook with a known deploy date, compare trigger rates in sessions
    before vs after deployment. A hook is effective if the target behavior
    (measured by trigger rate per session) decreased after deployment.
    """
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    triggers = load_jsonl(TRIGGERS_FILE, since=cutoff)
    receipts = load_jsonl(RECEIPTS_FILE, since=cutoff)

    if not triggers or not receipts:
        print(f"Insufficient data in last {days} days.")
        return

    # Count sessions per day from receipts (normalization denominator)
    sessions_per_day: dict[str, int] = defaultdict(int)
    for r in receipts:
        ts = r.get("ts", r.get("start", ""))
        if ts:
            sessions_per_day[ts[:10]] += 1

    # Group triggers by hook and day
    hook_day_triggers: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t in triggers:
        hook = t.get("hook", "?")
        ts = t.get("ts", "")
        if ts:
            hook_day_triggers[hook][ts[:10]] += 1

    all_days = sorted(sessions_per_day.keys())

    print(f"{'=' * 85}")
    print(f"  Hook Effectiveness Analysis — last {days} days")
    print(f"  Method: daily trigger rate (triggers/day) before vs after deployment")
    print(f"{'=' * 85}")
    print()
    print(f"  {'HOOK':<25} {'DEPLOYED':>10} {'DAYS_PRE':>8} {'TRIG/DAY':>8} "
          f"{'DAYS_POST':>9} {'TRIG/DAY':>8} {'CHANGE':>7} {'LABEL'}")
    print(f"  {'-' * 85}")

    for hook_name in sorted(HOOK_DEPLOY_DATES):
        deploy_date = HOOK_DEPLOY_DATES[hook_name]
        day_triggers = hook_day_triggers.get(hook_name, {})

        # Split days into before/after deployment
        days_before = [d for d in all_days if d < deploy_date]
        days_after = [d for d in all_days if d >= deploy_date]

        if not days_before and not days_after:
            print(f"  {hook_name:<25} {deploy_date:>10} {'—':>8} {'—':>8} "
                  f"{'—':>9} {'—':>8} {'—':>7} [NO DATA]")
            continue

        # Triggers per day in each period
        total_before = sum(day_triggers.get(d, 0) for d in days_before)
        total_after = sum(day_triggers.get(d, 0) for d in days_after)

        n_before = max(len(days_before), 1)
        n_after = max(len(days_after), 1)

        rate_before = total_before / n_before
        rate_after = total_after / n_after

        # For hooks deployed before our window, "before" is empty — show post-only
        if not days_before:
            print(f"  {hook_name:<25} {deploy_date:>10} {'—':>8} {'—':>8} "
                  f"{n_after:>9} {rate_after:>8.1f} {'—':>7} [PRE-WINDOW]")
            continue

        # Change ratio (negative = fewer triggers = hook working)
        if rate_before > 0:
            change = (rate_after - rate_before) / rate_before
            change_str = f"{change:+.0%}"
        elif rate_after > 0:
            change_str = "+∞"
            change = 1.0
        else:
            change_str = "0%"
            change = 0.0

        # Labels
        min_days = min(n_before, n_after)
        if min_days < 3:
            label = "[UNDERPOWERED]"
        elif change < -0.25:
            label = "[EFFECTIVE]"
        elif change < 0:
            label = "[MARGINAL]"
        elif change == 0:
            label = "[NO CHANGE]"
        else:
            label = "[RISING]"  # triggers increased — hook not preventing

        print(f"  {hook_name:<25} {deploy_date:>10} {n_before:>8} "
              f"{rate_before:>8.1f} {n_after:>9} {rate_after:>8.1f} "
              f"{change_str:>7} {label}")

    print()
    print("  NOTE: Observational, not causal. Session volume varies over time.")
    print("  TRIG/DAY = average daily trigger count. Lower post-deploy = hook is working.")
    print("  [RISING] = triggers increased post-deploy — hook may not be preventing behavior.")
    print("  [UNDERPOWERED] = <3 days in either period — interpret with caution.")
    print()


def main():
    days = 7
    verbose = "--verbose" in sys.argv
    effectiveness = "--effectiveness" in sys.argv
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    if effectiveness:
        effectiveness_report(days if days != 7 else 30)
        return

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    triggers = load_jsonl(TRIGGERS_FILE, since=cutoff)
    receipts = load_jsonl(RECEIPTS_FILE, since=cutoff)

    if not triggers:
        print(f"No hook triggers in the last {days} days.")
        return
    if not receipts:
        print(f"No session receipts in the last {days} days.")
        return

    # Build session -> receipt lookup
    session_data: dict[str, dict] = {}
    for r in receipts:
        sid = r.get("session", "")
        if sid:
            session_data[sid] = r

    # Group triggers by session
    triggers_by_session: dict[str, list[dict]] = defaultdict(list)
    for t in triggers:
        sid = t.get("session", "unknown")
        triggers_by_session[sid].append(t)

    # Sessions with known IDs (not "unknown")
    known_sessions = {sid for sid in triggers_by_session if sid != "unknown"}
    unknown_count = len(triggers_by_session.get("unknown", []))

    # Build per-hook stats
    hook_stats: dict[str, dict] = defaultdict(lambda: {
        "total_fires": 0, "blocks": 0, "warns": 0,
        "sessions_fired": set(), "sessions_blocked": set(),
    })

    for sid, session_triggers in triggers_by_session.items():
        if sid == "unknown":
            # Still count for aggregate stats
            for t in session_triggers:
                hook = t.get("hook", "?")
                action = t.get("action", "?")
                hook_stats[hook]["total_fires"] += 1
                if action == "block":
                    hook_stats[hook]["blocks"] += 1
                elif action == "warn":
                    hook_stats[hook]["warns"] += 1
            continue

        for t in session_triggers:
            hook = t.get("hook", "?")
            action = t.get("action", "?")
            hook_stats[hook]["total_fires"] += 1
            hook_stats[hook]["sessions_fired"].add(sid)
            if action == "block":
                hook_stats[hook]["blocks"] += 1
                hook_stats[hook]["sessions_blocked"].add(sid)
            elif action == "warn":
                hook_stats[hook]["warns"] += 1

    # Compute outcome deltas for hooks with session-level data
    all_session_ids = set(session_data.keys())
    all_costs = [r.get("cost_usd", 0) or 0 for r in receipts if r.get("cost_usd")]
    avg_cost = sum(all_costs) / len(all_costs) if all_costs else 0

    print(f"{'=' * 65}")
    print(f"  Hook Outcome Correlator — last {days} days")
    print(f"{'=' * 65}")
    print()
    print(f"  Triggers:     {len(triggers)} ({unknown_count} with unknown session ID)")
    print(f"  Receipts:     {len(receipts)} sessions")
    print(f"  Avg cost:     ${avg_cost:.2f}/session")
    print(f"  Correlation:  {len(known_sessions)} sessions have both triggers + receipts")
    if unknown_count > 0:
        pct = unknown_count / len(triggers) * 100
        print(f"  WARNING:      {pct:.0f}% of triggers lack session IDs — correlation is partial")
    print()

    # Per-hook analysis
    print(f"  {'HOOK':<30} {'FIRES':>5} {'BLOCK':>5} {'WARN':>5} {'SESS':>5} {'COST_D':>8} {'VERDICT'}")
    print(f"  {'-' * 75}")

    for hook_name in sorted(hook_stats, key=lambda h: -hook_stats[h]["total_fires"]):
        stats = hook_stats[hook_name]
        fires = stats["total_fires"]
        blocks = stats["blocks"]
        warns = stats["warns"]
        sessions_fired = stats["sessions_fired"]
        sessions_blocked = stats["sessions_blocked"]

        # Compute cost delta: sessions where hook fired vs sessions where it didn't
        fired_costs = [
            session_data[sid].get("cost_usd", 0) or 0
            for sid in sessions_fired if sid in session_data
        ]
        unfired_sids = all_session_ids - sessions_fired
        unfired_costs = [
            session_data[sid].get("cost_usd", 0) or 0
            for sid in unfired_sids if sid in session_data
        ]

        cost_delta = ""
        if fired_costs and unfired_costs:
            avg_fired = sum(fired_costs) / len(fired_costs)
            avg_unfired = sum(unfired_costs) / len(unfired_costs)
            delta = avg_fired - avg_unfired
            cost_delta = f"{'+'if delta>=0 else ''}{delta:.2f}"

        # Verdict
        verdict = ""
        if blocks > 10 and fires > 0 and blocks / fires > 0.8:
            verdict = "DEMOTE?"
        elif fires > 20 and blocks == 0:
            verdict = "PROMOTE?"
        elif fires > 0 and blocks > 0 and blocks / fires < 0.1:
            verdict = "ok"
        elif blocks > 0:
            verdict = "ok"
        else:
            verdict = "-"

        print(f"  {hook_name:<30} {fires:>5} {blocks:>5} {warns:>5} "
              f"{len(sessions_fired):>5} {cost_delta:>8} {verdict}")

    print()

    # Recommendations
    print("  Recommendations:")
    recs = []
    for hook_name, stats in hook_stats.items():
        fires = stats["total_fires"]
        blocks = stats["blocks"]
        if fires == 0:
            continue
        if blocks > 10 and blocks / fires > 0.8:
            recs.append(f"    DEMOTE? {hook_name} — {blocks}/{fires} blocks "
                        f"({blocks/fires:.0%}). Review for false positives.")
        elif fires > 20 and blocks == 0:
            recs.append(f"    PROMOTE? {hook_name} — {fires} fires, 0 blocks. "
                        f"Consider upgrading to block if the warn is effective.")

    if recs:
        for r in recs:
            print(r)
    else:
        print("    (No actionable recommendations yet)")

    if unknown_count > len(triggers) * 0.5:
        print()
        print("    NOTE: >50% of triggers lack session IDs. Fix CLAUDE_SESSION_ID")
        print("    propagation to enable meaningful correlation.")
    print()

    if verbose:
        print("  Per-session breakdown:")
        for sid in sorted(known_sessions):
            receipt = session_data.get(sid, {})
            striggers = triggers_by_session[sid]
            hooks_fired = set(t.get("hook", "?") for t in striggers)
            cost = receipt.get("cost_usd", 0) or 0
            proj = receipt.get("project", "?")
            print(f"    {sid[:12]}  {proj:<12} ${cost:.2f}  hooks: {', '.join(sorted(hooks_fired))}")
        print()


if __name__ == "__main__":
    main()
