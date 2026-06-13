#!/usr/bin/env python3
"""skill-usage-watch collector — deterministic half of the 2h skill-usage skim.

The original watcher was a session-scoped CronCreate loop (session 078ec1d8,
2026-06-12); it died when its host session ended, freezing the watermark with
`audited: []`. This is the durable replacement: launchd runs this script every
2h (com.agent-infra.skill-usage-watch), it queries agentlogs.db for NEW
/execute + /critique Skill invocations and queues them in the state file's
`pending` list. No LLM here — the semantic skim of pending sessions happens in
interactive sessions (two-tier: deterministic screen → semantic judge), which
move entries from `pending` to `audited`.

Watermark semantics (inherited from the cron design): new last_check =
MIN(last_success_at) over claude+codex from v_indexer_health — NEVER wall
clock, because late-indexed sessions carry historical ts_start. A 6h query
overlap + invocation-level `seen` dedup additionally covers sources deferred
by the indexer's --limit-sources batching.

State: .claude/skill-usage-watch.json (gitignored, loop-mutated).
Surfacing: one line appended to .claude/checkpoint.md when new work lands,
and a cadence-drop note when empty_streak crosses 5.

Native-First: launchd is the scheduler; the payload needs JSON state + SQL,
hence Python rather than a shell recipe.
"""
import json
import os
import sys

from common.db import open_db_ro
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(REPO, ".claude", "skill-usage-watch.json")
CHECKPOINT = os.path.join(REPO, ".claude", "checkpoint.md")
DB = os.path.expanduser("~/.claude/agentlogs.db")
SKILLS = ("execute", "critique")
OVERLAP_HOURS = 6
SEEN_PRUNE_DAYS = 7


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"last_check": (datetime.now(timezone.utc) - timedelta(hours=6))
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "empty_streak": 0, "audited": [], "pending": [], "seen": []}


def main():
    state = load_state()
    state.setdefault("pending", [])
    state.setdefault("seen", [])

    con = open_db_ro(DB)
    try:
        watermark = con.execute(
            "SELECT MIN(last_success_at) FROM v_indexer_health "
            "WHERE vendor IN ('claude','codex')").fetchone()[0]
        since = (datetime.fromisoformat(state["last_check"].replace("Z", "+00:00"))
                 - timedelta(hours=OVERLAP_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = con.execute(
            "SELECT s.project_slug, s.session_uuid, tc.ts_start, "
            "       json_extract(tc.args_json,'$.skill'), "
            "       substr(replace(json_extract(tc.args_json,'$.args'),char(10),' '),1,80) "
            "FROM tool_calls tc "
            "JOIN runs r ON r.run_id = tc.run_id "
            "JOIN sessions s ON s.session_pk = r.session_pk "
            "WHERE tc.tool_name = 'Skill' "
            f"  AND json_extract(tc.args_json,'$.skill') IN ({','.join('?' * len(SKILLS))}) "
            "  AND tc.ts_start > ? ORDER BY tc.ts_start",
            (*SKILLS, since)).fetchall()
    finally:
        con.close()

    seen = set(state["seen"])
    audited = set(state["audited"])
    fresh = []
    for project, uuid, ts, skill, args in rows:
        key = f"{uuid}|{ts}"
        if key in seen or uuid in audited:
            continue
        seen.add(key)
        fresh.append({"project": project, "session": uuid, "ts": ts,
                      "skill": skill, "args": (args or "")[:80]})

    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_PRUNE_DAYS)
              ).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["seen"] = sorted(k for k in seen if k.split("|", 1)[1] >= cutoff)

    if fresh:
        state["pending"].extend(fresh)
        state["empty_streak"] = 0
        note = (f"- [{now_iso()}] skill-usage-watch: {len(fresh)} new "
                f"execute/critique invocation(s) pending audit — see "
                f".claude/skill-usage-watch.json `pending` "
                f"({', '.join(sorted({f['project'] for f in fresh}))})\n")
        with open(CHECKPOINT, "a") as f:
            f.write(note)
    else:
        state["empty_streak"] += 1
        if state["empty_streak"] == 5:
            with open(CHECKPOINT, "a") as f:
                f.write(f"- [{now_iso()}] skill-usage-watch: 5 consecutive "
                        "empty checks — consider dropping cadence or retiring "
                        "the watcher\n")

    if watermark:
        state["last_check"] = watermark
    state["note"] = ("last_check = indexer last_success_at, NOT wall clock "
                     "(late-indexed sessions carry historical ts_start); "
                     "collector = launchd com.agent-infra.skill-usage-watch")
    with open(STATE, "w") as f:
        json.dump(state, f, indent=1)
        f.write("\n")

    print(f"[{now_iso()}] new={len(fresh)} pending={len(state['pending'])} "
          f"streak={state['empty_streak']} watermark={state['last_check']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
