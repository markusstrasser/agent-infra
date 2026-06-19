#!/usr/bin/env python3
# Gov-ID: tool:supervision-kpi
# goal: measure supervision load as a DIRECTION VECTOR (not a scalar that sums
#       opposite-sign corrections), so the autonomy objective is readable.
# verifier: scripts/tests/test_supervision_taxonomy.py
# blast_radius: local
"""Supervision KPI — measure human supervision load per session, by DIRECTION.

Constitutional objective: "maximize the rate agents become more autonomous, measured by
declining supervision." The first version of this script minimized a weighted SCALAR
(`sli = corrections + 2*denials + 3*repeated + 5*blindspot`). That conflated opposite-sign
signals — being WRONG (→ add a guardrail) and being TIMID (→ loosen) pushed the same number
the same way — and was BLIND to over-caution entirely ("why ask" / "why not build it now"
matched no pattern → scored zero). See `supervision_taxonomy.py` for the full argument.

This version classifies every correction via the single-source taxonomy (the regex TREND tier;
the emb QUALITY tier lives in blindspot_miner.py) and reports a per-DIRECTION vector:

    REDUCE_ERROR   — agent was wrong          (↓ = fewer mistakes)
    RAISE_AUTONOMY — agent was timid          (↓ = acting more freely — the pure autonomy signal)
    GROW_COVERAGE  — agent missed context     (↓ = better recall)
    AMPLIFY_TASTE  — agent missed taste        (a production-burden signal, not a defect)

The autonomy reading is a CONJUNCTION a scalar can't express:
    genuine gain == RAISE_AUTONOMY ↓  AND  (REDUCE_ERROR + GROW_COVERAGE) not rising.

Usage:
    supervision-kpi.py --today
    supervision-kpi.py --days 30 [--project intel] [--output artifacts/supervision-kpi.jsonl]
    supervision-kpi.py --days 30 --compare 2026-05-15
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from common.paths import PROJECTS_DIR
from config import extract_project_name

import supervision_taxonomy as tax

AGENTLOGS_DB = Path.home() / ".claude" / "agentlogs.db"
_BYPASS_MODES = frozenset({"bypassPermissions", "dontAsk", "never", "auto"})

# Patterns for system-injected user messages to skip (parsing concern, not taxonomy).
SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>", re.IGNORECASE)
SYSTEM_INJECTED_RE = re.compile(
    r"^(?:<task-notification>|<command-message>|<command-name>"
    r"|Base directory for this skill:"
    r"|Stop hook feedback:"
    r"|Uncommitted changes:"
    r"|You MUST call)",
)


# ---------------------------------------------------------------------------
# JSONL Parsing — single pass per session
# ---------------------------------------------------------------------------


def extract_supervision(path: Path) -> dict:
    """Extract typed supervision metrics from a session JSONL file.

    Text corrections are classified by the taxonomy's regex tier (deterministic, $0).
    `denial` and `repeated_instruction` are structural (tool results / similarity) and mapped
    to their taxonomy direction. The result carries per-type counts AND the direction vector.
    """
    session_id = None
    project = extract_project_name(path.parent.name)

    by_type: dict[str, int] = {t.id: 0 for t in tax.TAXONOMY}
    user_messages: list[str] = []

    turn_index = 0
    hook_turn_indices: list[int] = []
    correction_turn_indices: list[int] = []
    first_timestamp = None

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not session_id:
                session_id = obj.get("sessionId")
            ts = obj.get("timestamp")
            if ts and first_timestamp is None:
                first_timestamp = ts

            msg_type = obj.get("type")

            if msg_type == "user" and not obj.get("toolUseResult"):
                text = _extract_user_text(obj)
                if not text:
                    continue
                turn_index += 1
                # Single-source classification: one primary type per message (priority-ordered).
                m = tax.classify_regex(text)
                if m is not None:
                    by_type[m.type_id] += 1
                    correction_turn_indices.append(turn_index)
                user_messages.append(text)

            elif msg_type == "user" and obj.get("toolUseResult"):
                if _is_denial(obj["toolUseResult"]):
                    by_type["denial"] += 1
                    correction_turn_indices.append(turn_index)

            elif msg_type == "progress":
                data = obj.get("data", {})
                if data.get("type") == "hook_progress" and data.get("hookEvent") == "Stop":
                    hook_turn_indices.append(turn_index)

            elif msg_type == "attachment":
                # Real hook-fire signal. The hook_progress/Stop form above is near-absent in
                # practice (7 occurrences vs >3600 hook_success across transcripts), so it left
                # hooks_shown dead at 0 and air=null on 1591 sessions — the closure metric was
                # querying a field Claude Code does not write. A hook counts as "shown" only when
                # it surfaced content the agent could see (stdout/stderr/additional-context),
                # not routine silent logging hooks.
                att = obj.get("attachment") or {}
                if att.get("type") == "hook_success" and (
                    att.get("stdout") or att.get("stderr")
                    or att.get("hookAdditionalContext") or att.get("hook_additional_context")
                ):
                    hook_turn_indices.append(turn_index)

    by_type["repeated_instruction"] = _count_repeated_instructions(user_messages)

    # Per-turn, not per-fire: a turn with 5 PostToolUse hooks is one "hook shown" for AIR.
    hook_turn_indices = sorted(set(hook_turn_indices))

    # Direction vector — the objective's shape.
    vector = tax.empty_vector()
    for type_id, n in by_type.items():
        tax.add_to_vector(vector, type_id, n)

    corrections_after_hooks = _count_corrections_after_hooks(
        hook_turn_indices, correction_turn_indices, window=3
    )
    air = round(corrections_after_hooks / len(hook_turn_indices), 3) if hook_turn_indices else None

    return {
        "session_id": session_id or path.stem,
        "project": project,
        "date": first_timestamp[:10] if first_timestamp else None,
        "by_type": by_type,
        "vector": vector,
        "load": tax.gross_load(by_type, by_type=True),  # coarse weighted total — NOT the objective
        "hooks_shown": len(hook_turn_indices),
        "corrections_after_hooks": corrections_after_hooks,
        "air": air,
    }


def _extract_user_text(obj: dict) -> str | None:
    content = obj.get("message", {}).get("content", "")
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    if not text:
        return None
    text = text.strip()
    if SYSTEM_REMINDER_RE.search(text[:100]) or SYSTEM_INJECTED_RE.match(text):
        return None
    return text


def _is_denial(result) -> bool:
    if isinstance(result, str):
        return "denied" in result.lower()[:500]
    if not isinstance(result, dict):
        return False
    result_str = ""
    content = result.get("content", "")
    if isinstance(content, str):
        result_str = content
    elif isinstance(content, list):
        for block in content[:3]:
            if isinstance(block, dict):
                result_str += block.get("text", "") + " "
    result_str += " " + str(result.get("stdout", ""))
    low = result_str.lower()[:500]
    return "denied" in low or "permission denied" in low


def _count_repeated_instructions(messages: list[str], window: int = 5) -> int:
    """Count user messages that repeat similar content within a sliding window (Jaccard 0.4–0.95)."""
    if len(messages) < 2:
        return 0
    count = 0
    normalized = [set(re.findall(r"\w+", m.lower())) for m in messages]
    for i in range(1, len(normalized)):
        for j in range(max(0, i - window), i):
            if not normalized[i] or not normalized[j]:
                continue
            sim = len(normalized[i] & normalized[j]) / len(normalized[i] | normalized[j])
            if 0.4 < sim < 0.95:
                count += 1
                break
    return count


def _count_corrections_after_hooks(hook_turns: list[int], correction_turns: list[int], window: int = 3) -> int:
    if not hook_turns or not correction_turns:
        return 0
    count = 0
    correction_set = set(correction_turns)
    for ht in hook_turns:
        if any(ht + off in correction_set for off in range(1, window + 1)):
            count += 1
    return count


def query_approval_mode_stats(days: int = 21) -> dict | None:
    """agentlogs runs.approval_mode distribution — Eve needsApproval ground-truth proxy."""
    if not AGENTLOGS_DB.is_file():
        return None
    try:
        from common.db import open_db_ro
        with open_db_ro(AGENTLOGS_DB) as con:
            dist = {
                row[0]: row[1] for row in con.execute(
                    "SELECT COALESCE(approval_mode, '(null)') AS mode, COUNT(*) "
                    "FROM runs WHERE started_at > datetime('now', ?) GROUP BY mode",
                    (f"-{days} days",),
                )
            }
            recent = {
                row[0]: row[1] for row in con.execute(
                    "SELECT COALESCE(approval_mode, '(null)'), COUNT(*) FROM runs "
                    "WHERE started_at > datetime('now', '-7 days') GROUP BY 1"
                )
            }
            prior = {
                row[0]: row[1] for row in con.execute(
                    "SELECT COALESCE(approval_mode, '(null)'), COUNT(*) FROM runs "
                    "WHERE started_at BETWEEN datetime('now', '-14 days') "
                    "AND datetime('now', '-7 days') GROUP BY 1"
                )
            }
    except Exception:
        return None
    if not dist:
        return None

    def bypass_share(d: dict[str, int]) -> float:
        total = sum(d.values()) or 1
        bypass = sum(n for m, n in d.items() if m in _BYPASS_MODES)
        return bypass / total

    return {
        "days": days,
        "distribution": dist,
        "bypass_share_recent_7d": round(bypass_share(recent), 3),
        "bypass_share_prior_7d": round(bypass_share(prior), 3),
        "total_runs": sum(dist.values()),
    }


def _print_approval_mode_stats(window_days: int, results: list[dict]) -> None:
    if window_days < 7:
        return
    stats = query_approval_mode_stats(window_days)
    if not stats:
        return
    dist = stats["distribution"]
    top = sorted(dist.items(), key=lambda x: -x[1])[:5]
    parts = ", ".join(f"{m}={n}" for m, n in top)
    print(f"APPROVAL_MODES ({stats['total_runs']} runs, {window_days}d): {parts}", file=sys.stderr)
    br, bp = stats["bypass_share_recent_7d"], stats["bypass_share_prior_7d"]
    if br != bp:
        print(f"  bypass-mode share: {bp:.1%} → {br:.1%} (7d prior → recent)", file=sys.stderr)
    air_sessions = [r for r in results if r.get("air") is not None]
    if air_sessions and br > bp + 0.05:
        total_hooks = sum(r["hooks_shown"] for r in air_sessions)
        total_after = sum(r["corrections_after_hooks"] for r in air_sessions)
        air = total_after / total_hooks if total_hooks else 0
        if air > 0.05:
            print(
                "  ⚠ PROBLEM-HIDING? bypass-mode share rose while AIR elevated "
                f"({air:.3f}) — supervision may be dropping via mode, not hooks",
                file=sys.stderr,
            )


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------


def find_sessions_by_date(since: datetime, until: datetime | None = None) -> list[Path]:
    sessions = []
    since_ts = since.timestamp()
    until_ts = until.timestamp() if until else datetime.now().timestamp() + 86400
    for proj_dir in sorted(PROJECTS_DIR.iterdir()):
        if not proj_dir.is_dir():
            continue
        for jsonl in proj_dir.glob("*.jsonl"):
            if since_ts <= jsonl.stat().st_mtime <= until_ts:
                sessions.append(jsonl)
    return sorted(sessions, key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# Trend — per-direction slope (the objective is a vector, so is its trend)
# ---------------------------------------------------------------------------


def _slope(ys: list[float]) -> float:
    n = len(ys)
    xs = list(range(n))
    xm, ym = sum(xs) / n, sum(ys) / n
    denom = sum((x - xm) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denom


def compute_direction_trends(results: list[dict], window: int = 30) -> dict | None:
    """Per-direction slope over recent sessions. Negative slope = that direction's
    correction rate is falling. Returns None if too few sessions for a meaningful trend."""
    recent = sorted(results, key=lambda r: r.get("date") or "")[-window:]
    if len(recent) < 5:
        return None
    trends = {}
    for d in tax.Direction:
        ys = [r["vector"].get(d.value, 0) for r in recent]
        trends[d.value] = round(-_slope(ys), 4)  # positive = improving (rate declining)
    trends["load"] = round(-_slope([r["load"] for r in recent]), 4)
    return trends


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Supervision KPI — measure human supervision load per session, by direction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true", help="Process today's sessions")
    group.add_argument("--days", type=int, help="Process sessions from last N days")
    group.add_argument("--since", type=str, help="Process sessions since YYYY-MM-DD")
    parser.add_argument("--project", "-p", help="Filter by project name")
    parser.add_argument("--output", "-o", help="Write JSONL output to this file")
    parser.add_argument("--compare", type=str, metavar="YYYY-MM-DD",
                        help="Compare current window against the same-length period ending at this date")
    args = parser.parse_args()

    if args.today:
        since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        window_days = 1
    elif args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d")
        window_days = (datetime.now() - since).days
    else:
        since = datetime.now() - timedelta(days=args.days)
        window_days = args.days

    sessions = find_sessions_by_date(since)
    if args.project:
        sessions = [s for s in sessions if extract_project_name(s.parent.name) == args.project]
    if not sessions:
        print("No sessions found.", file=sys.stderr)
        sys.exit(0)

    results = []
    for path in sessions:
        try:
            results.append(extract_supervision(path))
        except Exception as e:
            print(f"WARN: failed to process {path.name}: {e}", file=sys.stderr)
    if not results:
        print("No sessions processed successfully.", file=sys.stderr)
        sys.exit(0)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        print(f"Wrote {len(results)} sessions to {output_path}", file=sys.stderr)
    else:
        for r in results:
            print(json.dumps(r))

    _print_summary(results, args)

    if args.compare:
        _print_comparison(results, args, window_days)


def _agg_vector(results: list[dict]) -> dict[str, int]:
    agg = tax.empty_vector()
    for r in results:
        for k, v in r["vector"].items():
            agg[k] = agg.get(k, 0) + v
    return agg


def _print_summary(results: list[dict], args) -> None:
    n = len(results)
    loads = sorted(r["load"] for r in results)
    mean_load = sum(loads) / n
    median_load = loads[n // 2] if n % 2 else (loads[n // 2 - 1] + loads[n // 2]) / 2
    days_label = "today" if getattr(args, "today", False) else f"{args.days}-day" if getattr(args, "days", None) else "since"

    print(file=sys.stderr)
    print(f"{days_label} summary: {n} sessions, mean load: {mean_load:.1f}, median load: {median_load:.1f}", file=sys.stderr)

    # The direction vector — the headline. Each direction names a DIFFERENT response.
    agg = _agg_vector(results)
    print("SUPERVISION VECTOR (corrections by direction):", file=sys.stderr)
    for d in tax.Direction:
        label = {
            "raise_autonomy": "was TIMID → loosen/act more  [the pure autonomy signal]",
            "reduce_error": "was WRONG → correctness guardrail",
            "grow_coverage": "missed CONTEXT → add detector",
            "amplify_taste": "missed TASTE → options, keep human judge",
        }[d.value]
        print(f"  {d.value:14s} {agg[d.value]:4d}  — {label}", file=sys.stderr)

    # Over-caution is the autonomy signal the old scalar was blind to — name the sessions.
    oc = sum(r["by_type"].get("over_caution", 0) for r in results)
    if oc:
        flagged = sorted((r for r in results if r["by_type"].get("over_caution", 0)),
                         key=lambda r: -r["by_type"]["over_caution"])[:6]
        names = ", ".join(f"{r['project']}/{r['session_id'][:8]}({r['by_type']['over_caution']})" for r in flagged)
        print(f"OVER-CAUTION: {oc} — the agent asked/deferred on reversible work. "
              f"Declining this = autonomy gain. [{names}]", file=sys.stderr)

    trends = compute_direction_trends(results)
    if trends:
        print(f"TRENDS (per-direction, + = rate declining/improving): "
              f"autonomy {trends['raise_autonomy']:+.3f}, error {trends['reduce_error']:+.3f}, "
              f"coverage {trends['grow_coverage']:+.3f}, load {trends['load']:+.3f}", file=sys.stderr)
        # The honest conjunction the scalar could never express.
        gain = trends["raise_autonomy"] > 0 and (trends["reduce_error"] >= 0 and trends["grow_coverage"] >= 0)
        verdict = ("genuine autonomy gain (timidity ↓, errors/misses not rising)" if gain
                   else "MIXED — read the vector; a falling load may hide rising errors or rising timidity")
        print(f"AUTONOMY READING: {verdict}", file=sys.stderr)
    else:
        print("TRENDS: insufficient data (need 5+ sessions)", file=sys.stderr)

    from collections import defaultdict
    by_project: dict[str, list[float]] = defaultdict(list)
    for r in results:
        by_project[r["project"]].append(r["load"])
    if len(by_project) > 1:
        parts = [f"{p}={sum(v) / len(v):.1f}" for p, v in sorted(by_project.items())]
        print(f"By project (mean load): {', '.join(parts)}", file=sys.stderr)

    air_sessions = [r for r in results if r["air"] is not None]
    if air_sessions:
        total_hooks = sum(r["hooks_shown"] for r in air_sessions)
        total_after = sum(r["corrections_after_hooks"] for r in air_sessions)
        overall_air = total_after / total_hooks if total_hooks else 0
        print(f"AIR: {overall_air:.3f} ({total_after}/{total_hooks} corrections after hooks, lower = better)", file=sys.stderr)

    _print_approval_mode_stats(
        21 if getattr(args, "today", False) else (getattr(args, "days", None) or 30),
        results,
    )


def _print_comparison(results: list[dict], args, window_days: int) -> None:
    compare_end = datetime.strptime(args.compare, "%Y-%m-%d")
    compare_start = compare_end - timedelta(days=window_days)
    compare_sessions = [s for s in find_sessions_by_date(compare_start) if s.stat().st_mtime < compare_end.timestamp()]
    if args.project:
        compare_sessions = [s for s in compare_sessions if extract_project_name(s.parent.name) == args.project]
    prev = []
    for path in compare_sessions:
        try:
            prev.append(extract_supervision(path))
        except Exception:
            pass
    if not prev:
        print(f"No comparison sessions found for period ending {args.compare}", file=sys.stderr)
        return
    curr_v, prev_v = _agg_vector(results), _agg_vector(prev)
    print(file=sys.stderr)
    print(f"=== COMPARISON vs {args.compare} (per-direction, per-session mean) ===", file=sys.stderr)
    for d in tax.Direction:
        c = curr_v[d.value] / len(results)
        p = prev_v[d.value] / len(prev)
        delta = c - p
        print(f"  {d.value:14s} {p:.2f} → {c:.2f}  ({delta:+.2f})", file=sys.stderr)
    if len(prev) < 20 or len(results) < 20:
        print("  WARNING: <20 sessions in one period — estimate underpowered", file=sys.stderr)


if __name__ == "__main__":
    main()
