#!/usr/bin/env python3
"""
Token baseline measurements for the token reduction action plan.

Queries runlogs.db to establish baselines for:
1. Full-file reads (>500 lines) frequency and distribution
2. Bash/tool output size distribution (P50/P90/P95)
3. Post-compaction rereads (files re-read within 5 events of compaction)
4. Top-decile session cost attribution by driver
5. Tool output volume by tool name

Usage:
    uv run python3 scripts/token-baseline.py [--days 30]
"""

import sqlite3
import json
import sys
import statistics
from pathlib import Path
from collections import defaultdict

DB = Path.home() / ".claude" / "runlogs.db"
RECEIPTS = Path.home() / ".claude" / "session-receipts.jsonl"

def _ok(msg):  print(f"  ✓ {msg}")
def _warn(msg): print(f"  ! {msg}")
def _fail(msg): print(f"  ✗ {msg}")
def _header(s): print(f"\n[{s}]")
def _kv(k, v): print(f"  {k:40s} {v}")

def percentile(data, p):
    """Simple percentile calculation."""
    if not data:
        return 0
    s = sorted(data)
    idx = int(len(s) * p / 100)
    return s[min(idx, len(s) - 1)]


def analyze_tool_output_sizes(conn, days):
    """Measure tool output sizes by tool name."""
    _header("Tool Output Size Distribution")

    # Use direct tool_result analysis with tool name from text field of preceding tool_call
    # Avoid expensive cross-event joins on 7.7GB DB
    rows = conn.execute("""
        SELECT e.text as tool_name, LENGTH(r_evt.text) as result_len
        FROM events e
        JOIN events r_evt ON e.run_id = r_evt.run_id AND r_evt.seq = e.seq + 1
        WHERE e.kind = 'tool_call'
        AND r_evt.kind = 'tool_result'
        AND e.ts > date('now', ?)
        AND r_evt.text IS NOT NULL
        AND e.text IS NOT NULL
        ORDER BY e.ts DESC
        LIMIT 50000
    """, (f"-{days} days",)).fetchall()

    if not rows:
        _warn("No tool call/result pairs found")
        return

    by_tool = defaultdict(list)
    for tool_name, result_len in rows:
        if result_len and tool_name:
            by_tool[tool_name].append(result_len)

    print(f"  {'Tool':<25s} {'Count':>7s} {'P50':>8s} {'P90':>8s} {'P95':>8s} {'Max':>8s} {'>10K':>6s}")
    print(f"  {'─'*25} {'─'*7} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6}")

    for tool in sorted(by_tool, key=lambda t: sum(by_tool[t]), reverse=True)[:15]:
        sizes = by_tool[tool]
        n = len(sizes)
        p50 = percentile(sizes, 50)
        p90 = percentile(sizes, 90)
        p95 = percentile(sizes, 95)
        mx = max(sizes)
        over10k = sum(1 for s in sizes if s > 10000)
        print(f"  {tool:<25s} {n:>7d} {p50:>8,d} {p90:>8,d} {p95:>8,d} {mx:>8,d} {over10k:>6d}")

    all_sizes = [r for sizes in by_tool.values() for r in sizes]
    if all_sizes:
        total_chars = sum(all_sizes)
        over_10k = sum(1 for s in all_sizes if s > 10000)
        over_50k = sum(1 for s in all_sizes if s > 50000)
        print(f"\n  Total tool results: {len(all_sizes):,d}")
        print(f"  Total chars: {total_chars:,.0f} (~{total_chars / 4:,.0f} tokens)")
        print(f"  Results >10K chars: {over_10k:,d} ({over_10k / len(all_sizes) * 100:.1f}%)")
        print(f"  Results >50K chars: {over_50k:,d} ({over_50k / len(all_sizes) * 100:.1f}%)")


