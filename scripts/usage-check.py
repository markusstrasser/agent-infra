#!/usr/bin/env python3
"""Session cost meter — reads ~/.claude/llmx-usage.jsonl and reports.

Default: last 6 hours grouped by (provider, model) with token counts and
estimated cost. Optional --since "2026-05-19T08:00" for explicit window.
Optional --json for machine-readable output.

Use mid-session to answer "are we approaching the cap?" without re-deriving
from chat logs. Per-call records are appended by llmx automatically; nothing
else to wire up.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys
from collections import defaultdict


# Rough per-million-token rates (USD) for the providers that actually appear
# in the log. Approximate — for cap-monitoring not invoicing.
RATES = {
    # (provider, prefix): (input $/M, output $/M)
    ("anthropic", "claude-opus-4"): (15.0, 75.0),
    ("anthropic", "claude-sonnet-4"): (3.0, 15.0),
    ("anthropic", "claude-haiku-4"): (1.0, 5.0),
    ("openai", "gpt-5"): (5.0, 15.0),
    ("openai", "gpt-4"): (2.5, 10.0),
    ("openai", "o3"): (5.0, 20.0),
    ("google", "gemini-3.1-pro"): (1.25, 10.0),
    ("google", "gemini-3-pro"): (1.25, 10.0),
    ("google", "gemini-3-flash"): (0.075, 0.30),
    ("google", "gemini-2.5"): (0.30, 2.50),
    ("perplexity", "sonar-pro"): (3.0, 15.0),
    ("perplexity", "sonar"): (1.0, 1.0),
    ("xai", "grok"): (5.0, 15.0),
}


def estimate_cost(provider: str, model: str, prompt_tok: int, completion_tok: int, reasoning_tok: int = 0) -> float:
    """Best-effort cost estimate. Reasoning tokens billed as output."""
    if not model:
        return 0.0
    out_tok = completion_tok + (reasoning_tok or 0)
    for (p, prefix), (in_rate, out_rate) in RATES.items():
        if provider == p and model.startswith(prefix):
            return (prompt_tok * in_rate + out_tok * out_rate) / 1_000_000
    return 0.0  # unknown — undercount rather than guess


def metered_today(args) -> None:
    """Today's genuinely-billed spend over the funnel ledger, grouped by spender.

    Only `transport == "api"` rows are metered — subscription/CLI transports are $0
    and are excluded (the default report over-counts them by pricing tokens regardless
    of transport; for cap-enforcement only the billed rows matter). This is the
    observability half of the $70-silent-spend backstop (improvement-log 2026-06-25):
    a backgrounded worker's metered escalation is invisible to the foreground-Bash
    cost-guard but lands in this ledger like every other llmx call.
    """
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    by_spender: dict[tuple, dict] = defaultdict(lambda: {"calls": 0, "in_tok": 0, "out_tok": 0, "cost": 0.0})
    total = {"calls": 0, "in_tok": 0, "out_tok": 0, "cost": 0.0}
    for line in args.log.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not (r.get("ts", "") or "").startswith(today):
            continue
        if r.get("transport") != "api":  # subscription/CLI = $0; only billed rows count
            continue
        prov, model = r.get("provider", "?"), r.get("model", "?")
        p_tok = r.get("prompt_tokens") or 0
        out_tok = (r.get("completion_tokens") or 0) + (r.get("reasoning_tokens") or 0)
        cost = estimate_cost(prov, model, p_tok, r.get("completion_tokens") or 0, r.get("reasoning_tokens") or 0)
        repo = (r.get("cwd", "") or "").rstrip("/").split("/")[-1] or "?"
        key = (r.get("caller") or "?", repo)
        for d in (by_spender[key], total):
            d["calls"] += 1
            d["in_tok"] += p_tok
            d["out_tok"] += out_tok
            d["cost"] += cost

    alarm = args.alarm is not None and total["cost"] >= args.alarm
    if args.json:
        print(json.dumps({
            "date": today,
            "metered_total_usd": round(total["cost"], 2),
            "metered_calls": total["calls"],
            "alarm_threshold_usd": args.alarm,
            "alarm": alarm,
            "by_spender": [{"caller": k[0], "repo": k[1], **{kk: (round(vv, 4) if kk == "cost" else vv) for kk, vv in v.items()}}
                           for k, v in sorted(by_spender.items(), key=lambda x: -x[1]["cost"])],
            "note": "transport==api only; cost is an estimate from approximate per-M rates (undercounts unpriced models).",
        }, indent=2))
    else:
        print(f"# llmx metered spend (transport==api) — {today} ({total['calls']} billed calls)")
        print(f"{'caller':22s} {'repo':18s} {'calls':6s} {'$est':8s}")
        for k, v in sorted(by_spender.items(), key=lambda x: -x[1]["cost"]):
            print(f"{k[0][:22]:22s} {k[1][:18]:18s} {v['calls']:6d} ${v['cost']:>6.2f}")
        print("-" * 60)
        print(f"{'TOTAL':47s} ${total['cost']:>6.2f}" + (f"  ⚠ ALARM ≥ ${args.alarm}" if alarm else ""))
        print("Note: estimate; transport==api only (subscription/CLI = $0, excluded).")
    sys.exit(1 if alarm else 0)


def main():
    parser = argparse.ArgumentParser(description="Session cost meter (llmx-usage.jsonl).")
    parser.add_argument("--hours", type=float, default=6.0, help="Window in hours (default 6).")
    parser.add_argument("--since", type=str, default=None, help="ISO timestamp lower bound (overrides --hours).")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output.")
    parser.add_argument("--log", type=pathlib.Path, default=pathlib.Path.home() / ".claude" / "llmx-usage.jsonl")
    parser.add_argument("--metered-today", action="store_true",
                        help="Only today's genuinely-billed (transport==api) spend, grouped by (caller, cwd). "
                             "This is the surface-agnostic funnel: every llmx call — foreground Bash, backgrounded "
                             "worker, or Python subprocess — appends here, so background/pipeline spend the "
                             "foreground-Bash cost-guard cannot see surfaces here. Exits 1 if --alarm exceeded.")
    parser.add_argument("--alarm", type=float, default=None,
                        help="With --metered-today: exit 1 if today's metered spend (USD) >= this. For doctor/sweep alarms.")
    args = parser.parse_args()

    if not args.log.exists():
        print(f"No usage log at {args.log}", file=sys.stderr)
        sys.exit(1)

    if args.metered_today:
        return metered_today(args)

    now = dt.datetime.now(dt.timezone.utc)
    if args.since:
        cutoff = dt.datetime.fromisoformat(args.since.replace("Z", "+00:00"))
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=dt.timezone.utc)
    else:
        cutoff = now - dt.timedelta(hours=args.hours)

    rows = []
    for line in args.log.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = r.get("ts")
        if not ts:
            continue
        try:
            t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if t < cutoff:
            continue
        rows.append(r)

    by_key = defaultdict(lambda: {"calls": 0, "prompt_tok": 0, "completion_tok": 0, "reasoning_tok": 0, "cost": 0.0})
    total = {"calls": 0, "prompt_tok": 0, "completion_tok": 0, "reasoning_tok": 0, "cost": 0.0}
    for r in rows:
        prov = r.get("provider", "?")
        model = r.get("model", "?")
        p_tok = r.get("prompt_tokens") or 0
        c_tok = r.get("completion_tokens") or 0
        rr_tok = r.get("reasoning_tokens") or 0
        cost = estimate_cost(prov, model, p_tok, c_tok, rr_tok)
        key = (prov, model)
        by_key[key]["calls"] += 1
        by_key[key]["prompt_tok"] += p_tok
        by_key[key]["completion_tok"] += c_tok
        by_key[key]["reasoning_tok"] += rr_tok
        by_key[key]["cost"] += cost
        total["calls"] += 1
        total["prompt_tok"] += p_tok
        total["completion_tok"] += c_tok
        total["reasoning_tok"] += rr_tok
        total["cost"] += cost

    if args.json:
        out = {
            "window": {"since": cutoff.isoformat(), "now": now.isoformat(), "hours": (now - cutoff).total_seconds() / 3600},
            "by_model": [{"provider": k[0], "model": k[1], **v} for k, v in sorted(by_key.items(), key=lambda x: -x[1]["cost"])],
            "total": total,
            "note": "Cost is an estimate from approximate per-million rates; CLI-transport calls (Gemini) have null tokens and contribute $0.",
        }
        print(json.dumps(out, indent=2))
        return

    print(f"# llmx usage — last {(now - cutoff).total_seconds() / 3600:.1f}h ({len(rows)} calls)")
    print()
    print(f"{'provider':10s} {'model':28s} {'calls':6s} {'in_tok':10s} {'out_tok':10s} {'$est':8s}")
    for k, v in sorted(by_key.items(), key=lambda x: -x[1]["cost"]):
        print(f"{k[0]:10s} {k[1][:28]:28s} {v['calls']:6d} {v['prompt_tok']:>10,} {v['completion_tok'] + v['reasoning_tok']:>10,} ${v['cost']:>6.2f}")
    print(f"{'-' * 80}")
    print(f"{'TOTAL':39s} {total['calls']:6d} {total['prompt_tok']:>10,} {total['completion_tok'] + total['reasoning_tok']:>10,} ${total['cost']:>6.2f}")
    print()
    print("Note: estimate from approximate per-M rates; CLI-transport calls (Gemini CLI) log null tokens.")


if __name__ == "__main__":
    main()
