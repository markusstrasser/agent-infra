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
    goal_state_from_transcript,
    slice_transcript_to_episode,
    tier1_eligible,
)
from reflect_capture import extract_corrections, parse_events  # noqa: E402

CLOSE_QUEUE = Path.home() / ".claude" / "close-queue"
DIGEST_LOG = Path.home() / ".claude" / "reflect-close-digest.jsonl"
CAPTURE_LOG = Path.home() / ".claude" / "reflect-capture.jsonl"
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


def _correction_strong(corrects: list[dict]) -> bool:
    for row in corrects:
        if row.get("subtype") == "f_tag":
            return True
        if row.get("strength") == "strong":
            return True
    return len(corrects) >= 3


def build_digest(intent: dict) -> dict | None:
    """Build digest from a close-queue intent row. Returns None if not eligible."""
    session_id = intent.get("session_id", "unknown")
    goal_state = intent.get("goal_state") or {}
    corrects = _session_corrections(session_id)
    strong = _correction_strong(corrects)
    eligible, reason = tier1_eligible(goal_state, correction_strong=strong)
    if not eligible and not intent.get("force_tier1"):
        return None

    transcript_path = intent.get("transcript_path") or ""
    lines: list[str] = []
    if transcript_path and Path(transcript_path).exists():
        lines = Path(transcript_path).read_text(encoding="utf-8", errors="replace").splitlines()

    episode_lines = slice_transcript_to_episode(lines, goal_state.get("evidence_ts"))
    events = parse_events(episode_lines)
    inline_corrects = extract_corrections(events)

    digest = {
        "schema": "reflect.close-digest.v1",
        "session_id": session_id,
        "project": intent.get("project", "unknown"),
        "ts": _utc_now(),
        "tier1_reason": reason,
        "goal_state": goal_state,
        "session_end_reason": intent.get("reason"),
        "episode_line_count": len(episode_lines),
        "correction_signals": len(corrects) + len(inline_corrects),
        "correction_subtypes": sorted(
            {
                *(row.get("subtype", "") for row in corrects),
                *(row.get("subtype", "") for row in inline_corrects),
            }
        ),
        "invoke_skill": True,
        "verify_hint": (
            "Verify one load-bearing claim from this session (receipt, gate output, "
            "artifact hash, or test exit code) before fm.py attach-evidence."
        ),
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


def process_intent(path: Path) -> bool:
    intent = _read_json(path)
    if not intent or intent.get("processed"):
        return False

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
    return digest is not None


def drain_queue(limit: int = 10) -> int:
    if not CLOSE_QUEUE.exists():
        return 0
    written = 0
    pending = sorted(CLOSE_QUEUE.glob("*.json"), key=lambda path: path.stat().st_mtime)
    for path in pending[:limit]:
        if process_intent(path):
            written += 1
    return written


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


def ack_digest(session_id: str) -> None:
    """Append rsi_closed marker so pending_nudge stops surfacing this session."""
    row = {
        "schema": "reflect.close-ack.v1",
        "session_id": session_id,
        "rsi_closed": True,
        "ts": _utc_now(),
    }
    with DIGEST_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def pending_nudge() -> str | None:
    """Return a one-line SessionStart nudge if a digest awaits /rsi close."""
    if not DIGEST_LOG.exists():
        return None
    closed = _closed_sessions()
    last: dict | None = None
    for line in DIGEST_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        sid = row.get("session_id")
        if row.get("invoke_skill") and sid and sid not in closed:
            last = row
    if not last:
        return None
    project = last.get("project", "?")
    session_short = str(last.get("session_id", ""))[:8]
    return (
        f"Prior session {project}/{session_short} has an RSI close digest. "
        f"Run `/rsi close` to verify one claim and attach evidence."
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="RSI session-close digest drain")
    parser.add_argument("--drain", action="store_true", help="Process close-queue entries")
    parser.add_argument("--nudge", action="store_true", help="Print SessionStart nudge if any")
    parser.add_argument("--ack", metavar="SESSION_ID", help="Mark session RSI-closed (stops nudge)")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.ack:
        ack_digest(args.ack)
        return 0
    if args.nudge:
        nudge = pending_nudge()
        if nudge:
            print(nudge)
        return 0
    if args.drain:
        count = drain_queue(limit=args.limit)
        sys.stderr.write(f"[reflect-session-close] {count} digest(s) written\n")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
