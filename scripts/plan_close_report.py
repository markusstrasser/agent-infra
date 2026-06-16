#!/usr/bin/env python3
"""Analyze plan-close-gate shadow log — promotion readiness report.

Usage:
    just plan-close-report
    uv run python3 scripts/plan_close_report.py --days 14
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common import con

LOG = Path.home() / ".claude" / "surface-gates" / "plan-close-shadow.jsonl"


def load_records(days: int) -> list[dict]:
    if not LOG.is_file():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[dict] = []
    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = rec.get("ts", "")
        try:
            when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            when = cutoff
        if when >= cutoff:
            out.append(rec)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Plan-close shadow report")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    records = load_records(args.days)
    missing_verified = sum(
        1 for r in records if not (r.get("artifacts") or {}).get("verified_disposition")
    )
    report = {
        "log": str(LOG),
        "days": args.days,
        "total_flags": len(records),
        "missing_verified_disposition": missing_verified,
        "promotion_hint": (
            "PLAN_CLOSE_GATE=advisory" if len(records) >= 3 else "keep shadow — <3 samples"
        ),
        "records": records[-10:],
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    con.header(f"Plan-close shadow ({args.days}d)")
    if not records:
        con.ok("no flags logged")
        return 0
    con.kv("flags", str(len(records)))
    con.kv("missing verified-disposition", str(missing_verified))
    con.kv("promotion hint", report["promotion_hint"])
    for r in records[-5:]:
        arts = r.get("artifacts") or {}
        print(f"  {r.get('ts', '?')[:19]} {Path(r.get('repo_root', '?')).name} "
              f"dispatch={arts.get('dispatch_json')} verified={arts.get('verified_disposition')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
