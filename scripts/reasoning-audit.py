#!/usr/bin/env python3
"""
Reasoning audit — identify expensive sessions where /fast mode would save money.

Analyzes the most expensive sessions and flags those where extended thinking
is likely wasteful: high tool-call counts (interactive/mechanical work) with
thinking blocks active.

Data limitations:
  - Claude JSONL redacts thinking block content (present but empty)
  - output_tokens in JSONL usage excludes reasoning tokens
  - Reasoning billing is invisible in local data

What we CAN measure:
  - Which turns used thinking (thinking block presence)
  - Visible output_tokens per turn
  - Tool call counts (proxy for mechanical vs reasoning-heavy work)

Estimation: Measured data from sessions with full token breakdowns shows
reasoning_output_tokens averages ~50% of total output (range: 38-73%).
Claude's extended thinking likely generates comparable volume, billed at
output rate ($75/M for Opus 4). /fast eliminates this entirely.

Usage:
    uv run python3 scripts/reasoning-audit.py [--top N] [--days D]
"""

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common.console import con

DB = Path.home() / ".claude" / "runlogs.db"

# Measured from sessions with token_usage events (Codex/Gemini):
# reasoning_output_tokens / output_tokens median ≈ 50% (range 38-73%)
# For /fast savings: reasoning tokens billed at output rate ($75/M Opus 4)
# but represent pure overhead on tool-heavy turns.


def get_top_sessions(conn, top_n, days):
    """Get top N sessions by cost from runlogs.db."""
    rows = conn.execute("""
        SELECT session_pk, vendor_session_id, project_slug, cost_usd,
               duration_min, started_at, jsonl_path, model
        FROM sessions
        WHERE cost_usd IS NOT NULL AND cost_usd > 0
          AND (started_at > date('now', ?) OR ? = 0)
        ORDER BY cost_usd DESC
        LIMIT ?
    """, (f"-{days} days", days, top_n)).fetchall()
    return rows


def batch_tool_call_counts(conn, session_pks):
    """Count tool_call events for multiple sessions in one query."""
    if not session_pks:
        return {}
    placeholders = ",".join("?" * len(session_pks))
    rows = conn.execute(f"""
        SELECT r.session_pk, COUNT(*)
        FROM events e
        JOIN runs r ON e.run_id = r.run_id
        WHERE r.session_pk IN ({placeholders}) AND e.kind = 'tool_call'
        GROUP BY r.session_pk
    """, session_pks).fetchall()
    return dict(rows)


def analyze_jsonl(jsonl_path):
    """Extract thinking/tool metrics from a session JSONL file."""
    result = {
        "tool_calls": 0,
        "thinking_turns": 0,
        "total_turns": 0,
        "total_output_tokens": 0,
    }

    path = Path(jsonl_path)
    if not path.exists():
        return result

    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            if d.get("type") != "assistant":
                continue

            msg = d.get("message", {})
            content = msg.get("content", [])
            usage = msg.get("usage", {})

            if not isinstance(content, list):
                continue

            result["total_turns"] += 1
            output_tok = usage.get("output_tokens", 0)
            result["total_output_tokens"] += output_tok

            has_thinking = False
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "tool_use":
                    result["tool_calls"] += 1
                elif btype == "thinking":
                    has_thinking = True

            if has_thinking:
                result["thinking_turns"] += 1

    return result


