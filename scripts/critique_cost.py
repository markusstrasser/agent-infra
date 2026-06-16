#!/usr/bin/env python3
"""Summarize external API token usage from .model-review/*.meta.json files.

Usage:
  critique_cost.py              # all projects, last 30 days
  critique_cost.py --days 7
  critique_cost.py --project genomics
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECTS = Path.home() / "Projects"

# Rough $/M (input, output) for cost display — subscription sessions may be $0 marginal.
RATES = {
    "deep_review": (0.50, 2.50),      # gemini-3.5-flash order of magnitude
    "gpt_general": (0.50, 2.50),      # gpt-5.5 via codex/api
    "formal_review": (0.50, 2.50),
    "mechanical_review": (0.50, 2.50),
    "fast_extract": (0.10, 0.40),
    "composer_review": (0.50, 2.50),
    "composer_screen": (3.00, 15.00),
    "claude_review": (15.0, 75.0),
    "unknown": (1.0, 5.0),
}


def _usage(meta: dict) -> tuple[int, int]:
    u = meta.get("usage") or {}
    inp = u.get("prompt_tokens") or u.get("inputTokens") or 0
    out = u.get("completion_tokens") or u.get("outputTokens") or 0
    return int(inp), int(out)


def _mtime_days(path: Path) -> float:
    return (datetime.now(timezone.utc) - datetime.fromtimestamp(
        path.stat().st_mtime, tz=timezone.utc
    )).total_seconds() / 86400


def _cost(profile: str, inp: int, out: int) -> float:
    rin, rout = RATES.get(profile, RATES["unknown"])
    return inp / 1e6 * rin + out / 1e6 * rout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--project", help="Limit to one project dir name")
    args = ap.parse_args()

    roots = [PROJECTS / args.project] if args.project else [
        p for p in PROJECTS.iterdir() if p.is_dir()
    ]

    by_profile: dict[str, dict] = defaultdict(lambda: {"n": 0, "in": 0, "out": 0, "usd": 0.0})
    by_review: dict[str, dict] = defaultdict(lambda: {"axes": 0, "in": 0, "out": 0, "usd": 0.0})
    skipped = 0

    for root in roots:
        for meta_path in root.glob(".model-review/**/*.meta.json"):
            if _mtime_days(meta_path) > args.days:
                continue
            try:
                meta = json.loads(meta_path.read_text())
            except (json.JSONDecodeError, OSError):
                skipped += 1
                continue
            inp, out = _usage(meta)
            if inp + out < 50:
                continue
            profile = meta.get("requested_profile") or meta.get("profile") or "unknown"
            usd = _cost(profile, inp, out)
            by_profile[profile]["n"] += 1
            by_profile[profile]["in"] += inp
            by_profile[profile]["out"] += out
            by_profile[profile]["usd"] += usd

            review_key = f"{root.name}/{meta_path.parent.name}"
            by_review[review_key]["axes"] += 1
            by_review[review_key]["in"] += inp
            by_review[review_key]["out"] += out
            by_review[review_key]["usd"] += usd

    total_usd = sum(v["usd"] for v in by_profile.values())
    total_calls = sum(v["n"] for v in by_profile.values())
    packets = [v for v in by_review.values() if v["axes"] >= 2]

    print(f"# Critique external cost (meta.json, last {args.days}d)")
    if args.project:
        print(f"  project: {args.project}")
    print(f"  axis dispatches: {total_calls}  review packets (≥2 axes): {len(packets)}")
    print(f"  est external USD: ${total_usd:,.2f}  (API-rate proxy; subscription may differ)")
    if skipped:
        print(f"  skipped unreadable: {skipped}")

    print("\n## By profile")
    for prof, v in sorted(by_profile.items(), key=lambda x: -x[1]["usd"]):
        avg_in = v["in"] / v["n"] if v["n"] else 0
        avg_out = v["out"] / v["n"] if v["n"] else 0
        print(f"  {prof:22} n={v['n']:4}  avg_in={avg_in:,.0f}  avg_out={avg_out:,.0f}  ${v['usd']:.2f}")

    if packets:
        totals = sorted(v["usd"] for v in packets)
        p50 = totals[len(totals) // 2]
        print(f"\n## Per review packet (≥2 axes, n={len(packets)})")
        print(f"  USD p50=${p50:.2f}  mean=${sum(totals)/len(totals):.2f}  max=${max(totals):.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
