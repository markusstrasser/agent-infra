#!/usr/bin/env python3
"""Hook ROI telemetry — analyze hook trigger patterns.

Reads ~/.claude/hook-triggers.jsonl to show:
- Triggers per hook (total, warn, block)
- False positive candidates (blocks followed by immediate user override)
- Triggers by project
- Trend over time
- Transfer effectiveness (--transfer): per-project hook success for cross-project deployment tracking

Usage:
    hook-roi.py [--days N] [--verbose]
    hook-roi.py --transfer [--since YYYY-MM-DD] [--days N]
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from common.paths import TRIGGERS_FILE

# Advisory (non-blocking) action values — module-level so both the
# fire/block triage in main() and the outcome classifier below share ONE
# definition (epistemics principle #9: a shared invariant gets one
# definition, consumers load it — this list deciding "advisory vs blocking"
# is exactly that kind of invariant; two copies drifting would silently
# mislabel a guard's O2 flag).
ADVISORY = {"warn", "warn-only", "suggest", "remind", "advise", "log"}

# The exposure-clean action value the T3 guards (git-stash-guard,
# multiagent-commit, llmx-subscription-flag — see skills/hooks/pretool-*.py)
# emit when their precondition matched but nothing fired. Introduced
# 2026-07-18 alongside command fingerprinting (cmd_tok/cmd_fp) — see
# hook-trigger-log.sh and hook_cmd_fingerprint.py in the skills repo.
EXPOSURE_ACTION = "exposure-clean"


def load_triggers(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    # Binary-safe: the trigger log accumulates occasional non-utf8 bytes from
    # hook detail strings; a plain text open() raises UnicodeDecodeError and
    # crashes the whole report (this silently broke the tool, which is part of
    # why the ledger went unconsumed — fixed 2026-06-01).
    with open(path, "rb") as f:
        for raw in f:
            line = raw.decode("utf-8", "replace").strip()
            if line:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):  # skip bare JSON strings/scalars
                    entries.append(obj)
    return entries


def parse_ts(ts: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return datetime.min


def main(days: int = 7, verbose: bool = False):
    if days == 7 and "--days" in sys.argv:  # legacy CLI compat
        pass
    if "--verbose" in sys.argv:
        verbose = True
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    cutoff = datetime.now() - timedelta(days=days)
    triggers = load_triggers(TRIGGERS_FILE)
    recent = [t for t in triggers if parse_ts(t.get("ts", "")) > cutoff]

    if not recent:
        print(f"No hook triggers in the last {days} days.")
        if not TRIGGERS_FILE.exists():
            print(f"Trigger log not found at {TRIGGERS_FILE}")
            print("Hooks need to call hook-trigger-log.sh to populate this.")
        elif triggers:
            print(f"({len(triggers)} total triggers on file, all older than {days} days)")
        return

    # --- By hook ---
    by_hook: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t in recent:
        hook = t.get("hook", "?")
        action = t.get("action", "?")
        by_hook[hook][action] += 1
        by_hook[hook]["total"] += 1

    # --- By project ---
    by_project: dict[str, int] = defaultdict(int)
    for t in recent:
        by_project[t.get("project", "?")] += 1

    # --- By tool ---
    by_tool: dict[str, int] = defaultdict(int)
    for t in recent:
        tool = t.get("tool", "")
        if tool:
            by_tool[tool] += 1

    # --- By day ---
    by_day: dict[str, int] = defaultdict(int)
    for t in recent:
        day = t.get("ts", "")[:10]
        if day:
            by_day[day] += 1

    # --- Print ---
    print(f"{'=' * 55}")
    print(f"  Hook ROI Analysis — last {days} days")
    print(f"{'=' * 55}")
    print()
    print(f"  Total triggers:  {len(recent)}")
    print(f"  Unique hooks:    {len(by_hook)}")
    print()

    # Hook breakdown
    print("  By hook:")
    sorted_hooks = sorted(by_hook.items(), key=lambda x: x[1]["total"], reverse=True)
    for hook, actions in sorted_hooks:
        total = actions["total"]
        warns = actions.get("warn", 0)
        blocks = actions.get("block", 0)
        reminds = actions.get("remind", 0)
        allows = actions.get("allow", 0)
        parts = []
        if blocks:
            parts.append(f"{blocks} block")
        if warns:
            parts.append(f"{warns} warn")
        if reminds:
            parts.append(f"{reminds} remind")
        if allows:
            parts.append(f"{allows} allow")
        detail = ", ".join(parts) if parts else "?"
        print(f"    {hook:<30} {total:>4}  ({detail})")
    print()

    # Project breakdown
    print("  By project:")
    for proj, count in sorted(by_project.items(), key=lambda x: -x[1]):
        print(f"    {proj:<25} {count:>4}")
    print()

    # Tool breakdown
    if by_tool:
        print("  By tool (top 10):")
        for tool, count in sorted(by_tool.items(), key=lambda x: -x[1])[:10]:
            print(f"    {tool:<30} {count:>4}")
        print()

    # Daily trend
    if len(by_day) > 1:
        print("  Daily trend:")
        for day in sorted(by_day.keys()):
            bar = "#" * min(by_day[day], 50)
            print(f"    {day}  {by_day[day]:>4}  {bar}")
        print()

    # False positive candidates: blocks that are high-frequency
    # (if a hook blocks often, it might be too aggressive)
    block_heavy = [
        (h, a) for h, a in sorted_hooks
        if a.get("block", 0) > 5 and a.get("block", 0) / a["total"] > 0.5
    ]
    if block_heavy:
        print("  Potential false-positive hooks (>50% block rate, >5 blocks):")
        for hook, actions in block_heavy:
            rate = actions["block"] / actions["total"]
            print(f"    {hook}: {actions['block']}/{actions['total']} ({rate:.0%} block rate)")
        print()

    if verbose and triggers:
        print(f"  All-time: {len(triggers)} total triggers")

    # Recommendations — bidirectional triage by volume x block-rate.
    #
    # Key principle (2026-06-01, after the spinning-detector rot): high triggers
    # + 0 blocks is NOT a promote signal. For advisory hooks (warn/suggest/
    # remind) the agent reads every single fire and ignores most of them; a
    # high-volume advisory hook is NOISE to cull or narrow, not aggression to
    # add. The old logic here said "0 blocks -> PROMOTE to block" — which for
    # the spinning detector (~1945 fires/wk, 0 blocks, PostToolUse so it CANNOT
    # block) was exactly backwards. It was silenced, not promoted.
    # (ADVISORY is module-level now — shared with the outcome classifier below.)
    # Noise floor scales with the corpus so it stays meaningful at any window.
    total_fires = sum(a["total"] for _, a in sorted_hooks) or 1
    noise_floor = max(50, total_fires // 50)
    print("  Recommendations:")
    print("  (Candidates for judgment, not auto-actions. A high-volume advisory that")
    print("   enforces a real contract — e.g. source/provenance grading — is working")
    print("   as intended; cull NOISE, not enforcement. See feedback_hook_roi_ledger.)")
    printed = False
    for hook, actions in sorted_hooks:
        total = actions["total"]
        blocks = actions.get("block", 0)
        if total == 0:
            continue
        advisory = sum(actions.get(a, 0) for a in ADVISORY)
        if blocks > 10 and blocks / total > 0.8:
            print(f"    DEMOTE? {hook} — {blocks}/{total} blocks ({blocks/total:.0%}). "
                  f"Too aggressive; likely false-positive-heavy.")
            printed = True
        elif blocks == 0 and total >= noise_floor and advisory >= 0.9 * total:
            print(f"    CULL/NARROW? {hook} — {total} fires, 0 blocks, {advisory} advisory. "
                  f"High-volume nag the agent reads every turn and ignores. Silence it, "
                  f"narrow the matcher, fire once instead of per-call, or move to "
                  f"PreToolUse if it should actually PREVENT the action (PostToolUse "
                  f"advisories can only nag after the fact).")
            printed = True
        elif blocks == 0 and 20 <= total < noise_floor and advisory == total:
            print(f"    REVIEW? {hook} — {total} fires, 0 blocks. If this is a real "
                  f"recurring problem AND the hook runs PreToolUse, consider a hard block; "
                  f"otherwise it is working as an advisory — leave it.")
            printed = True
    if not printed:
        if not any(a["total"] > 10 for _, a in sorted_hooks):
            print("    (Not enough data yet for recommendations. Collect more triggers.)")
        else:
            print("    (No hooks flagged — block-rates and volumes look healthy.)")
    print()


# =============================================================================
# Outcome analysis (T2, 2026-07-18) — guard-forcerate-study /
# rescue-class-surface-closure-loop (arc-agi loop/backlog.jsonl rows 906/909).
#
# Consumes the cmd_tok/cmd_fp fingerprint fields skills/hooks/hook-trigger-
# log.sh started emitting the same day (T1), plus the "exposure-clean" action
# three guards now emit when their precondition matched but nothing fired
# (T3: git-stash-guard, multiagent-commit, llmx-subscription-flag).
#
# This is a HEURISTIC over log adjacency, not ground truth — see
# classify_outcomes()'s docstring and outcome_report()'s printed header for
# the honest limits before trusting a number out of it.
#
# Distinct from scripts/hook-outcome-correlator.py (`just hook-decay`), which
# correlates a hook's ACTIVE/deployed status with SESSION-level outcomes
# (cost, duration, context% via session-receipts.jsonl) — a coarser, before/
# after deployment-effectiveness question. This module answers a per-FIRE
# question instead: for one specific guard firing, did the agent comply,
# repeat the same command anyway, or abandon it. Checked at build time
# (2026-07-18): no overlap — the correlator never touches cmd_tok/cmd_fp/
# exposure-clean, which didn't exist before this file's own T1/T3 changes.
# =============================================================================


def _session_key(row: dict) -> str:
    return row.get("session") or "unknown"


def classify_outcomes(triggers: list[dict]) -> dict[str, dict]:
    """Per-guard OUTCOME classification over command-fingerprinted rows.

    Method: group all rows (fires AND exposure-clean rows) by (session,
    hook), sort by ts, and for each fire look at the NEXT row in that group
    sharing the same cmd_tok (coarse first token — "git", "llmx", ...):
      - same cmd_fp on that next row  -> REPEATED_ATTEMPT (the agent re-ran
        the identical command shape; a run of N identical-fp fires yields
        N-1 repeated-attempt transitions, one per adjacent pair — this
        counts TRANSITIONS, not distinct incidents).
      - next row is an exposure-clean row with a DIFFERENT cmd_fp -> COMPLY
        (the guard's precondition matched again, this time cleanly — the
        strongest evidence this log format can produce that the agent
        adjusted the command and it went through).
      - next row is a different fire (different fp, not exposure-clean), or
        no matching-token row exists at all -> ABANDONED, IF this guard has
        emitted at least one exposure-clean row somewhere in the loaded
        window (i.e. it is CAPABLE of producing comply evidence and didn't
        here); otherwise -> UNKNOWN, because for a guard with zero exposure
        instrumentation, comply and abandoned are OBSERVATIONALLY IDENTICAL
        from this log alone (both look like silence) and guessing between
        them would be exactly the kind of unearned confidence T2 was asked
        not to produce.
      - a row with no cmd_tok at all (pre-enrichment, or not command-shaped)
        -> UNKNOWN, always, no adjacency logic attempted.

    HONEST LIMITS (repeated in outcome_report()'s printed header — read
    before trusting a number here):
      - Inferred from log ADJACENCY, never from a tool's actual exit code or
        stdout. A same-session retry hours later still counts as a pair;
        there is no wall-clock cap.
      - "Exposure-instrumented" is evaluated per (guard, LOADED WINDOW) — a
        guard capable of exposure logging that simply had no eligible-clean
        call in a short --days window will under-report as UNKNOWN for that
        window, not because the log format can't tell but because this
        particular slice of it didn't happen to contain one.
    """
    instrumented = {t["hook"] for t in triggers if t.get("action") == EXPOSURE_ACTION and t.get("hook")}

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in triggers:
        h = t.get("hook")
        if not h:
            continue
        groups[(_session_key(t), h)].append(t)
    for rows in groups.values():
        rows.sort(key=lambda r: r.get("ts", ""))

    per_guard: dict[str, dict] = defaultdict(lambda: {
        "fires": 0, "comply": 0, "repeated_attempt": 0, "abandoned": 0, "unknown": 0,
        "exposures": 0, "dominant_action": Counter(),
    })

    for (_session, hook), rows in groups.items():
        g = per_guard[hook]
        for i, row in enumerate(rows):
            action = row.get("action", "")
            if action == EXPOSURE_ACTION:
                g["exposures"] += 1
                continue
            tok = row.get("cmd_tok", "")
            fp = row.get("cmd_fp", "")
            g["fires"] += 1
            if action:
                g["dominant_action"][action] += 1
            if not tok:
                g["unknown"] += 1
                continue
            nxt = next((later for later in rows[i + 1:] if later.get("cmd_tok") == tok), None)
            if nxt is None:
                g["abandoned" if hook in instrumented else "unknown"] += 1
            elif nxt.get("cmd_fp") == fp:
                g["repeated_attempt"] += 1
            elif nxt.get("action") == EXPOSURE_ACTION:
                g["comply"] += 1
            else:
                g["abandoned" if hook in instrumented else "unknown"] += 1

    return dict(per_guard)


def _outcome_label(dominant: Counter) -> str:
    """A guard's REPEATED-ATTEMPT bucket is the same underlying signal
    (identical command fingerprint re-firing) for both block- and warn-type
    guards, but it means something different in each: for an advisory guard
    it reads as the agent OVERRIDING the guidance (nothing stopped it from
    proceeding); for a hard block it reads as FRICTION (the command never
    went through either time). Labeled by the guard's dominant fire action,
    not per-row, since a single guard is overwhelmingly one type or the
    other in practice."""
    if not dominant:
        return "override"
    top_action = dominant.most_common(1)[0][0]
    return "friction" if top_action == "block" else "override"


def outcome_report(triggers: list[dict], days: int = 7) -> None:
    cutoff = datetime.now() - timedelta(days=days)
    recent = [t for t in triggers if parse_ts(t.get("ts", "")) > cutoff]
    if not recent:
        print(f"No hook triggers in the last {days} days.")
        return

    per_guard = classify_outcomes(recent)
    fire_guards = {h: g for h, g in per_guard.items() if g["fires"] > 0}
    if not fire_guards:
        print("No command-shaped (cmd_tok-enriched) guard fires in this window — "
              "nothing to classify. Enrichment landed 2026-07-18; rows logged before "
              "that carry no cmd_tok/cmd_fp and are never retroactively fingerprinted.")
        return

    instrumented = sorted({h for h, g in per_guard.items() if g["exposures"] > 0})

    print(f"{'=' * 72}")
    print(f"  Hook OUTCOME Analysis (comply / override-or-friction / abandoned) — last {days} days")
    print(f"{'=' * 72}")
    print()
    print("  METHOD / LIMITS — read before trusting a number here:")
    print("  - Inferred from LOG ADJACENCY (what fired next for the same guard + command")
    print("    first-token, in the same session), never from a tool's actual exit code or")
    print("    stdout. This is a heuristic, not ground truth.")
    print("  - COMPLY requires an exposure-clean row for the SAME guard, with a DIFFERENT")
    print("    fingerprint, later in the same session. Only guards that emit exposure-clean")
    print("    rows can ever show COMPLY or ABANDONED as distinct outcomes — every other")
    print("    guard reports 'unknown' for both, because silence alone cannot tell comply")
    print("    (the agent fixed it and nothing fired) apart from abandoned (the agent")
    print("    dropped it) from this log format.")
    print(f"  - Exposure-instrumented guards in this window: {', '.join(instrumented) if instrumented else '(none)'}")
    print("  - REPEATED-ATTEMPT (same fingerprint re-firing) needs no exposure")
    print("    instrumentation — measurable for every guard. It counts adjacent-pair")
    print("    TRANSITIONS: N identical-fp fires in a row yield N-1 repeated-attempt")
    print("    counts, not N.")
    print("  - Session-scoped only; no wall-clock cap between the paired events (a retry")
    print("    hours later in the same session still counts as a pair).")
    print("  - Rows with no cmd_tok (pre-2026-07-18, or not command-shaped) are always")
    print("    'unknown' here, never guessed.")
    print()

    header = f"  {'guard':<28} {'fires':>6} {'comply':>7} {'ovr/fric':>9} {'abandon':>8} {'unknown':>8}  flag"
    print(header)
    for hook in sorted(fire_guards, key=lambda h: -fire_guards[h]["fires"]):
        g = fire_guards[hook]
        n = g["fires"]
        classified = g["comply"] + g["repeated_attempt"] + g["abandoned"]
        label = _outcome_label(g["dominant_action"])
        flag = ""
        if classified >= 10 and g["repeated_attempt"] / classified > 0.5:
            flag = f"** >50% {label} over {classified} classified — O2 retune candidate"
        print(f"  {hook:<28} {n:>6} {g['comply']:>7} {g['repeated_attempt']:>9} {g['abandoned']:>8} {g['unknown']:>8}  {flag}")
    print()
    print("  ovr/fric = repeated-attempt count, labeled 'override' for advisory-dominant")
    print("  guards and 'friction' for block-dominant guards (see _outcome_label). The O2")
    print("  flag denominator is CLASSIFIED outcomes (comply+repeated+abandoned), excluding")
    print("  unknown — an unclassified row carries no signal either way.")
    print()


def transfer_report(triggers: list[dict], days: int, since: str | None = None) -> None:
    """Cross-project transfer effectiveness: per-hook × per-project breakdown.

    Shows which hooks deployed globally are effective across projects.
    Flags low-volume projects (<20 sessions) as underpowered.
    """
    cutoff_dt = datetime.now() - timedelta(days=days)
    if since:
        cutoff_dt = max(cutoff_dt, datetime.strptime(since, "%Y-%m-%d"))
    cutoff = cutoff_dt.isoformat()
    recent = [t for t in triggers if t.get("ts", "") >= cutoff]

    if not recent:
        print("No triggers in the transfer window.")
        return

    # hook × project matrix
    matrix: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    project_session_counts: dict[str, set] = defaultdict(set)

    for t in recent:
        hook = t.get("hook", "?")
        proj = t.get("project", "?")
        action = t.get("action", "?")
        session = t.get("session_id", t.get("ts", "")[:16])
        matrix[hook][proj][action] += 1
        matrix[hook][proj]["total"] += 1
        project_session_counts[proj].add(session)

    min_sessions = 20
    print(f"{'=' * 60}")
    print(f"  Hook Transfer Report — since {cutoff[:10]}")
    print(f"{'=' * 60}")
    print()

    for hook in sorted(matrix.keys()):
        projects = matrix[hook]
        total = sum(p["total"] for p in projects.values())
        if total < 3:
            continue
        print(f"  {hook} ({total} total):")
        for proj in sorted(projects.keys()):
            counts = projects[proj]
            n_sessions = len(project_session_counts.get(proj, set()))
            underpowered = " [UNDERPOWERED]" if n_sessions < min_sessions else ""
            blocks = counts.get("block", 0)
            warns = counts.get("warn", 0)
            t = counts["total"]
            block_rate = blocks / t if t else 0
            print(f"    {proj:<20} {t:>3} triggers ({blocks} block, {warns} warn, "
                  f"block_rate={block_rate:.0%}){underpowered}")
        print()

    print("  Project session counts (for denominator check):")
    for proj, sessions in sorted(project_session_counts.items(),
                                  key=lambda x: -len(x[1])):
        n = len(sessions)
        flag = " < min" if n < min_sessions else ""
        print(f"    {proj:<20} {n:>3} sessions{flag}")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hook ROI telemetry")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--transfer", action="store_true",
                        help="Show per-hook × per-project transfer report")
    parser.add_argument("--since", type=str,
                        help="Filter triggers since YYYY-MM-DD (with --transfer)")
    parser.add_argument("--outcomes", action="store_true",
                        help="Per-guard comply/override(-or-friction)/abandoned outcome "
                             "classification over cmd_tok/cmd_fp-enriched rows (T2, "
                             "guard-forcerate-study). See outcome_report()'s printed "
                             "header for method + honest limits.")
    args = parser.parse_args()

    triggers = load_triggers(TRIGGERS_FILE)
    if args.transfer:
        transfer_report(triggers, args.days, args.since)
    elif args.outcomes:
        outcome_report(triggers, args.days)
    else:
        main(args.days, args.verbose)
