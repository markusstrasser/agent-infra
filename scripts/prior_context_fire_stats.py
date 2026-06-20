#!/usr/bin/env python3
"""Measure prior-context hook fire rate vs blindspot/triage flags."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prior_context_triage import from_db

TRIGGERS = Path.home() / ".claude/hook-triggers.jsonl"


def hook_fires(since: str) -> list[dict]:
    if not TRIGGERS.is_file():
        return []
    out: list[dict] = []
    for line in TRIGGERS.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get("hook") != "prior-context":
            continue
        ts = row.get("ts") or ""
        if ts < since:
            continue
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None, help="ISO date (default: 7d ago)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.since:
        since = args.since
    else:
        since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    fires = hook_fires(since)
    flags = from_db(since)
    by_project = Counter(r.get("project") or "?" for r in fires)
    summary = {
        "since": since,
        "hook_fires": len(fires),
        "triage_flags": len(flags),
        "fires_per_flag": round(len(fires) / max(len(flags), 1), 3),
        "fires_by_project": dict(by_project.most_common()),
        "interpretation": (
            "fires on UserPromptSubmit (preventive); triage_flags are post-hoc corrections — "
            "target fires_per_flag rising on propose/diagnose prompts, not 1:1 parity"
        ),
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Prior-context fire stats since {since}")
        print(f"  hook_fires: {len(fires)}")
        print(f"  triage_flags: {len(flags)}")
        print(f"  fires/flag: {summary['fires_per_flag']}")
        for proj, n in by_project.most_common(8):
            print(f"    {proj}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
