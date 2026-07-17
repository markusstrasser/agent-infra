#!/usr/bin/env python3
"""spend_forensics.py — monthly metered-spend compositor (no scratchpad reinvent).

Wraps the same PRICING + transport rules as usage-check.py. Answers
"why did the bill spike?" with: monthly metered USD by provider/model/repo,
subscription vs api call ratio, and pointers to spend ADRs.

Usage:
  uv run python3 scripts/spend_forensics.py [--month YYYY-MM] [--json]
  just spend-forensics [YYYY-MM]
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import pathlib
import sys
from collections import defaultdict

ADRS = [
    "decisions/2026-05-31-gemini-cli-to-paid-api-migration.md",
    "decisions/2026-07-14-gemini-critique-only-policy.md",
    "decisions-pending/2026-06-25-metered-spend-funnel-enforcement.md",
]
DEFAULT_LOG = pathlib.Path.home() / ".claude" / "llmx-usage.jsonl"
_USAGE_CHECK = pathlib.Path(__file__).resolve().parent / "usage-check.py"


def _load_usage_check():
    spec = importlib.util.spec_from_file_location("usage_check", _USAGE_CHECK)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_USAGE_CHECK}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _month_prefix(month: str | None) -> str:
    if month:
        return month
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")


def rollup(log: pathlib.Path, month: str) -> dict:
    uc = _load_usage_check()
    by_model: dict[tuple, dict] = defaultdict(
        lambda: {"calls": 0, "in_tok": 0, "out_tok": 0, "cost": 0.0}
    )
    by_repo: dict[str, dict] = defaultdict(lambda: {"calls": 0, "cost": 0.0})
    metered = {"calls": 0, "cost": 0.0}
    subscription = {"calls": 0}
    unpriced_models: set[str] = set()

    if not log.is_file():
        return {"error": f"missing log {log}", "month": month}

    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = r.get("ts") or ""
        if not ts.startswith(month):
            continue
        transport = r.get("transport")
        if not uc._is_metered(transport):
            subscription["calls"] += 1
            continue
        prov, model = r.get("provider") or "?", r.get("model") or "?"
        p_tok = r.get("prompt_tokens") or 0
        c_tok = r.get("completion_tokens") or 0
        rr_tok = r.get("reasoning_tokens") or 0
        cost = uc.estimate_cost(prov, model, p_tok, c_tok, rr_tok)
        if model and model not in uc.PRICING:
            unpriced_models.add(model)
        key = (prov, model)
        by_model[key]["calls"] += 1
        by_model[key]["in_tok"] += p_tok
        by_model[key]["out_tok"] += c_tok + rr_tok
        by_model[key]["cost"] += cost
        repo = (r.get("cwd") or "").rstrip("/").split("/")[-1] or "?"
        by_repo[repo]["calls"] += 1
        by_repo[repo]["cost"] += cost
        metered["calls"] += 1
        metered["cost"] += cost

    return {
        "month": month,
        "metered_usd": round(metered["cost"], 2),
        "metered_calls": metered["calls"],
        "subscription_calls": subscription["calls"],
        "by_model": [
            {
                "provider": k[0],
                "model": k[1],
                "calls": v["calls"],
                "in_tok": v["in_tok"],
                "out_tok": v["out_tok"],
                "cost_usd": round(v["cost"], 2),
            }
            for k, v in sorted(by_model.items(), key=lambda x: -x[1]["cost"])
        ],
        "by_repo": [
            {"repo": k, "calls": v["calls"], "cost_usd": round(v["cost"], 2)}
            for k, v in sorted(by_repo.items(), key=lambda x: -x[1]["cost"])
        ],
        "unpriced_models": sorted(unpriced_models),
        "adrs": ADRS,
        "note": "transport==api (or *-api) only for $; subscription/CLI counted separately. Unpriced models undercount.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--month", default=None, help="YYYY-MM (default: current UTC month)")
    ap.add_argument("--log", type=pathlib.Path, default=DEFAULT_LOG)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    month = _month_prefix(args.month)
    report = rollup(args.log, month)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if "error" not in report else 1
    if "error" in report:
        print(report["error"], file=sys.stderr)
        return 1
    print(f"# spend-forensics — {month}")
    print(
        f"metered: ${report['metered_usd']:.2f} ({report['metered_calls']} api calls) · "
        f"subscription/CLI calls: {report['subscription_calls']}"
    )
    print()
    print(f"{'provider':12s} {'model':28s} {'calls':6s} {'$est':8s}")
    for row in report["by_model"][:15]:
        print(
            f"{row['provider'][:12]:12s} {row['model'][:28]:28s} "
            f"{row['calls']:6d} ${row['cost_usd']:>6.2f}"
        )
    print()
    print(f"{'repo':24s} {'calls':6s} {'$est':8s}")
    for row in report["by_repo"][:12]:
        print(f"{row['repo'][:24]:24s} {row['calls']:6d} ${row['cost_usd']:>6.2f}")
    if report["unpriced_models"]:
        print(f"\n⚠ unpriced models (undercount): {', '.join(report['unpriced_models'][:8])}")
    print("\nADRs:")
    for a in report["adrs"]:
        print(f"  · {a}")
    print(f"\n{report['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
