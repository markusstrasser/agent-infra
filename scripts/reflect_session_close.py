#!/usr/bin/env python3
"""reflect_session_close.py — async Tier 1 digest for goal-gated RSI session close.

Reads pending entries from ~/.claude/close-queue/, builds episode-bounded digests,
writes ~/.claude/reflect-close-digest.jsonl. Invoked from SessionStart drain hook
or manually. No LLM — digest is structured facts for /rsi close skill.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from goal_state import (  # noqa: E402
    slice_transcript_to_episode,
    tier1_eligible,
)
from reflect_capture import (  # noqa: E402
    extract_corrections,
    extract_operator_dx_interventions,
    parse_events,
    real_issue_signal,
)

CLOSE_QUEUE = Path.home() / ".claude" / "close-queue"
DIGEST_LOG = Path.home() / ".claude" / "reflect-close-digest.jsonl"

# Projects with loop/hindsight_grades.jsonl (HINDSIGHT Mode 3 bridge).
_HINDSIGHT_GRADES: dict[str, Path] = {
    "arc-agi": Path.home() / "Projects" / "arc-agi" / "loop" / "hindsight_grades.jsonl",
}
_VALID_HINDSIGHT_GRADES = frozenset({"DERIVABLE", "NON-DERIVABLE", "HAD-LEVER", "HAD-PARTS", "NOVEL"})
CAPTURE_LOG = Path.home() / ".claude" / "reflect-capture.jsonl"
UNSUPPORTED_SHADOW = Path.home() / ".claude" / "unsupported-completion-shadow.jsonl"
MAINTAIN = REPO / "MAINTAIN.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def _session_corrections(session_id: str) -> list[dict]:
    if not CAPTURE_LOG.exists():
        return []
    rows: list[dict] = []
    for line in CAPTURE_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if row.get("session") == session_id and row.get("kind") == "correction":
            rows.append(row)
    return rows


def _unsupported_completion(session_id: str) -> dict | None:
    """Latest unsupported-completion shadow fire for this session (claimed success w/o evidence).

    A real fabrication-risk signal — the highest-value thing a verify-close can catch. Returns the
    row (success_hits/evidence_hits/msg_tail) when present, else None. Written by
    stop-unsupported-completion.sh; absent file → None (fail open)."""
    if not UNSUPPORTED_SHADOW.exists():
        return None
    found: dict | None = None
    for line in UNSUPPORTED_SHADOW.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if row.get("session") == session_id:
            found = row  # latest wins
    return found


def build_digest(intent: dict) -> dict | None:
    """Build digest from a close-queue intent row. Returns None if not eligible."""
    session_id = intent.get("session_id", "unknown")
    goal_state = intent.get("goal_state") or {}
    corrects = _session_corrections(session_id)

    # Gate on a REAL empirical issue (single-source predicate) — cheap, no transcript read.
    real_issue, kinds = real_issue_signal(corrects)
    uc = _unsupported_completion(session_id)
    if uc and uc.get("would_fire"):
        real_issue = True
        kinds = sorted(set(kinds) | {"unsupported_completion"})

    eligible, reason = tier1_eligible(goal_state, real_issue=real_issue)
    if not eligible and not intent.get("force_tier1"):
        return None

    transcript_path = intent.get("transcript_path") or ""
    lines: list[str] = []
    if transcript_path and Path(transcript_path).exists():
        lines = Path(transcript_path).read_text(encoding="utf-8", errors="replace").splitlines()

    episode_lines = slice_transcript_to_episode(lines, goal_state.get("evidence_ts"))
    events = parse_events(episode_lines)
    inline_corrects = extract_corrections(events)
    fail_then_user = sum(
        1 for r in (*corrects, *inline_corrects) if r.get("subtype") == "fail_then_user"
    )

    # Point the verify at the SPECIFIC issue — solid info, not a generic nudge.
    if "unsupported_completion" in kinds:
        hint = (
            "FABRICATION RISK: session claimed success without an evidence marker. Re-run the "
            "claimed-successful command and confirm the outcome BEFORE attaching evidence."
        )
    elif "user_rescued_failure" in kinds:
        hint = (
            "The agent failed and the operator had to step in. Verify the fix actually landed "
            "(test exit / gate output / artifact hash) — don't trust the recovery narration."
        )
    elif "operator_dx" in kinds:
        hint = (
            "OPERATOR DX/RSI INTERVENTION: fill operator_dx_reflex fields "
            "(operator_added_value, miss_class, would_have_prevented, action_taken) — "
            "max one action (local fix | steward proposal | explicit noop)."
        )
    elif reason == "goal_achieved":
        hint = (
            "Goal claimed ACHIEVED. Independently verify the achievement (receipt, gate output, "
            "artifact hash) — the /goal evaluator is a proxy, not ground truth."
        )
    else:
        hint = (
            "Verify one load-bearing claim from this session (receipt, gate output, artifact "
            "hash, or test exit code) before closing."
        )

    # RSI/DX reflex stubs from capture + inline transcript (judgment fields empty for skill)
    dx_rows = [r for r in (*corrects, *inline_corrects) if r.get("subtype") == "operator_dx"]
    if not dx_rows:
        dx_rows = extract_operator_dx_interventions(events)
    if dx_rows and "operator_dx" not in kinds:
        kinds = sorted(set(kinds) | {"operator_dx"})
        # refresh hint if we only discovered DX from transcript
        if "unsupported_completion" not in kinds and "user_rescued_failure" not in kinds:
            hint = (
                "OPERATOR DX/RSI INTERVENTION: fill operator_dx_reflex fields "
                "(operator_added_value, miss_class, would_have_prevented, action_taken) — "
                "max one action (local fix | steward proposal | explicit noop)."
            )
    operator_dx_reflex = [
        {
            "operator_added_value": r.get("operator_added_value") or r.get("trigger", ""),
            "miss_class": r.get("miss_class", "other"),
            "would_have_prevented": r.get("would_have_prevented", ""),
            "action_taken": r.get("action_taken", ""),
            "match": r.get("match", ""),
        }
        for r in dx_rows
    ]

    digest = {
        "schema": "reflect.close-digest.v1",
        "session_id": session_id,
        "project": intent.get("project", "unknown"),
        "ts": _utc_now(),
        "tier1_reason": reason,
        "real_issue_kinds": kinds,                       # WHY this close was triggered (the issue)
        "unsupported_completion": (
            {k: uc.get(k) for k in ("would_fire", "success_hits", "evidence_hits", "msg_tail")}
            if uc else None
        ),
        "fail_then_user_count": fail_then_user,
        "goal_state": goal_state,
        "session_end_reason": intent.get("reason"),
        "episode_line_count": len(episode_lines),
        "correction_signals": len(corrects) + len(inline_corrects),  # context only — no longer the trigger
        "correction_subtypes": sorted(
            {
                *(row.get("subtype", "") for row in corrects),
                *(row.get("subtype", "") for row in inline_corrects),
            }
        ),
        "operator_dx_reflex": operator_dx_reflex,
        "invoke_skill": True,
        "verify_hint": hint,
        "transcript_path": transcript_path,
    }
    return digest


def append_digest(digest: dict) -> None:
    DIGEST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DIGEST_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(digest, default=str) + "\n")


def append_maintain_one_liner(digest: dict) -> None:
    if not MAINTAIN.exists():
        return
    project = digest.get("project", "?")
    reason = digest.get("tier1_reason", "?")
    line = (
        f"\n- [{digest.get('ts', '')[:10]}] RSI close queued: "
        f"{project}/{digest.get('session_id', '')[:8]} ({reason})\n"
    )
    text = MAINTAIN.read_text(encoding="utf-8", errors="replace")
    if line.strip() in text:
        return
    with MAINTAIN.open("a", encoding="utf-8") as handle:
        handle.write(line)


def process_intent(path: Path) -> str:
    """Process one intent file end-to-end (read → gate → digest → mark processed).

    Returns the outcome: 'written' | 'skipped:<reason>' | 'already_processed' | 'unreadable'.
    """
    intent = _read_json(path)
    if not intent:
        return "unreadable"
    if intent.get("processed"):
        return "already_processed"

    digest = build_digest(intent)
    intent["processed"] = True
    intent["processed_ts"] = _utc_now()

    if digest:
        append_digest(digest)
        append_maintain_one_liner(digest)
        intent["digest_written"] = True
    else:
        intent["digest_written"] = False
        intent["skip_reason"] = "tier1_not_eligible"

    path.write_text(json.dumps(intent, indent=2) + "\n", encoding="utf-8")
    return "written" if digest else f"skipped:{intent['skip_reason']}"


def drain_queue(limit: int = 10) -> dict:
    """Process up to `limit` UNPROCESSED intents, oldest first.

    The unprocessed filter must run BEFORE the limit window: processed intents stay in
    the queue with frozen mtimes, so `sorted(...)[:limit]` alone wedges permanently once
    `limit` processed files accumulate at the head of the mtime order (the 2026-06-18 →
    07-06 outage: 132 intents starved behind 10 done files).

    Returns stats: read (intents examined), written (digests), skipped ({reason: count}),
    unreadable (unparseable queue files), pending_after (unprocessed left beyond limit).
    """
    stats: dict = {"read": 0, "written": 0, "skipped": {}, "unreadable": 0, "pending_after": 0}
    if not CLOSE_QUEUE.exists():
        return stats
    pending: list[Path] = []
    for path in sorted(CLOSE_QUEUE.glob("*.json"), key=lambda path: path.stat().st_mtime):
        intent = _read_json(path)
        if intent is None:
            stats["unreadable"] += 1
        elif not intent.get("processed"):
            pending.append(path)
    for path in pending[:limit]:
        stats["read"] += 1
        outcome = process_intent(path)
        if outcome == "written":
            stats["written"] += 1
        elif outcome.startswith("skipped:"):
            reason = outcome.split(":", 1)[1]
            stats["skipped"][reason] = stats["skipped"].get(reason, 0) + 1
        # 'already_processed'/'unreadable' here = raced by a concurrent drain; leave unaccounted
        # so the silent-zero guard in main() flags it rather than a count papering over it.
    stats["pending_after"] = max(0, len(pending) - stats["read"])
    return stats


def _closed_sessions() -> set[str]:
    """Session ids with an rsi_closed ack in the digest log."""
    closed: set[str] = set()
    if not DIGEST_LOG.exists():
        return closed
    for line in DIGEST_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if row.get("rsi_closed") and row.get("session_id"):
            closed.add(str(row["session_id"]))
    return closed


def latest_digest(session_id: str | None = None) -> dict | None:
    """Latest reflect.close-digest.v1 row — NEVER an ack.

    The digest log is a mixed event stream (digest.v1 + close-ack.v1 about the same
    lifecycle), so any consumer must select by schema; blind `tail -1` returns whatever
    was appended last — in practice an ack (the /rsi SKILL.md Step-1 failure). This owns
    that selection so consumers load it instead of re-stating it.

    With session_id: that session's latest digest, acked or not (explicit ask).
    Without: the latest digest whose session has no rsi_closed ack — the pending close.
    """
    if not DIGEST_LOG.exists():
        return None
    closed = _closed_sessions() if session_id is None else set()
    found: dict | None = None
    for line in DIGEST_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if row.get("schema") != "reflect.close-digest.v1":
            continue
        sid = str(row.get("session_id", ""))
        if session_id is not None:
            if sid == session_id:
                found = row  # latest wins
        elif sid not in closed:
            found = row
    return found


def hindsight_grades_path(project: str) -> Path | None:
    path = _HINDSIGHT_GRADES.get(project)
    return path if path and path.parent.parent.exists() else None


def append_hindsight_grade(project: str, row: dict) -> bool:
    """Append one Mode-3 grade row. Returns False if skipped (no path / invalid grade)."""
    path = hindsight_grades_path(project)
    grade = str(row.get("grade") or "").strip().upper()
    item = str(row.get("item") or "").strip()
    if not path or not item or grade not in _VALID_HINDSIGHT_GRADES:
        return False
    ts = row.get("ts") or _utc_now()[:16]
    out = {
        "ts": ts,
        "item": item,
        "grade": grade,
        "evidence": row.get("evidence") or "",
        "gap": row.get("gap") or "",
    }
    for key in ("session", "miss_class", "fix_commit", "source"):
        if row.get(key):
            out[key] = row[key]
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False) + "\n")
    return True


def operator_hindsight_from_digest(digest: dict, reflex: dict, *, grade: str) -> dict:
    """Build a hindsight row from digest + filled operator_dx_reflex fields."""
    import re

    miss = str(reflex.get("miss_class") or "other")
    seed = (
        reflex.get("operator_added_value")
        or reflex.get("match")
        or miss
    )
    slug = re.sub(r"[^a-z0-9]+", "-", str(seed).lower()).strip("-")[:48] or miss
    return {
        "item": f"operator:{slug}",
        "grade": grade,
        "evidence": reflex.get("operator_added_value") or reflex.get("match") or "",
        "gap": reflex.get("would_have_prevented") or "",
        "session": digest.get("session_id"),
        "miss_class": miss,
        "source": f"rsi-close/{digest.get('session_id', '')[:8]}",
    }


def ack_digest(session_id: str, *, hindsight: dict | list[dict] | None = None) -> int:
    """Append rsi_closed marker; optionally append HINDSIGHT Mode 3 grade(s). Returns count appended."""
    row = {
        "schema": "reflect.close-ack.v1",
        "session_id": session_id,
        "rsi_closed": True,
        "ts": _utc_now(),
    }
    with DIGEST_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    if not hindsight:
        return 0
    digest = latest_digest(session_id) or {}
    project = str(digest.get("project") or "")
    rows = hindsight if isinstance(hindsight, list) else [hindsight]
    n = 0
    for raw in rows:
        item = raw if raw.get("item") else operator_hindsight_from_digest(digest, raw, grade=raw.get("grade", ""))
        if append_hindsight_grade(project, item):
            n += 1
    return n


def _current_project() -> str:
    """Project asking for a nudge — cwd basename, matching the digest 'project' convention."""
    try:
        return Path.cwd().name
    except OSError:
        return ""


def pending_nudge(here: str | None = None) -> str | None:
    """One-line SessionStart nudge, RELEVANCE-GATED by project (added 2026-06-16: was
    project-blind, so a cross-project digest nudged — and dragged — an unrelated focused
    session into closing it). Surface an IN-PROJECT close fully; collapse other-project
    closes to a count. The queue is still drained by whichever session runs `/rsi close`
    regardless — this governs only the unprompted nudge."""
    if not DIGEST_LOG.exists():
        return None
    if here is None:
        here = _current_project()
    closed = _closed_sessions()
    in_project: dict | None = None
    other = 0
    for line in DIGEST_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        sid = row.get("session_id")
        if not (row.get("invoke_skill") and sid and sid not in closed):
            continue
        if here and row.get("project") == here:
            in_project = row          # latest in-project wins
        else:
            other += 1
    if in_project is not None:
        session_short = str(in_project.get("session_id", ""))[:8]
        tail = f" (+{other} pending in other projects — `just loop-funnel`)" if other else ""
        return (
            f"Prior {here} session {session_short} has an RSI close digest. "
            f"Run `/rsi close` to verify one claim and attach evidence.{tail}"
        )
    if other:
        return (
            f"{other} RSI close digest(s) pending in other projects (none in "
            f"{here or 'this project'}) — drain via `/rsi close` or review `just loop-funnel`."
        )
    return None


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="RSI session-close digest drain")
    parser.add_argument("--drain", action="store_true", help="Process close-queue entries")
    parser.add_argument("--nudge", action="store_true", help="Print SessionStart nudge if any")
    parser.add_argument("--ack", metavar="SESSION_ID", help="Mark session RSI-closed (stops nudge)")
    parser.add_argument(
        "--hindsight",
        metavar="JSON",
        help="Mode-3 grade appended on ack (item+grade required, or operator_dx_reflex fields)",
    )
    parser.add_argument(
        "--latest-digest",
        nargs="?",
        const="",
        default=None,
        metavar="SESSION_ID",
        help="Print latest close-digest row (never an ack): with SESSION_ID that session's, "
        "bare/empty the latest un-acked one. Exit 1 if none.",
    )
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)

    if args.ack:
        hindsight = None
        if args.hindsight:
            try:
                hindsight = json.loads(args.hindsight)
            except json.JSONDecodeError:
                sys.stderr.write("[reflect-session-close] invalid --hindsight JSON\n")
                return 1
        n = ack_digest(args.ack, hindsight=hindsight)
        if args.hindsight and n == 0:
            sys.stderr.write("[reflect-session-close] hindsight grade skipped (bad project/grade/item)\n")
        elif n:
            sys.stderr.write(f"[reflect-session-close] {n} hindsight grade(s) appended\n")
        return 0
    if args.latest_digest is not None:
        digest = latest_digest(args.latest_digest or None)
        if digest is None:
            sys.stderr.write("[reflect-session-close] no matching close-digest\n")
            return 1
        print(json.dumps(digest, indent=2, default=str))
        return 0
    if args.nudge:
        nudge = pending_nudge()
        if nudge:
            print(nudge)
        return 0
    if args.drain:
        stats = drain_queue(limit=args.limit)
        skipped_n = sum(stats["skipped"].values())
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(stats["skipped"].items())) or "none"
        sys.stderr.write(
            f"[reflect-session-close] {stats['read']} intents read, "
            f"{stats['written']} digests written, {skipped_n} skipped ({breakdown}); "
            f"{stats['pending_after']} still pending, {stats['unreadable']} unreadable\n"
        )
        if stats["read"] > 0 and stats["written"] == 0 and skipped_n == 0:
            # Every examined intent must land as written or skip-accounted; a silent zero
            # is the drain-logic bug class that starved the queue for 18 days — fail loud.
            sys.stderr.write(
                "[reflect-session-close] SILENT-ZERO: intents read but none written or "
                "skip-accounted — drain logic bug\n"
            )
            return 1
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
