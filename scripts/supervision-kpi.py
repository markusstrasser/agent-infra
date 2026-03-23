#!/usr/bin/env python3
"""Supervision KPI — measure human supervision load per agent session.

Constitutional gap: "maximize rate agents become more autonomous, measured by
declining supervision" but zero supervision metrics existed. This script fills
that gap with three KPIs extracted from JSONL session transcripts.

KPIs:
  SLI  — Supervision Load Index (composite per-session score)
  AIR  — Alert Intervention Rate (corrections after hook warnings)
  AGR  — Autonomy Gain Rate (SLI trend over rolling window)

Usage:
    supervision-kpi.py --today
    supervision-kpi.py --days 30
    supervision-kpi.py --days 30 --project intel
    supervision-kpi.py --days 30 --output artifacts/supervision-kpi.jsonl
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from config import extract_project_name

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

from common.paths import PROJECTS_DIR

# Correction keywords — checked at START of user message (first 80 chars, lowered)
# Anchored to message start to avoid false positives from long messages about
# unrelated topics that happen to contain "no" somewhere.
CORRECTION_PATTERNS = re.compile(
    r"^(?:#f\s+)?"  # optional #f feedback prefix
    r"(?:no[,.\s]|not that|instead[,.\s]|wrong|don'?t\s|stop[,.\s]|undo|revert)",
    re.IGNORECASE,
)

# Patterns for system-injected user messages to skip
SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>", re.IGNORECASE)
# Task notifications (subagent results), command messages (skill loads),
# skill base directory injections — all system-generated, not human input
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
    """Extract supervision metrics from a session JSONL file."""
    session_id = None
    project_dir = path.parent.name
    project = extract_project_name(project_dir)

    # Accumulators
    corrections = 0
    denials = 0
    hooks_shown = 0
    corrections_after_hooks = 0

    # For repeated instruction detection
    user_messages: list[str] = []  # recent user message texts

    # For AIR: track turn indices
    turn_index = 0
    hook_turn_indices: list[int] = []  # turns where hooks fired
    correction_turn_indices: list[int] = []  # turns where corrections happened

    # For date extraction
    first_timestamp = None
    last_timestamp = None

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
            if ts:
                if first_timestamp is None:
                    first_timestamp = ts
                last_timestamp = ts

            msg_type = obj.get("type")

            # --- User messages (not tool results) ---
            if msg_type == "user" and not obj.get("toolUseResult"):
                text = _extract_user_text(obj)
                if not text:
                    continue

                turn_index += 1

                # Check for correction
                # Only check first 80 chars to anchor at message start
                check_text = text[:80]
                if CORRECTION_PATTERNS.search(check_text):
                    corrections += 1
                    correction_turn_indices.append(turn_index)

                # Store for repeated instruction detection
                user_messages.append(text)

            # --- Tool results: check for denials ---
            elif msg_type == "user" and obj.get("toolUseResult"):
                result = obj["toolUseResult"]
                if _is_denial(result):
                    denials += 1
                    correction_turn_indices.append(turn_index)

            # --- Hook progress events ---
            elif msg_type == "progress":
                data = obj.get("data", {})
                if data.get("type") == "hook_progress":
                    hook_event = data.get("hookEvent", "")
                    # Only count Stop hooks as "shown to agent" — these inject
                    # advisory messages into the conversation. PreToolUse/
                    # PostToolUse hooks run transparently on every tool call
                    # and can't be distinguished from silent runs in JSONL.
                    if hook_event == "Stop":
                        hooks_shown += 1
                        hook_turn_indices.append(turn_index)

    # --- Compute repeated instructions ---
    repeated_instructions = _count_repeated_instructions(user_messages)

    # --- Compute AIR: corrections within 3 turns after hook ---
    corrections_after_hooks = _count_corrections_after_hooks(
        hook_turn_indices, correction_turn_indices, window=3
    )

    # --- Compute SLI ---
    sli = corrections + 2 * denials + 3 * repeated_instructions

    # --- AIR ---
    air = (
        round(corrections_after_hooks / hooks_shown, 3) if hooks_shown > 0 else None
    )

    # Date from first timestamp
    date = first_timestamp[:10] if first_timestamp else None

    return {
        "session_id": session_id or path.stem,
        "project": project,
        "date": date,
        "sli": sli,
        "corrections": corrections,
        "denials": denials,
        "repeated_instructions": repeated_instructions,
        "hooks_shown": hooks_shown,
        "corrections_after_hooks": corrections_after_hooks,
        "air": air,
    }


def _extract_user_text(obj: dict) -> str | None:
    """Extract text from a user message record, skipping system reminders."""
    content = obj.get("message", {}).get("content", "")
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        text = "\n".join(parts)

    if not text:
        return None

    text = text.strip()

    # Skip system-injected messages (not real human input)
    if SYSTEM_REMINDER_RE.search(text[:100]):
        return None
    if SYSTEM_INJECTED_RE.match(text):
        return None

    return text


def _is_denial(result) -> bool:
    """Check if a tool result represents a permission denial."""
    # toolUseResult can be a dict, string, or other types
    if isinstance(result, str):
        return "denied" in result.lower()[:500]

    if not isinstance(result, dict):
        return False

    result_str = ""

    # Content field (can be string or list)
    content = result.get("content", "")
    if isinstance(content, str):
        result_str = content
    elif isinstance(content, list):
        for block in content[:3]:
            if isinstance(block, dict):
                result_str += block.get("text", "") + " "

    # Also check stdout
    result_str += " " + str(result.get("stdout", ""))

    result_lower = result_str.lower()[:500]
    return "denied" in result_lower or "permission denied" in result_lower


def _count_repeated_instructions(messages: list[str], window: int = 5) -> int:
    """Count user messages that repeat similar content within a sliding window.

    Uses Jaccard similarity on word tokens. A message is "repeated" if it's
    similar (0.4 < sim < 0.95) to a message within the last `window` turns.
    """
    if len(messages) < 2:
        return 0

    count = 0
    normalized = [set(re.findall(r"\w+", m.lower())) for m in messages]

    for i in range(1, len(normalized)):
        for j in range(max(0, i - window), i):
            if not normalized[i] or not normalized[j]:
                continue
            sim = len(normalized[i] & normalized[j]) / len(
                normalized[i] | normalized[j]
            )
            if 0.4 < sim < 0.95:
                count += 1
                break  # count each message as repeated at most once

    return count


def _count_corrections_after_hooks(
    hook_turns: list[int], correction_turns: list[int], window: int = 3
) -> int:
    """Count corrections that occur within `window` turns after a hook event."""
    if not hook_turns or not correction_turns:
        return 0

    count = 0
    correction_set = set(correction_turns)
    for ht in hook_turns:
        for offset in range(1, window + 1):
            if ht + offset in correction_set:
                count += 1
                break  # count each hook as triggering at most one correction

    return count


# ---------------------------------------------------------------------------
# Session discovery (reused from session-features.py)
# ---------------------------------------------------------------------------


def find_sessions_by_date(
    since: datetime, until: datetime | None = None
) -> list[Path]:
    """Find session JSONL files modified within a date range."""
    sessions = []
    since_ts = since.timestamp()
    until_ts = until.timestamp() if until else datetime.now().timestamp() + 86400

    for proj_dir in sorted(PROJECTS_DIR.iterdir()):
        if not proj_dir.is_dir():
            continue
        for jsonl in proj_dir.glob("*.jsonl"):
            mtime = jsonl.stat().st_mtime
            if since_ts <= mtime <= until_ts:
                sessions.append(jsonl)

    return sorted(sessions, key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# AGR (Autonomy Gain Rate) — linear regression on SLI over sessions
# ---------------------------------------------------------------------------


def compute_agr(results: list[dict], window: int = 30) -> float | None:
    """Compute Autonomy Gain Rate as negative slope of SLI over recent sessions.

    Positive AGR = autonomy improving (SLI declining).
    Uses simple OLS on session index vs SLI.
    """
    # Take last `window` sessions, sorted by date
    recent = sorted(results, key=lambda r: r.get("date") or "")[-window:]
    if len(recent) < 5:
        return None  # not enough data for meaningful trend

    n = len(recent)
    xs = list(range(n))
    ys = [r["sli"] for r in recent]

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    denominator = sum((x - x_mean) ** 2 for x in xs)

    if denominator == 0:
        return 0.0

    slope = numerator / denominator
    return round(-slope, 4)  # negative slope = positive AGR (improving)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Supervision KPI — measure human supervision load per session",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  supervision-kpi.py --today
  supervision-kpi.py --days 30
  supervision-kpi.py --days 30 --project intel
  supervision-kpi.py --days 30 --output artifacts/supervision-kpi.jsonl
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true", help="Process today's sessions")
    group.add_argument("--days", type=int, help="Process sessions from last N days")
    group.add_argument("--since", type=str, help="Process sessions since YYYY-MM-DD")

    parser.add_argument("--project", "-p", help="Filter by project name")
    parser.add_argument("--output", "-o", help="Write JSONL output to this file")
    parser.add_argument("--compare", type=str, metavar="YYYY-MM-DD",
                        help="Compare current window against period ending at this date (same window length)")

    args = parser.parse_args()

    # Resolve sessions
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

    # Filter by project
    if args.project:
        sessions = [
            s
            for s in sessions
            if extract_project_name(s.parent.name) == args.project
        ]

    if not sessions:
        print("No sessions found.", file=sys.stderr)
        sys.exit(0)

    # Process
    results = []
    for path in sessions:
        try:
            metrics = extract_supervision(path)
            results.append(metrics)
        except Exception as e:
            print(f"WARN: failed to process {path.name}: {e}", file=sys.stderr)

    if not results:
        print("No sessions processed successfully.", file=sys.stderr)
        sys.exit(0)

    # Output JSONL
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

    # Summary to stderr
    _print_summary(results, args)

    # Comparison mode: measure delta against a prior period
    if args.compare:
        compare_end = datetime.strptime(args.compare, "%Y-%m-%d")
        compare_start = compare_end - timedelta(days=window_days)
        compare_sessions = find_sessions_by_date(compare_start)
        # Filter to only sessions before compare_end
        compare_sessions = [s for s in compare_sessions
                           if s.stat().st_mtime < compare_end.timestamp()]
        if args.project:
            compare_sessions = [s for s in compare_sessions
                               if extract_project_name(s.parent.name) == args.project]
        compare_results = []
        for path in compare_sessions:
            try:
                compare_results.append(extract_supervision(path))
            except Exception:
                pass
        if compare_results:
            curr_slis = [r["sli"] for r in results]
            prev_slis = [r["sli"] for r in compare_results]
            curr_mean = sum(curr_slis) / len(curr_slis)
            prev_mean = sum(prev_slis) / len(prev_slis)
            delta = curr_mean - prev_mean
            print(file=sys.stderr)
            print(f"=== COMPARISON vs {args.compare} ===", file=sys.stderr)
            print(f"  Prior period: {len(compare_results)} sessions, mean SLI: {prev_mean:.1f}", file=sys.stderr)
            print(f"  Current:      {len(results)} sessions, mean SLI: {curr_mean:.1f}", file=sys.stderr)
            print(f"  Delta:        {delta:+.1f} SLI ({'improving' if delta < 0 else 'worsening'})", file=sys.stderr)
            min_sessions = 20
            if len(compare_results) < min_sessions or len(results) < min_sessions:
                print(f"  WARNING: <{min_sessions} sessions in one period — estimate underpowered", file=sys.stderr)
        else:
            print(f"No comparison sessions found for period ending {args.compare}", file=sys.stderr)


def _print_summary(results: list[dict], args) -> None:
    """Print summary statistics to stderr."""
    n = len(results)
    slis = [r["sli"] for r in results]
    mean_sli = sum(slis) / n
    sorted_slis = sorted(slis)
    median_sli = sorted_slis[n // 2] if n % 2 == 1 else (sorted_slis[n // 2 - 1] + sorted_slis[n // 2]) / 2

    days_label = "today" if getattr(args, "today", False) else f"{args.days}-day"

    print(file=sys.stderr)
    print(
        f"{days_label} summary: {n} sessions, mean SLI: {mean_sli:.1f}, "
        f"median SLI: {median_sli:.1f}",
        file=sys.stderr,
    )

    # AGR
    agr = compute_agr(results)
    if agr is not None:
        direction = "positive = improving" if agr >= 0 else "negative = declining"
        print(f"AGR (autonomy gain rate): {agr:+.4f} ({direction})", file=sys.stderr)
    else:
        print("AGR: insufficient data (need 5+ sessions)", file=sys.stderr)

    # By project
    from collections import defaultdict

    by_project: dict[str, list[float]] = defaultdict(list)
    for r in results:
        by_project[r["project"]].append(r["sli"])

    if len(by_project) > 1:
        parts = []
        for proj in sorted(by_project):
            proj_slis = by_project[proj]
            proj_mean = sum(proj_slis) / len(proj_slis)
            parts.append(f"{proj}={proj_mean:.1f}")
        print(f"By project: {', '.join(parts)}", file=sys.stderr)

    # AIR summary (only sessions with hooks)
    air_sessions = [r for r in results if r["air"] is not None]
    if air_sessions:
        total_hooks = sum(r["hooks_shown"] for r in air_sessions)
        total_corrections_after = sum(r["corrections_after_hooks"] for r in air_sessions)
        overall_air = total_corrections_after / total_hooks if total_hooks else 0
        print(
            f"AIR: {overall_air:.3f} ({total_corrections_after}/{total_hooks} "
            f"corrections after hooks, lower = better)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
