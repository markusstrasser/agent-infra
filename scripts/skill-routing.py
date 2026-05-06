#!/usr/bin/env python3
"""Classify Skill tool invocations as user-slash vs model-proactive.

Reads agentlogs.db. For each Skill tool_call, looks at the most recent
preceding user_message in the same run; if it starts with /skillname
(possibly after preamble/newlines), it's user-slash; otherwise proactive.

Use to validate skillOverrides decisions: a skill with N>0 proactive
invocations should not be set to user-invocable-only.

Usage:
    uv run python3 scripts/skill-routing.py [--days N] [--skill NAME]
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DB = Path.home() / ".claude" / "agentlogs.db"

QUERY = """
WITH skill_calls AS (
  SELECT
    e.run_id,
    e.seq AS skill_seq,
    e.ts,
    json_extract(tc.args_json, '$.skill') AS skill
  FROM tool_calls tc
  JOIN events e ON e.tool_call_id = tc.tool_call_id AND e.kind='tool_call'
  WHERE tc.tool_name='Skill' AND tc.ts_start > ?
),
classified AS (
  SELECT
    sc.skill,
    sc.run_id,
    sc.skill_seq,
    (SELECT e2.text FROM events e2
     WHERE e2.run_id = sc.run_id AND e2.seq < sc.skill_seq AND e2.kind = 'user_message'
     ORDER BY e2.seq DESC LIMIT 1) AS user_text
  FROM skill_calls sc
  WHERE sc.skill IS NOT NULL
)
SELECT
  skill,
  CASE
    WHEN user_text LIKE '/' || skill || '%'
      OR user_text LIKE '%' || char(10) || '/' || skill || '%'
    THEN 'user-slash'
    ELSE 'proactive'
  END AS trigger,
  COUNT(*) AS n
FROM classified
GROUP BY skill, trigger
ORDER BY skill, trigger;
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--skill", help="Filter to one skill name")
    ap.add_argument("--db", default=str(DB))
    args = ap.parse_args()

    cutoff = f"date('now', '-{args.days} days')"
    conn = sqlite3.connect(args.db)
    cur = conn.execute(f"SELECT {cutoff}").fetchone()[0]
    rows = conn.execute(QUERY, (cur,)).fetchall()

    by_skill: dict[str, dict[str, int]] = {}
    for skill, trigger, n in rows:
        if args.skill and skill != args.skill:
            continue
        by_skill.setdefault(skill, {})[trigger] = n

    if not by_skill:
        print("No skill invocations found in window.")
        return 0

    rows_out = []
    for skill, counts in by_skill.items():
        proactive = counts.get("proactive", 0)
        user = counts.get("user-slash", 0)
        total = proactive + user
        rows_out.append((skill, proactive, user, total))
    rows_out.sort(key=lambda r: -r[3])

    print(f"{'skill':<40} {'proactive':>10} {'user-/':>8} {'total':>8}  signal")
    print("-" * 80)
    for skill, p, u, t in rows_out:
        if t == 0:
            sig = ""
        elif p == 0:
            sig = "user-only — candidate user-invocable-only"
        elif u == 0:
            sig = "model-only — keep on"
        else:
            sig = f"mixed ({p}/{u})"
        print(f"{skill:<40} {p:>10} {u:>8} {t:>8}  {sig}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
