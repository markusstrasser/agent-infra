#!/usr/bin/env python3
"""Feature-loop decompose-quality SHADOW probe — REPORT-ONLY.

Measures (does NOT enforce) the one UNMEASURED moment of the feature-work loop:
**decomposition quality at fan-out** (the decompose-time half). Decision:
`decisions/2026-06-16-feature-work-loop-binding-measurement-first.md`.

Per-fan-out-session (sessions.subagent_count > 1) over a window:
  1. OVERLAP — the ONE new query: files mutated (edit/write/delete) by >=2 runs in a
     session — the merge-hell predictor (prior-art: a clean decomposition means no two
     agents own the same file). Sub-split: >=2 SUBAGENT runs (parallel overlap, via
     v_run_kind) and >=2 distinct worktree cwds (cross-worktree overlap, via runs.cwd).
     Classified code-vs-record: an append-only coordination file (LOG.md / MEMORY.md /
     *.jsonl) touched by N agents is BENIGN by design, not merge-hell — dropped from the
     headline, not merge-hell (record != code).
  2. THROUGHPUT — lines per landed commit vs the 200-400 empirical reviewability band
     (CONSUMED from git_commits via the sessions join).
  3. REWORK — per-session fragility_pct = commits later fixed within 3 days
     (CONSUMED from v_session_durability — NOT recomputed).

Adds exactly ONE query (overlap); everything else reads existing agentlogs views.
Report-only: no blocking, no surface change, no writes to the DB.

Consumer = the decompose-side demand question: does CODE overlap correlate with rework?
High + correlated -> justifies a decompose-time gate (Phase 3). Near-zero -> decomposition
is already clean -> cut.

    uv run python3 scripts/feature_loop_probe.py --report --days 60
    uv run python3 scripts/feature_loop_probe.py --report --json
    from feature_loop_probe import decompose_overlap   # for gov.py
"""
# Gov-ID: probe:feature-loop-decompose
# goal: measure decomposition CODE overlap at fan-out (report-only, shadow)
# verifier: null
# blast_radius: local

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

DB = Path.home() / ".claude" / "agentlogs.db"

# Append-only coordination files: ">=2 runs touched" is benign (designed for concurrent
# append), NOT merge-hell — dropped from the headline (record != code).
_RECORD_RE = re.compile(
    r"(^|/)(LOG|MEMORY|CYCLE|MAINTAIN|TODOS?|PRIORITIES|CHANGELOG)\.md$"
    r"|improvement-log\.md$|(-|_)log\.(md|jsonl|json)$|\.jsonl$"
    r"|(^|/)agent-memory/|(^|/)\.claude/|checkpoint",
    re.I,
)
# Source code: a >=2-run overlap here is a genuine merge-hell / drift-parallel risk.
_CODE_RE = re.compile(r"\.(py|ts|tsx|js|jsx|go|rs|sql|sh|lua|rb|java|c|cc|cpp|h|hpp)$", re.I)


def _overlap_class(path: str) -> str:
    if _RECORD_RE.search(path):
        return "record"
    if _CODE_RE.search(path):
        return "code"
    return "other"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    with _conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# The ONE new query: files mutated by >=2 runs within a fan-out session.
_OVERLAP_SQL = """
WITH mut AS (
  SELECT ft.path AS path, ft.run_id AS run_id, r.session_pk AS session_pk,
         r.cwd AS cwd, COALESCE(rk.run_kind, 'main') AS run_kind
  FROM file_touches ft
  JOIN runs r       ON r.run_id = ft.run_id
  JOIN sessions s   ON s.session_pk = r.session_pk
  LEFT JOIN v_run_kind rk ON rk.run_id = ft.run_id
  WHERE ft.op IN ('edit', 'write', 'delete')
    AND s.subagent_count > 1
    AND date(s.start_ts) >= date('now', ?)
)
SELECT session_pk, path,
       COUNT(DISTINCT run_id) AS n_runs,
       COUNT(DISTINCT CASE WHEN run_kind = 'subagent' THEN run_id END) AS n_subagent_runs,
       COUNT(DISTINCT cwd) AS n_cwds
FROM mut
GROUP BY session_pk, path
HAVING COUNT(DISTINCT run_id) >= 2
ORDER BY n_runs DESC
"""

