#!/usr/bin/env python3
"""Hook outcome correlator — join hook triggers with session receipts.

Correlates hook fire events with session outcomes (cost, duration, context%)
to measure whether hooks actually improve sessions.

Per-hook outputs:
  - Fire rate (triggers/session)
  - Block rate (blocks/triggers)
  - Outcome delta: avg cost/duration when hook fired vs not
  - Effectiveness score and promotion/demotion proposals

Usage: uv run python3 scripts/hook-outcome-correlator.py [--days N] [--verbose]
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

TRIGGERS_FILE = Path.home() / ".claude" / "hook-triggers.jsonl"
RECEIPTS_FILE = Path.home() / ".claude" / "session-receipts.jsonl"


def load_jsonl(path: Path, cutoff: str) -> list[dict]:
    """Load JSONL entries after cutoff timestamp."""
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = entry.get("ts", "")
            if ts >= cutoff:
                entries.append(entry)
    return entries


def main():
    days = 7
    verbose = "--verbose" in sys.argv
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    triggers = load_jsonl(TRIGGERS_FILE, cutoff)
    receipts = load_jsonl(RECEIPTS_FILE, cutoff)

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