def analyze_full_file_reads(conn, days):
    """Count Read tool calls that appear to be full-file reads (no offset/limit)."""
    _header("Full-File Read Analysis")

    rows = conn.execute("""
        SELECT e.payload_json, LENGTH(r_evt.text) as result_len
        FROM events e
        LEFT JOIN events r_evt ON e.run_id = r_evt.run_id AND r_evt.seq = e.seq + 1 AND r_evt.kind = 'tool_result'
        WHERE e.kind = 'tool_call'
        AND e.text = 'Read'
        AND e.ts > date('now', ?)
        ORDER BY e.ts DESC
        LIMIT 20000
    """, (f"-{days} days",)).fetchall()

    if not rows:
        _warn("No Read tool calls found in events data")
        return

    total_reads = len(rows)
    full_reads = 0
    targeted_reads = 0
    large_results = 0
    sizes = []

    for payload_json, result_len in rows:
        try:
            payload = json.loads(payload_json) if payload_json else {}
            inp = payload.get("input", {})
            has_offset = "offset" in inp
            has_limit = "limit" in inp
            has_pages = "pages" in inp

            if not has_offset and not has_limit and not has_pages:
                full_reads += 1
            else:
                targeted_reads += 1

            if result_len and result_len > 10000:
                large_results += 1
            if result_len:
                sizes.append(result_len)
        except json.JSONDecodeError:
            pass

    _kv("Total Read calls:", f"{total_reads:,d}")
    _kv("Full-file reads (no offset/limit):", f"{full_reads:,d} ({full_reads / total_reads * 100:.1f}%)")
    _kv("Targeted reads (with offset/limit):", f"{targeted_reads:,d} ({targeted_reads / total_reads * 100:.1f}%)")
    _kv("Results >10K chars:", f"{large_results:,d}")
    if sizes:
        _kv("Read result size P50:", f"{percentile(sizes, 50):,d} chars")
        _kv("Read result size P90:", f"{percentile(sizes, 90):,d} chars")
        _kv("Read result size P95:", f"{percentile(sizes, 95):,d} chars")


