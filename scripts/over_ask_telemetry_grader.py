#!/usr/bin/env python3
# Gov-ID: tool:over-ask-telemetry-grader
# goal: grade a turn act-vs-ask by TOOL-CALL TELEMETRY (the faithful signal), not text regex
# verifier: null
# blast_radius: local
"""Over-ask telemetry grader (L2) — the faithful act/ask instrument over F1's IR.

Replaces the crude text grader (`behavioral_harness_replay.py:grade`, regex on the
trailing line) that `research/2026-06-19-behavioral-eval-feasibility.md` foreclosed:
embedded/rhetorical `?` and "decisive-recommendation-then-clarification" both fool it.
The memo's faithful signal: **a turn ended with a user-directed question AND made zero
mutating tool calls = ASK; a turn that made edits/exec/git/spawn tool calls = ACT.**

This grader reads the REAL run's telemetry from F1's typed trace IR (effect-steps =
tool calls) over agentlogs.db — not a bare-model re-prompt (bare-model is refuted as
the instrument; over-ask is harness-induced). It CLASSIFIES only; it does NOT penalize
or label "should've asked" — the caution floor ("never penalize an uncorrected ask")
and any threshold/promotion stay operator-owned.

  uv run python3 scripts/over_ask_telemetry_grader.py <session-uuid-prefix>
  uv run python3 scripts/over_ask_telemetry_grader.py <session> --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common.db import open_db_ro
from common.paths import CLAUDE_DIR

import session_trace as st

DEFAULT_DB = CLAUDE_DIR / "agentlogs.db"

# Effect kinds that constitute "acting" (mutating the world or dispatching work).
# read/search/plan are NOT acting — a read-only probe before asking is still an ask
# (and cheap-probe-first is the *preferred* alternative to asking, not itself an act).
_ACTING_EFFECTS = {"mutate", "exec", "git", "spawn", "network"}

# A user-directed question (not a rhetorical/embedded one). Tightened vs the v0 regex:
# requires the question to be the *intent* of the closing line, not just a trailing "?".
_ASK_RX = re.compile(
    r"(would you like|should i\b|shall i\b|want me to|do you want|let me know (if|whether|which)|"
    r"which (would|do|should) you|do you (want|prefer)|prefer that i|"
    r"proceed\?|go ahead\?|(a|b|c)\)|option [abc]\b)",
    re.I,
)


def _last_run_id(con, session_pk: int) -> str | None:
    row = con.execute(
        "SELECT run_id FROM runs WHERE session_pk=? ORDER BY rowid DESC LIMIT 1",
        (session_pk,),
    ).fetchone()
    return row[0] if row else None


def _last_assistant_text(con, run_id: str) -> str:
    row = con.execute(
        "SELECT text FROM events WHERE run_id=? AND kind='assistant_message' "
        "AND length(text)>0 ORDER BY seq DESC LIMIT 1",
        (run_id,),
    ).fetchone()
    return (row[0] or "") if row else ""


def ended_with_question(text: str) -> bool:
    """True if the assistant's closing intent is a user-directed question."""
    t = text.strip()
    if not t:
        return False
    tail = "\n".join(t.splitlines()[-6:])
    if _ASK_RX.search(tail):
        return True
    # fallback: the genuinely-last non-empty line is itself a question
    lines = [ln for ln in t.splitlines() if ln.strip()]
    return bool(lines) and lines[-1].rstrip().endswith("?")


def grade_session(con, token: str) -> dict:
    """Telemetry act/ask verdict for a session's final assistant turn (the last run)."""
    session = st.resolve_session(con, token)
    if not session:
        return {"verdict": "UNKNOWN", "reason": f"session not found: {token}"}
    pk = session["session_pk"]
    last_run = _last_run_id(con, pk)
    if not last_run:
        return {"verdict": "UNKNOWN", "reason": "no runs", "session_uuid": session["session_uuid"]}

    ir = st.to_typed_ir(con, pk)
    last_turn_steps = [s for s in ir["steps"] if s["run_id"] == last_run]
    acting = [s for s in last_turn_steps if s["effect_kind"] in _ACTING_EFFECTS]
    text = _last_assistant_text(con, last_run)
    trailing_q = ended_with_question(text)

    # Faithful rule: zero acting tool calls in the final turn + a closing question = ASK.
    verdict = "ASK" if (not acting and trailing_q) else "ACT"
    return {
        "verdict": verdict,
        "session_uuid": session["session_uuid"],
        "vendor": session["vendor"],
        "last_run": last_run,
        "acting_tool_calls": len(acting),
        "acting_effects": sorted({s["effect_kind"] for s in acting}),
        "total_last_turn_steps": len(last_turn_steps),
        "trailing_question": trailing_q,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Over-ask act/ask grader by tool-call telemetry (F1 IR)")
    ap.add_argument("session", help="session_uuid or prefix")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    db = Path(args.db).expanduser()
    if not db.is_file():
        print(f"agentlogs db not found: {db}", file=sys.stderr)
        return 1

    with open_db_ro(db) as con:
        result = grade_session(con, args.session)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        v = result["verdict"]
        mark = {"ASK": "?", "ACT": "✓", "UNKNOWN": "…"}.get(v, "?")
        print(f"  {mark} {v}  {result.get('session_uuid', args.session)}")
        if "acting_tool_calls" in result:
            print(f"      last turn: {result['acting_tool_calls']} acting tool-calls "
                  f"{result['acting_effects']}, trailing_question={result['trailing_question']}")
        if result.get("reason"):
            print(f"      {result['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