# CONSUMED: commit sizes for fan-out sessions (throughput vs the 200-400 band).
_THROUGHPUT_SQL = """
SELECT COALESCE(gc.insertions, 0) + COALESCE(gc.deletions, 0) AS churn
FROM git_commits gc
JOIN sessions s ON (gc.session_id = s.vendor_session_id OR gc.session_id = s.synthetic_session_key)
WHERE s.subagent_count > 1
  AND date(gc.authored_at) >= date('now', ?)
  AND gc.subject NOT LIKE '[wip]%'
  AND COALESCE(gc.commit_type, '') NOT IN ('wip')
"""

# CONSUMED: per-session fragility (rework) from the existing durability view.
_REWORK_SQL = """
SELECT sd.session_id, sd.commits_produced, sd.commits_later_fixed, sd.fragility_pct
FROM v_session_durability sd
JOIN sessions s ON (sd.session_id = s.vendor_session_id OR sd.session_id = s.synthetic_session_key)
WHERE s.subagent_count > 1
  AND date(s.start_ts) >= date('now', ?)
"""

_FANOUT_SESSIONS_SQL = """
SELECT COUNT(*) AS n FROM sessions
WHERE subagent_count > 1 AND date(start_ts) >= date('now', ?)
"""


def decompose_overlap(days: int = 60) -> list[dict]:
    """Files mutated by >=2 runs in a fan-out session, classified code/record/other."""
    rows = _rows(_OVERLAP_SQL, (f"-{days} days",))
    for r in rows:
        r["klass"] = _overlap_class(r["path"])
    return rows


def report(days: int = 60) -> dict:
    win = (f"-{days} days",)
    n_fanout = _rows(_FANOUT_SESSIONS_SQL, win)[0]["n"]
    overlap = decompose_overlap(days)
    code = [o for o in overlap if o["klass"] == "code"]  # real merge-hell risk (HEADLINE)
    record = [o for o in overlap if o["klass"] == "record"]  # benign concurrent append (dropped)
    code_parallel = [o for o in code if (o["n_subagent_runs"] or 0) >= 2]
    code_cross_wt = [o for o in code if (o["n_cwds"] or 0) >= 2]
    churns = sorted(r["churn"] for r in _rows(_THROUGHPUT_SQL, win))
    rework = _rows(_REWORK_SQL, win)
    median = churns[len(churns) // 2] if churns else 0
    over_400 = sum(1 for c in churns if c > 400)
    frag = [r["fragility_pct"] for r in rework if r["fragility_pct"] is not None]
    return {
        "window_days": days,
        "fanout_sessions": n_fanout,  # honest denominator
        "code_overlap": len(
            code
        ),  # HEADLINE: source files touched by >=2 runs (real conflict risk)
        "code_parallel_overlap": len(code_parallel),  # >=2 SUBAGENT runs on one source file
        "code_cross_worktree_overlap": len(code_cross_wt),  # >=2 worktrees on one source file
        "record_overlap_dropped": len(record),  # benign append files (LOG/MEMORY/.jsonl) — FP class
        "overlap_total_raw": len(overlap),
        "commits": len(churns),
        "median_commit_lines": median,
        "commits_over_400_lines": over_400,
        "pct_over_400": round(100 * over_400 / len(churns), 1) if churns else 0.0,
        "mean_session_fragility_pct": round(sum(frag) / len(frag), 1) if frag else 0.0,
        "top_code_overlap": code[:8],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=60, help="window (default 60)")
    ap.add_argument("--report", action="store_true", help="consumer summary")
    ap.add_argument("--json", action="store_true", help="JSON output")
    a = ap.parse_args()

    rep = report(a.days)
    if a.json:
        print(json.dumps(rep, indent=2))
        return 0
    print(
        f"[feature-loop] window={rep['window_days']}d  fanout_sessions={rep['fanout_sessions']}\n"
        f"  CODE overlap: {rep['code_overlap']} source file-session pairs touched by >=2 runs"
        f"  ({rep['code_parallel_overlap']} by >=2 subagents, {rep['code_cross_worktree_overlap']} cross-worktree)\n"
        f"  (record/append FPs dropped: {rep['record_overlap_dropped']}; raw total {rep['overlap_total_raw']})\n"
        f"  throughput: {rep['commits']} commits, median {rep['median_commit_lines']} lines, "
        f"{rep['commits_over_400_lines']} over 400 ({rep['pct_over_400']}%)\n"
        f"  rework: mean session fragility {rep['mean_session_fragility_pct']}%"
    )
    for o in rep["top_code_overlap"]:
        print(
            f"    · {o['path']}  ({o['n_runs']} runs, {o['n_subagent_runs']} subagent,"
            f" {o['n_cwds']} cwd) sess#{o['session_pk']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
