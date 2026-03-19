#!/usr/bin/env python3
"""Agent ops dashboard.

Reads Claude Code receipts plus Codex/OpenAI run data to show weekly/all-time
stats: cost, duration, compactions, top projects, and provider-specific usage.

Usage: uv run python3 scripts/dashboard.py [--days N]
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from agent_receipts import collect_codex_receipts, load_openai_receipts

RECEIPTS = Path.home() / ".claude" / "session-receipts.jsonl"
COMPACTIONS = Path.home() / ".claude" / "compact-log.jsonl"
EPISTEMIC_METRICS = Path.home() / ".claude" / "epistemic-metrics.jsonl"
MIN_TS = datetime.min


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def parse_ts(ts: str) -> datetime:
    if ts.endswith("Z"):
        try:
            return datetime.fromisoformat(ts[:-1] + "+00:00").replace(tzinfo=None)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(ts).replace(tzinfo=None)
    except ValueError:
        pass
    # Handle legacy ISO formats
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return datetime.min


def main():
    days = 7
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    cutoff = datetime.now() - timedelta(days=days)

    # --- Load data ---
    receipts = load_jsonl(RECEIPTS)
    compactions = load_jsonl(COMPACTIONS)

    recent = [r for r in receipts if parse_ts(r.get("ts", "")) > cutoff]
    recent_compactions = [c for c in compactions if parse_ts(c.get("ts", "")) > cutoff]

    if not recent:
        print(f"No sessions in the last {days} days.")
        if receipts:
            print(f"({len(receipts)} total receipts on file)")
        else:
            print("No receipts yet. Receipts are written when sessions end.")
        return

    # --- Aggregate ---
    # Sum cost including compaction iterations (top-level usage excludes compaction)
    total_cost = 0.0
    for r in recent:
        base_cost = float(r.get("cost_usd", 0))
        # Check for compaction iteration costs (usage.iterations[] array)
        iterations = r.get("usage", {}).get("iterations", []) if isinstance(r.get("usage"), dict) else []
        iter_cost = sum(float(it.get("cost_usd", 0)) for it in iterations if isinstance(it, dict))
        total_cost += base_cost + iter_cost
    total_mins = sum(float(r.get("duration_min", 0)) for r in recent)
    total_lines_add = sum(int(r.get("lines_added", 0)) for r in recent)
    total_lines_rm = sum(int(r.get("lines_removed", 0)) for r in recent)
    avg_context = sum(int(r.get("context_pct", 0)) for r in recent) / len(recent)

    # By project
    by_project: dict[str, dict] = defaultdict(lambda: {"sessions": 0, "cost": 0.0, "mins": 0.0})
    for r in recent:
        p = r.get("project", "?")
        by_project[p]["sessions"] += 1
        by_project[p]["cost"] += float(r.get("cost_usd", 0))
        by_project[p]["mins"] += float(r.get("duration_min", 0))

    # By model
    by_model: dict[str, int] = defaultdict(int)
    for r in recent:
        by_model[r.get("model", "?")] += 1

    # Exit reasons
    by_reason: dict[str, int] = defaultdict(int)
    for r in recent:
        by_reason[r.get("reason", "?")] += 1

    # --- Print ---
    print(f"{'=' * 50}")
    print(f"  Agent Ops Dashboard — last {days} days")
    print(f"{'=' * 50}")
    print()
    print(f"  Sessions:     {len(recent)}")
    print(f"  Total cost:   ${total_cost:.2f}")
    print(f"  Total time:   {total_mins:.0f} min ({total_mins/60:.1f} hrs)")
    print(f"  Avg context:  {avg_context:.0f}% at exit")
    print(f"  Code churn:   +{total_lines_add} / -{total_lines_rm}")
    print(f"  Compactions:  {len(recent_compactions)}")
    print()

    # By project table
    print("  By project:")
    sorted_projects = sorted(by_project.items(), key=lambda x: x[1]["cost"], reverse=True)
    for proj, stats in sorted_projects:
        print(f"    {proj:<20} {stats['sessions']:>3} sessions  ${stats['cost']:>6.2f}  {stats['mins']:>5.0f}m")
    print()

    # By model
    print("  By model:")
    for model, count in sorted(by_model.items(), key=lambda x: x[1], reverse=True):
        print(f"    {model:<20} {count:>3} sessions")
    print()

    # Exit reasons
    print("  Exit reasons:")
    for reason, count in sorted(by_reason.items(), key=lambda x: x[1], reverse=True):
        print(f"    {reason:<20} {count:>3}")
    print()

    # All-time summary if we have more data
    if len(receipts) > len(recent):
        all_cost = 0.0
        for r in receipts:
            base = float(r.get("cost_usd", 0))
            iters = r.get("usage", {}).get("iterations", []) if isinstance(r.get("usage"), dict) else []
            all_cost += base + sum(float(it.get("cost_usd", 0)) for it in iters if isinstance(it, dict))
        print(f"  All-time: {len(receipts)} sessions, ${all_cost:.2f} total")

    # --- Orchestrator panel ---
    print_orchestrator_panel(cutoff)

    # --- OpenAI / Codex panel ---
    print_openai_panel(cutoff)

    # --- Session facets panel (from /insights data) ---
    print_facets_panel(cutoff)

    # --- Overview freshness panel ---
    print_overview_panel()

    # --- Epistemic metrics panel ---
    print_epistemic_panel(cutoff)


def print_openai_panel(cutoff: datetime):
    """Print Codex/OpenAI usage from normalized receipts."""
    codex = collect_codex_receipts(cutoff=cutoff)
    openai = [r for r in load_openai_receipts() if parse_ts(r.get("ts", "")) > cutoff]
    runs = codex + openai
    if not runs:
        return

    print()
    print(f"{'=' * 50}")
    print("  OpenAI / Codex")
    print(f"{'=' * 50}")
    print()

    by_source = defaultdict(int)
    by_status = defaultdict(int)
    total_in = 0
    total_out = 0
    total_reasoning = 0
    total_cached = 0
    total_tools = 0

    for run in runs:
        by_source[run.get("source", "?")] += 1
        by_status[run.get("status", "?")] += 1
        total_in += int(run.get("input_tokens", 0) or 0)
        total_out += int(run.get("output_tokens", 0) or 0)
        total_reasoning += int(run.get("reasoning_output_tokens", 0) or 0)
        total_cached += int(run.get("cached_input_tokens", 0) or 0)
        total_tools += int(run.get("tool_call_count", 0) or 0)

    source_str = ", ".join(f"{count} {source}" for source, count in sorted(by_source.items()))
    status_str = ", ".join(f"{count} {status}" for status, count in sorted(by_status.items()))
    print(f"  Runs:         {len(runs)} ({source_str})")
    print(f"  Status:       {status_str}")
    print(f"  Tokens:       {total_in:,} in / {total_out:,} out / {total_reasoning:,} reasoning / {total_cached:,} cached")
    print(f"  Tool calls:   {total_tools:,}")

    background = defaultdict(int)
    for run in openai:
        state = run.get("background_state")
        if state:
            background[state] += 1
    if background:
        bg_str = ", ".join(f"{count} {state}" for state, count in sorted(background.items()))
        print(f"  Background:   {bg_str}")

    print()
    print("  Recent runs:")
    recent = sorted(runs, key=lambda row: parse_ts(row.get("ts", "")) or MIN_TS, reverse=True)[:6]
    for run in recent:
        source = run.get("source", "?")
        run_id = run.get("response_id") or run.get("session") or run.get("run_id") or "?"
        short_id = str(run_id)[:12]
        project = run.get("project") or "?"
        model = run.get("model") or "?"
        effort = run.get("reasoning_effort") or "-"
        status = run.get("background_state") or run.get("status") or "?"
        tools = int(run.get("tool_call_count", 0) or 0)
        tags = run.get("task_tags") or run.get("metadata_tags") or []
        tag_str = ",".join(tags[:3]) if tags else "-"
        task_label = run.get("task_label") or "-"
        print(
            f"    {source:<16} {short_id:<12} {project:<12} {model:<12} "
            f"{status:<11} tools={tools:<3} effort={effort:<6} tags={tag_str}"
        )
        if task_label != "-":
            print(f"      {task_label[:90]}")


def print_orchestrator_panel(cutoff: datetime):
    """Print orchestrator task stats from SQLite DB."""
    db_path = Path.home() / ".claude" / "orchestrator.db"
    if not db_path.exists():
        return

    from common.db import open_db
    db = open_db(db_path)

    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    tasks = db.execute("""
        SELECT * FROM tasks
        WHERE created_at >= ? OR finished_at >= ?
        ORDER BY created_at DESC
    """, (cutoff_str, cutoff_str)).fetchall()

    if not tasks:
        db.close()
        return

    print()
    print(f"{'=' * 50}")
    print("  Orchestrator")
    print(f"{'=' * 50}")
    print()

    by_status = defaultdict(int)
    total_cost = 0.0
    total_tokens_in = 0
    total_tokens_out = 0
    for t in tasks:
        by_status[t["status"]] += 1
        total_cost += t["cost_usd"] or 0
        total_tokens_in += t["tokens_in"] or 0
        total_tokens_out += t["tokens_out"] or 0

    status_str = ", ".join(f"{v} {k}" for k, v in sorted(by_status.items()))
    print(f"  Tasks:        {len(tasks)} ({status_str})")
    print(f"  Total cost:   ${total_cost:.2f}")
    if total_tokens_in or total_tokens_out:
        print(f"  Tokens:       {total_tokens_in:,} in / {total_tokens_out:,} out")

    # By pipeline
    by_pipeline = defaultdict(lambda: {"done": 0, "failed": 0, "pending": 0, "cost": 0.0})
    for t in tasks:
        p = t["pipeline"] or "(one-off)"
        if t["status"] in ("done", "done_with_denials"):
            by_pipeline[p]["done"] += 1
        elif t["status"] == "failed":
            by_pipeline[p]["failed"] += 1
        else:
            by_pipeline[p]["pending"] += 1
        by_pipeline[p]["cost"] += t["cost_usd"] or 0

    if by_pipeline:
        print()
        print("  By pipeline:")
        for pipe, stats in sorted(by_pipeline.items(), key=lambda x: -x[1]["cost"]):
            parts = []
            if stats["done"]:
                parts.append(f"{stats['done']} done")
            if stats["failed"]:
                parts.append(f"{stats['failed']} failed")
            if stats["pending"]:
                parts.append(f"{stats['pending']} pending")
            print(f"    {pipe:<25} {', '.join(parts):<25} ${stats['cost']:.2f}")

    # Recent failures
    failures = [t for t in tasks if t["status"] == "failed"]
    if failures:
        print()
        print("  Recent failures:")
        for t in failures[:5]:
            err = (t["error"] or "?")[:60]
            print(f"    #{t['id']} {t['pipeline'] or '-'}/{t['step'] or '-'}: {err}")

    print()
    db.close()


def print_overview_panel():
    """Print overview freshness across projects."""
    from config import PROJECT_ROOTS
    import re as _re

    rows = []
    for name, root in PROJECT_ROOTS.items():
        overview_dir = root / ".claude" / "overviews"
        if not overview_dir.exists():
            continue
        for f in sorted(overview_dir.glob("*-overview.md")):
            try:
                text = f.read_text(errors="replace")[:500]
                m = _re.search(
                    r"<!-- Generated: (\S+) \| git: (\S+) \| model: (\S+) -->", text
                )
                otype = f.stem.replace("-overview", "")
                if m:
                    gen_ts = m.group(1)
                    try:
                        gen_dt = datetime.fromisoformat(gen_ts.replace("Z", "+00:00")).replace(tzinfo=None)
                        age_days = (datetime.now() - gen_dt).days
                        age = f"{age_days}d" if age_days > 0 else "<1d"
                    except ValueError:
                        age = "?"
                else:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    age_days = (datetime.now() - mtime).days
                    age = f"~{age_days}d"
                rows.append((name, otype, age))
            except OSError:
                continue

    if not rows:
        return

    print()
    print(f"{'=' * 50}")
    print("  Overviews")
    print(f"{'=' * 50}")
    print()
    for name, otype, age in rows:
        print(f"    {name:<12} {otype:<12} {age}")
    print()


def print_facets_panel(cutoff: datetime):
    """Print session quality metrics from Claude Code /insights facet data."""
    facets_dir = Path.home() / ".claude" / "usage-data" / "facets"
    meta_dir = Path.home() / ".claude" / "usage-data" / "session-meta"
    if not facets_dir.exists():
        return

    # Load facets and session-meta, join by session_id
    facets = []
    for f in facets_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            facets.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    # Load session-meta for timestamp filtering
    meta_by_id: dict[str, dict] = {}
    if meta_dir.exists():
        for f in meta_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                sid = data.get("session_id", f.stem)
                meta_by_id[sid] = data
            except (json.JSONDecodeError, OSError):
                continue

    # Filter to recent sessions
    recent_facets = []
    for fac in facets:
        sid = fac.get("session_id", "")
        meta = meta_by_id.get(sid, {})
        ts = meta.get("start_time", "")
        if ts and parse_ts(ts) > cutoff:
            recent_facets.append((fac, meta))

    if not recent_facets:
        return

    print()
    print(f"{'=' * 50}")
    print(f"  Session Facets ({len(recent_facets)} sessions)")
    print(f"{'=' * 50}")
    print()

    # Outcome distribution
    outcomes: dict[str, int] = defaultdict(int)
    friction_totals: dict[str, int] = defaultdict(int)
    session_types: dict[str, int] = defaultdict(int)
    total_tool_errors = 0
    total_friction_sessions = 0

    for fac, meta in recent_facets:
        outcome = fac.get("outcome", "?")
        outcomes[outcome] += 1

        stype = fac.get("session_type", "?")
        session_types[stype] += 1

        fc = fac.get("friction_counts", {})
        if fc:
            total_friction_sessions += 1
            for ftype, count in fc.items():
                friction_totals[ftype] += count

        total_tool_errors += meta.get("tool_errors", 0)

    # Outcomes
    outcome_parts = []
    for o in ["fully_achieved", "mostly_achieved", "partially_achieved", "not_achieved"]:
        if outcomes.get(o):
            outcome_parts.append(f"{outcomes[o]} {o.replace('_', ' ')}")
    if outcome_parts:
        print(f"  Outcomes:     {', '.join(outcome_parts)}")

    # Friction
    if friction_totals:
        sorted_friction = sorted(friction_totals.items(), key=lambda x: -x[1])[:5]
        friction_str = ", ".join(f"{k}={v}" for k, v in sorted_friction)
        print(f"  Friction:     {total_friction_sessions}/{len(recent_facets)} sessions ({friction_str})")
    else:
        print(f"  Friction:     0/{len(recent_facets)} sessions")

    if total_tool_errors:
        print(f"  Tool errors:  {total_tool_errors}")

    # Session types
    if session_types:
        type_parts = sorted(session_types.items(), key=lambda x: -x[1])[:4]
        print(f"  Types:        {', '.join(f'{v} {k}' for k, v in type_parts)}")

    print()


def print_epistemic_panel(cutoff: datetime):
    """Print epistemic health metrics from epistemic-metrics.jsonl."""
    metrics = load_jsonl(EPISTEMIC_METRICS)
    if not metrics:
        return

    recent = [m for m in metrics if parse_ts(m.get("ts", "")) > cutoff]
    if not recent:
        return

    print()
    print(f"{'=' * 50}")
    print("  Epistemic Health")
    print(f"{'=' * 50}")
    print()

    # Latest pushback index
    pushback = [m for m in recent if m.get("metric") == "pushback_index"]
    if pushback:
        latest = pushback[-1]
        rate = latest.get("overall_rate", 0)
        zero = latest.get("zero_pushback_sessions", 0)
        sessions = latest.get("sessions", 0)
        print(f"  Pushback index:     {rate:.1%} ({zero} zero-pushback of {sessions} sessions)")
        by_proj = latest.get("by_project", {})
        if by_proj:
            parts = [f"{p}={v:.0%}" for p, v in sorted(by_proj.items())]
            print(f"    by project: {', '.join(parts)}")

    # Latest lint results
    lint = [m for m in recent if m.get("metric") == "epistemic_lint"]
    if lint:
        latest = lint[-1]
        unsourced = latest.get("unsourced_claims", 0)
        files = latest.get("files_scanned", 0)
        issue_rate = latest.get("issue_rate", 0)
        print(f"  Epistemic lint:     {unsourced} unsourced claims ({issue_rate:.0%} of {files} files)")
        by_type = latest.get("by_type", {})
        if by_type:
            top3 = sorted(by_type.items(), key=lambda x: -x[1])[:3]
            parts = [f"{t}={c}" for t, c in top3]
            print(f"    top types: {', '.join(parts)}")

    # Latest SAFE-lite eval
    safe = [m for m in recent if m.get("metric") == "safe_lite_eval"]
    if safe:
        latest = safe[-1]
        precision = latest.get("factual_precision")
        checked = latest.get("claims_checked", 0)
        supported = latest.get("supported", 0)
        contradicted = latest.get("contradicted", 0)
        if precision is not None:
            print(f"  SAFE-lite precision: {precision:.1%} ({supported}S/{contradicted}C of {checked} claims)")
        else:
            print(f"  SAFE-lite:          {checked} claims checked, no judged results")

    # Latest trace-faithfulness results
    trace = [m for m in recent if m.get("metric") == "trace_faithfulness"]
    if trace:
        latest = trace[-1]
        faith = latest.get("faithfulness_score")
        fabricated = latest.get("fabricated_sources")
        file_cites = (latest.get("verified_sources", 0) or 0) + (fabricated or 0)
        if faith is not None:
            print(f"  Trace faithfulness:  {faith:.1%} ({latest.get('matched_claims', 0)} matched / {latest.get('info_claims', 0)} claims)")
        if fabricated is not None:
            print(f"  Fabricated cites:    {fabricated} of {file_cites} file citations")

    # Trend: show all pushback entries for trend direction
    if len(pushback) >= 2:
        rates = [m.get("overall_rate", 0) for m in pushback]
        if rates[-1] > rates[0]:
            trend = "improving"
        elif rates[-1] < rates[0]:
            trend = "declining"
        else:
            trend = "flat"
        print(f"  Pushback trend:     {trend} ({rates[0]:.1%} → {rates[-1]:.1%})")

    # Latest fold metrics
    if pushback:
        latest = pushback[-1]
        fold_rate = latest.get("fold_rate")
        if fold_rate is not None:
            total_p = latest.get("total_pressured", 0)
            total_f = latest.get("total_folds", 0)
            print(f"  Fold rate:          {fold_rate:.1%} ({total_f} folds of {total_p} pressured turns)")

    # Latest claims reader
    claims = [m for m in recent if m.get("metric") == "claims_reader"]
    if claims:
        latest = claims[-1]
        total = latest.get("total_claims", 0)
        vr = latest.get("verified_rate", 0)
        sr = latest.get("sourced_rate", 0)
        print(f"  Claims:             {total} total, {vr:.0%} verified, {sr:.0%} sourced")

    # Latest compaction nuance
    compaction = [m for m in recent if m.get("metric") == "compaction_nuance"]
    if compaction:
        latest = compaction[-1]
        avg_density = latest.get("avg_density")
        if avg_density is not None:
            print(f"  Compaction nuance:   {avg_density:.4f} avg density ({latest.get('low_nuance_events', 0)} low-nuance events)")
        else:
            print(f"  Compaction nuance:   {latest.get('events', 0)} events, no density data")

    # Latest calibration canary
    canary = [m for m in recent if m.get("metric") == "calibration_canary"]
    if canary:
        latest = canary[-1]
        acc = latest.get("accuracy")
        brier = latest.get("brier_score")
        consistency = latest.get("avg_consistency")
        if acc is not None and brier is not None:
            print(f"  Calibration canary:  {acc:.1%} acc / {brier:.4f} Brier / {consistency:.1%} consistency")

    print()


if __name__ == "__main__":
    main()
