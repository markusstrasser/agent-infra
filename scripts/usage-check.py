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


# PRICING — VENDORED copy of llmx/llmx/usage_report.py:PRICING (the single source).
# agent-infra can't import llmx (separate env), so this exact-model map is vendored
# behind a drift-test — tests/test_usage_check_pricing_drift.py AST-parses the llmx
# source and asserts equality, so the two can't silently diverge (epistemic-discipline
# invariant #9). Edit rates in llmx; then sync here or the drift-test fails loudly.
# Per-MTok (input, output); output rate also applies to reasoning tokens. Exact model
# keys (NOT prefixes) — an unpriced model returns None (surfaces as $0, never guessed).
PRICING: dict[str, tuple[float, float]] = {
    "gemini-3-flash-preview": (0.075, 0.30),
    "gemini-3-flash": (0.075, 0.30),
    "gemini-3.1-flash-lite-preview": (0.05, 0.20),
    "gemini-3.5-flash": (1.50, 9.0),
    "gemini-3.1-pro-preview": (1.25, 10.0),
    # GPT-5.6 suite (developers.openai.com/api/docs/pricing, GA 2026-07-09)
    # Standard short-context: Sol $5/$30, Terra $2.50/$15, Luna $1/$6.
    # Alias gpt-5.6 → sol. Pro mode bills at same model rates (more tokens).
    "gpt-5.6-sol": (5.0, 30.0),
    "gpt-5.6": (5.0, 30.0),
    "gpt-5.6-terra": (2.50, 15.0),
    "gpt-5.6-luna": (1.0, 6.0),
    "gpt-5.3-chat-latest": (1.75, 14.0),
    "gpt-5.3-codex": (1.25, 10.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-fable-5": (10.0, 50.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    # SpaceXAI Grok 4.5 (docs.x.ai 2026-07-08): base $2/$6; Cursor fast variant $4/$18
    "grok-4.5": (2.0, 6.0),
    "grok-4.5-medium": (2.0, 6.0),
    "grok-4.5-high": (2.0, 6.0),
    "grok-4.5-xhigh": (2.0, 6.0),
    "grok-4.5-fast-medium": (4.0, 18.0),
    "grok-4.5-fast-high": (4.0, 18.0),
    "grok-4.5-fast-xhigh": (4.0, 18.0),
    # openrouter (verified live 2026-07-07: /api/v1/models pricing.prompt/completion)
    "qwen/qwen3.6-27b": (0.285, 2.40),
}


def _is_metered(transport) -> bool:
    """True iff genuinely billed (per-token API). Metered rows: `api` + `*-api`
    (e.g. `agent-api` = perplexity research). Subscription/CLI (`claude-cli`,
    `codex-cli`) are $0. Mirrors llmx spend_guard.is_metered_transport."""
    return bool(transport) and (transport == "api" or transport.endswith("-api"))


def est_cost(model: str, prompt_tok: int, out_tok: int):
    """Exact-model cost estimate, or None if the model is unpriced."""
    rate = PRICING.get(model or "")
    if rate is None:
        return None
    return (prompt_tok * rate[0] + out_tok * rate[1]) / 1_000_000


def estimate_cost(provider: str, model: str, prompt_tok: int, completion_tok: int, reasoning_tok: int = 0) -> float:
    """Best-effort cost estimate. Reasoning tokens billed as output. Unpriced → $0
    (undercount rather than guess). `provider` kept for call-site compatibility;
    pricing is model-keyed via the single-sourced PRICING map."""
    out_tok = completion_tok + (reasoning_tok or 0)
    return est_cost(model, prompt_tok, out_tok) or 0.0


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
        if not _is_metered(r.get("transport")):  # subscription/CLI = $0; only billed rows count
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