def main():
    parser = argparse.ArgumentParser(description="Reasoning audit — find /fast savings")
    parser.add_argument("--top", type=int, default=20, help="Number of top sessions")
    parser.add_argument("--days", type=int, default=0, help="Limit to last N days (0=all)")
    args = parser.parse_args()

    if not DB.exists():
        con.fail(f"Runlogs DB not found: {DB}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB))
    sessions = get_top_sessions(conn, args.top, args.days)

    if not sessions:
        con.fail("No sessions with cost data found")
        sys.exit(1)

    con.header(f"Reasoning Audit — Top {len(sessions)} Sessions")

    headers = ["Session", "Project", "Cost", "Duration", "Turns",
               "Think", "Tools", "Flag"]
    widths = [12, 12, 10, 9, 7, 7, 7, 10]

    rows = []
    flagged_sessions = []
    project_flags = defaultdict(int)

    # Batch query: tool call counts for all sessions at once
    session_pks = [s[0] for s in sessions]
    tool_counts = batch_tool_call_counts(conn, session_pks)

    for (session_pk, vendor_session_id, project_slug, cost_usd,
         duration_min, started_at, jsonl_path, model) in sessions:

        sid_short = (vendor_session_id or str(session_pk))[:8] + ".."

        tool_calls = tool_counts.get(session_pk, 0)

        metrics = analyze_jsonl(jsonl_path) if jsonl_path else {
            "tool_calls": 0, "thinking_turns": 0,
            "total_turns": 0, "total_output_tokens": 0}

        # Use JSONL tool count if events had zero (different import paths)
        if tool_calls == 0:
            tool_calls = metrics["tool_calls"]

        total_turns = metrics["total_turns"]
        thinking_turns = metrics["thinking_turns"]

        # Flag: >20 tool calls AND thinking active on >5 turns
        # Tool-heavy sessions are mechanical — thinking adds cost without value
        flag = ""
        if tool_calls > 20 and thinking_turns > 5:
            flag = "HIGH"
            flagged_sessions.append({
                "pk": session_pk, "project": project_slug,
                "cost": cost_usd, "thinking_turns": thinking_turns,
                "total_turns": total_turns, "tool_calls": tool_calls,
            })
            project_flags[project_slug] += 1

        dur_str = f"{duration_min:.0f}m" if duration_min else "—"

        rows.append([
            sid_short,
            project_slug or "?",
            f"${cost_usd:,.2f}",
            dur_str,
            str(total_turns) if total_turns > 0 else "—",
            str(thinking_turns) if total_turns > 0 else "—",
            str(tool_calls) if tool_calls > 0 else "—",
            flag,
        ])

    con.table(headers, rows, widths)

    # Summary
    print()
    n_flagged = len(flagged_sessions)
    flagged_cost = sum(s["cost"] for s in flagged_sessions)
    total_cost = sum(s[3] for s in sessions)

    if n_flagged > 0:
        con.ok(f"{n_flagged}/{len(sessions)} sessions flagged as tool-heavy + thinking active")

        # Reasoning cost estimate: from measured data, ~50% of output tokens
        # are reasoning. Output is ~12-15% of total cost on Opus 4 (cache-read
        # dominated sessions). Reasoning portion of output ≈ 50% of that.
        # Conservative: /fast saves 5-8% of flagged session costs.
        savings_low = flagged_cost * 0.05
        savings_high = flagged_cost * 0.08
        con.ok(f"Estimated savings with /fast on flagged: "
               f"${savings_low:,.0f}–${savings_high:,.0f} "
               f"(5-8% of ${flagged_cost:,.0f} flagged cost)")

        top_projects = sorted(project_flags.items(), key=lambda x: -x[1])
        proj_str = ", ".join(f"{p} ({c})" for p, c in top_projects)
        con.ok(f"Projects most affected: {proj_str}")

        # Per-project breakdown
        print()
        con.header("Per-Project Reasoning Exposure")
        proj_data = defaultdict(lambda: {"sessions": 0, "cost": 0, "thinking_turns": 0})
        for s in flagged_sessions:
            p = s["project"]
            proj_data[p]["sessions"] += 1
            proj_data[p]["cost"] += s["cost"]
            proj_data[p]["thinking_turns"] += s["thinking_turns"]

        ph = ["Project", "Sessions", "Cost", "Think Turns", "Savings Est."]
        pw = [14, 10, 12, 14, 14]
        pr = []
        for proj in sorted(proj_data, key=lambda p: -proj_data[p]["cost"]):
            d = proj_data[proj]
            sav = f"${d['cost'] * 0.05:,.0f}–${d['cost'] * 0.08:,.0f}"
            pr.append([proj, str(d["sessions"]), f"${d['cost']:,.2f}",
                       str(d["thinking_turns"]), sav])
        con.table(ph, pr, pw)
    else:
        con.ok(f"0/{len(sessions)} sessions flagged — thinking usage appears proportionate")

    # Data coverage
    sessions_with_jsonl = sum(1 for s in sessions if s[6] and Path(s[6]).exists())
    print()
    con.kv("Sessions analyzed", f"{len(sessions)} (${total_cost:,.0f} total)")
    con.kv("JSONL files found", f"{sessions_with_jsonl}/{len(sessions)}")
    con.kv("Reasoning estimate", "50% of output is reasoning (measured median)")
    con.kv("Savings model", "5-8% of session cost (output share * reasoning ratio)")
    if sessions_with_jsonl < len(sessions):
        con.warn(f"{len(sessions) - sessions_with_jsonl} sessions lack JSONL — "
                 "thinking turns not countable")

    conn.close()


if __name__ == "__main__":
    main()