def analyze_session_cost_drivers(days):
    """Classify top-decile session costs by project."""
    _header("Top-Decile Session Cost Attribution")

    sessions = []
    with open(RECEIPTS) as f:
        for line in f:
            d = json.loads(line.strip())
            if d.get("ts", "") < "2026-01-01":
                continue
            sessions.append(d)

    if not sessions:
        _warn("No session receipts found")
        return

    # Sort by cost, take top 10%
    sessions.sort(key=lambda s: s.get("cost_usd", 0), reverse=True)
    n = len(sessions)
    top_decile = sessions[:max(1, n // 10)]

    by_project = defaultdict(lambda: {"count": 0, "cost": 0.0, "durations": [], "contexts": []})
    for s in top_decile:
        proj = s.get("project", "unknown")
        by_project[proj]["count"] += 1
        by_project[proj]["cost"] += s.get("cost_usd", 0)
        by_project[proj]["durations"].append(s.get("duration_min", 0))
        by_project[proj]["contexts"].append(s.get("context_pct", 0))

    total_top = sum(d["cost"] for d in by_project.values())
    print(f"  Top {len(top_decile)} sessions ({len(top_decile)/n*100:.0f}%): ${total_top:,.2f}")
    print()
    print(f"  {'Project':<15s} {'Sessions':>8s} {'Cost':>10s} {'%':>6s} {'Avg Dur':>10s} {'Avg Ctx':>8s}")
    print(f"  {'─'*15} {'─'*8} {'─'*10} {'─'*6} {'─'*10} {'─'*8}")

    for proj in sorted(by_project, key=lambda p: by_project[p]["cost"], reverse=True):
        d = by_project[proj]
        avg_dur = statistics.mean(d["durations"]) if d["durations"] else 0
        avg_ctx = statistics.mean(d["contexts"]) if d["contexts"] else 0
        pct = d["cost"] / total_top * 100
        print(f"  {proj:<15s} {d['count']:>8d} ${d['cost']:>9,.2f} {pct:>5.1f}% {avg_dur:>9.1f}m {avg_ctx:>7.1f}%")


def analyze_compaction_rereads(conn, days):
    """Check if files are re-read shortly after compaction events."""
    _header("Post-Compaction Reread Analysis")

    # Find compaction events (status_update with compaction-related text)
    compactions = conn.execute("""
        SELECT e.run_id, e.seq, e.ts
        FROM events e
        JOIN runs r ON e.run_id = r.run_id
        JOIN sessions s ON r.session_pk = s.session_pk
        WHERE s.vendor = 'claude'
        AND e.kind = 'status_update'
        AND (e.text LIKE '%compact%' OR e.text LIKE '%compress%' OR e.text LIKE '%summar%')
        AND e.ts > date('now', ?)
    """, (f"-{days} days",)).fetchall()

    _kv("Compaction-like status events found:", f"{len(compactions):,d}")

    if not compactions:
        _warn("No compaction events found in events table. Using compact-log.jsonl instead.")
        compact_log = Path.home() / ".claude" / "compact-log.jsonl"
        if compact_log.exists():
            count = 0
            with open(compact_log) as f:
                for line in f:
                    d = json.loads(line.strip())
                    count += 1
            _kv("Entries in compact-log.jsonl:", f"{count:,d}")
            _warn("Cannot measure rereads from compact-log alone — need event-level correlation")
        return


def analyze_token_usage_by_project(conn, days):
    """Break down token usage by project from token_usage events."""
    _header("Token Usage by Project (from events)")

    rows = conn.execute("""
        SELECT s.project_slug,
            json_extract(e.payload_json, '$.info.total_token_usage.input_tokens') as input_tok,
            json_extract(e.payload_json, '$.info.total_token_usage.cached_input_tokens') as cached_tok,
            json_extract(e.payload_json, '$.info.total_token_usage.output_tokens') as output_tok,
            json_extract(e.payload_json, '$.info.total_token_usage.reasoning_output_tokens') as reason_tok
        FROM events e
        JOIN runs r ON e.run_id = r.run_id
        JOIN sessions s ON r.session_pk = s.session_pk
        WHERE e.kind = 'token_usage'
        AND e.ts > date('now', ?)
        AND s.project_slug IN ('agent-infra', 'genomics', 'phenome', 'intel', 'arc-agi')
    """, (f"-{days} days",)).fetchall()

    if not rows:
        _warn("No token_usage events found for the period")
        return

    by_project = defaultdict(lambda: {"input": [], "cached": [], "output": [], "reasoning": []})
    for proj, inp, cached, out, reason in rows:
        if inp:
            by_project[proj]["input"].append(int(inp))
            by_project[proj]["cached"].append(int(cached or 0))
            by_project[proj]["output"].append(int(out or 0))
            by_project[proj]["reasoning"].append(int(reason or 0))

    print(f"  {'Project':<12s} {'Events':>7s} {'Avg Input':>12s} {'Cache%':>7s} {'Avg Output':>12s} {'Reason%':>8s}")
    print(f"  {'─'*12} {'─'*7} {'─'*12} {'─'*7} {'─'*12} {'─'*8}")

    for proj in sorted(by_project, key=lambda p: statistics.mean(by_project[p]["input"]) if by_project[p]["input"] else 0, reverse=True):
        d = by_project[proj]
        n = len(d["input"])
        avg_inp = statistics.mean(d["input"])
        avg_cached = statistics.mean(d["cached"])
        cache_pct = avg_cached / avg_inp * 100 if avg_inp > 0 else 0
        avg_out = statistics.mean(d["output"])
        avg_reason = statistics.mean(d["reasoning"])
        reason_pct = avg_reason / avg_out * 100 if avg_out > 0 else 0
        print(f"  {proj:<12s} {n:>7d} {avg_inp:>11,.0f} {cache_pct:>6.1f}% {avg_out:>11,.0f} {reason_pct:>7.1f}%")


def main():
    days = 30
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        days = int(sys.argv[idx + 1])

    print(f"Token Baseline Report — last {days} days")
    print(f"{'═' * 60}")

    if not DB.exists():
        _fail(f"Runlogs DB not found at {DB}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB))

    analyze_session_cost_drivers(days)
    analyze_tool_output_sizes(conn, days)
    analyze_full_file_reads(conn, days)
    analyze_token_usage_by_project(conn, days)
    analyze_compaction_rereads(conn, days)

    conn.close()
    print(f"\n{'═' * 60}")
    print("Done. Run weekly to track changes.")


if __name__ == "__main__":
    main()
