#!/usr/bin/env python3
"""Triage post-deploy prior-context blindspot flags (A5 prerequisite).

Reads blindspot miner output / agentlogs for GROW_COVERAGE flags since a date,
classifies residual misses into buckets for v2 targeting.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

DB = Path.home() / ".claude/agentlogs.db"
SINCE_DEFAULT = "2026-06-14"

BUCKETS = {
    "sibling_repo": re.compile(r"sibling|other repo|genomics/|personal/|phenome/|inside Projects/", re.I),
    "observe_rsi": re.compile(r"observe|agentlogs|blindspot|system\?|part of observe", re.I),
    "git_history": re.compile(r"git log|commit history|discussed before|did we already", re.I),
    "research_memo": re.compile(r"read the (full )?paper|research memo|/research", re.I),
    "cursor_gap": re.compile(r"cursor|composer", re.I),
    "existing_infra": re.compile(r"already exist|schema|view|just recipe|hook", re.I),
}


def classify(text: str) -> list[str]:
    hits = [name for name, rx in BUCKETS.items() if rx.search(text)]
    return hits or ["other"]


def from_db(since: str, limit: int = 500) -> list[dict]:
    if not DB.is_file():
        return []
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT e.ts, s.project_slug, s.session_uuid, substr(e.text, 1, 500) AS text
        FROM events e
        JOIN runs r ON e.run_id = r.run_id
        JOIN sessions s ON r.session_pk = s.session_pk
        WHERE e.role = 'user' AND e.ts >= ? AND length(e.text) > 20
        ORDER BY e.ts DESC
        LIMIT ?
        """,
        (since, limit),
    ).fetchall()
    con.close()
    out = []
    for r in rows:
        t = r["text"] or ""
        if not re.search(r"\b(why|check|did you|already|before|forget|miss)\b", t, re.I):
            continue
        buckets = classify(t)
        if "other" in buckets and len(buckets) == 1:
            continue
        proj = r["project_slug"] or "?"
        out.append({
            "ts": r["ts"],
            "project": proj,
            "session_id": (r["session_uuid"] or "")[:8],
            "buckets": buckets,
            "excerpt": t[:120].replace("\n", " "),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=SINCE_DEFAULT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    flags = from_db(args.since)
    bucket_counts: Counter[str] = Counter()
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    sessions: set[str] = set()

    for f in flags:
        sessions.add(f["session_id"])
        for b in f["buckets"]:
            bucket_counts[b] += 1
            if len(by_bucket[b]) < 5:
                by_bucket[b].append(f)

    summary = {
        "since": args.since,
        "flags": len(flags),
        "distinct_sessions": len(sessions),
        "bucket_counts": dict(bucket_counts.most_common()),
        "samples": {k: v for k, v in by_bucket.items()},
        "recommendation": (
            "Ship v2 slice matching top bucket first "
            f"({bucket_counts.most_common(1)[0][0] if bucket_counts else 'n/a'})"
        ),
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Prior-context triage since {args.since}")
        print(f"  flags: {len(flags)}  sessions: {len(sessions)}")
        for name, n in bucket_counts.most_common():
            print(f"  {name}: {n}")
        print(f"  → {summary['recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
