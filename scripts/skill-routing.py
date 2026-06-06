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
import json
import re
import sqlite3
from pathlib import Path

from common.skill_objects import collect_skill_objects, iter_default_roots

DB = Path.home() / ".claude" / "agentlogs.db"
DEFAULT_CASES = Path("schemas/skill-routing-cases.json")

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
    ap.add_argument("--cases", type=Path, help="Run deterministic routing fixture cases")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.cases:
        return run_cases(args.cases, json_output=args.json)

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


def _terms(text: str) -> set[str]:
    raw = re.findall(r"[a-z0-9]+", text.lower())
    terms = {t for t in raw if len(t) >= 3}
    terms.update(f"{a}{b}" for a, b in zip(raw, raw[1:]) if len(a) + len(b) >= 3)
    return terms


def _score(prompt: str, row: dict) -> int:
    prompt_terms = _terms(prompt)
    name_terms = _terms(str(row.get("name") or "").replace("-", " "))
    haystack = " ".join(
        str(row.get(key) or "")
        for key in ("object_id", "name", "description", "primary_category", "notes")
    )
    row_terms = _terms(haystack)
    score = len(prompt_terms & row_terms)
    score += 3 * len(prompt_terms & name_terms)
    name = str(row.get("name") or "").replace("-", " ").lower()
    if name and name in prompt.lower():
        score += 5
    return score


def run_cases(cases_path: Path, *, json_output: bool = False) -> int:
    cases = json.loads(cases_path.read_text())
    rows = [obj.to_json() for obj in collect_skill_objects(iter_default_roots(None))]
    results = []
    for case in cases:
        project = case.get("project")
        candidates = [row for row in rows if row.get("project") == project]
        ranked = sorted(
            ((row["object_id"], _score(case["prompt"], row)) for row in candidates),
            key=lambda item: item[1],
            reverse=True,
        )
        top = [object_id for object_id, score in ranked[:5] if score > 0]
        expected = set(case["expected"])
        passed = bool(top and top[0] in expected)
        results.append({
            "id": case["id"],
            "prompt": case["prompt"],
            "expected": case["expected"],
            "top": top,
            "passed": passed,
        })

    if json_output:
        print(json.dumps({"cases": results}, indent=2))
    else:
        for result in results:
            status = "PASS" if result["passed"] else "FAIL"
            print(f"{status} {result['id']}: top={result['top']} expected={result['expected']}")
    return 1 if any(not result["passed"] for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
