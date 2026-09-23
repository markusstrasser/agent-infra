#!/usr/bin/env python3
"""reflect_session_close.py — async Tier 1 digest for goal-gated RSI session close.

Reads pending entries from ~/.claude/close-queue/, builds episode-bounded digests,
writes ~/.claude/reflect-close-digest.jsonl. Invoked from SessionStart drain hook
or manually. No LLM — digest is structured facts for /rsi close skill.
"""

from __future__ import annotations

import fcntl
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

# The transcript-prune horizon: the weekly agentlogs-archive job runs
# `archive_raw_logs.py --apply` at this default, moving raw transcripts older than it
# off ~/.claude/projects. A digest past it has lost its /rsi close verify path.
from archive_raw_logs import DEFAULT_KEEP_DAYS as TRANSCRIPT_HORIZON_DAYS  # noqa: E402
from goal_state import (  # noqa: E402
    slice_transcript_to_episode,
    tier1_eligible,
)
from reflect_capture import (  # noqa: E402
    extract_corrections,
    extract_operator_dx_interventions,
    parse_events,
    project_from_cwd,
    real_issue_signal,
)

CLOSE_QUEUE = Path.home() / ".claude" / "close-queue"
DIGEST_LOG = Path.home() / ".claude" / "reflect-close-digest.jsonl"
DIGEST_SCHEMA = "reflect.close-digest.v1"
ACK_SCHEMA = "reflect.close-ack.v1"
EXPIRED_REASON = "expired_unverifiable"
# Shortest session-id prefix accepted: the SessionStart nudge used to print 8-char ids,
# and closers paste those back into --latest-digest / --ack.
MIN_ID_PREFIX = 8

# Projects with loop/hindsight_grades.jsonl (HINDSIGHT Mode 3 bridge).
_HINDSIGHT_GRADES: dict[str, Path] = {
    "arc-agi": Path.home() / "Projects" / "arc-agi" / "loop" / "hindsight_grades.jsonl",
}
_VALID_HINDSIGHT_GRADES = frozenset({"DERIVABLE", "NON-DERIVABLE", "HAD-LEVER", "HAD-PARTS", "NOVEL"})
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


def build_digest(intent: dict) -> dict | None:
    """Build digest from a close-queue intent row. Returns None if not eligible."""
    session_id = intent.get("session_id", "unknown")
    goal_state = intent.get("goal_state") or {}
    corrects = _session_corrections(session_id)

    # Gate on a REAL empirical issue (single-source predicate) — cheap, no transcript read.
    real_issue, kinds = real_issue_signal(corrects)
    # The unsupported-completion shadow (stop-unsupported-completion.sh) was retired
    # 2026-09-02 after 4.6 months past its window with no grader; its log is archived.

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
        "schema": DIGEST_SCHEMA,
        "session_id": session_id,
        "project": intent.get("project", "unknown"),
        "ts": _utc_now(),
        "tier1_reason": reason,
        "real_issue_kinds": kinds,                       # WHY this close was triggered (the issue)
        "unsupported_completion": None,  # shadow retired 2026-09-02; key kept for digest readers
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


class DigestLookupError(LookupError):
    """A pasted session id that names no digest, or more than one session."""

    def __init__(self, message: str, candidates: list[str] | None = None) -> None:
        super().__init__(message)
        self.candidates = candidates or []


def _parse_rows(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _read_rows(log: Path | None = None) -> list[dict]:
    """Every parseable row of the digest log (digest.v1 and close-ack.v1 interleaved)."""
    path = DIGEST_LOG if log is None else log
    if not path.exists():
        return []
    return _parse_rows(path.read_text(encoding="utf-8", errors="replace"))


def _id_key(raw: object) -> str:
    """A pasted session id, trimmed of whitespace and a trailing ellipsis ('992ed156-...')."""
    return str(raw or "").strip().rstrip(".…")


def _id_matches(session_id: str, key: str) -> bool:
    """Does `key` name `session_id`: the full id, or a prefix of >= MIN_ID_PREFIX chars."""
    return bool(key) and (
        session_id == key or (len(key) >= MIN_ID_PREFIX and session_id.startswith(key))
    )


def _closed_keys(rows: list[dict]) -> set[str]:
    keys: set[str] = set()
    for row in rows:
        key = _id_key(row.get("session_id")) if row.get("rsi_closed") else ""
        if key:
            keys.add(key)
    return keys


def _is_closed(session_id: str, closed: set[str]) -> bool:
    """An ack closes a digest by full id OR by prefix — acks written with the nudge's
    8-char id (666dd3c4, b49d6a14, 2026-07/08) were inert under exact matching."""
    return session_id in closed or any(_id_matches(session_id, k) for k in closed)


def _closed_sessions() -> set[str]:
    """Normalized ack keys (full ids or prefixes) in the digest log."""
    return _closed_keys(_read_rows())


def resolve_session(key: str, rows: list[dict] | None = None) -> str:
    """The one digest session a pasted id means: exact id or unique prefix.

    Raises DigestLookupError when nothing matches or a prefix is ambiguous — callers
    must never guess between sessions or write an ack no reader will match.
    """
    rows = _read_rows() if rows is None else rows
    k = _id_key(key)
    matches: list[str] = []
    for row in rows:
        if row.get("schema") != DIGEST_SCHEMA:
            continue
        sid = str(row.get("session_id") or "")
        if sid and _id_matches(sid, k) and sid not in matches:
            matches.append(sid)
    if k in matches:
        return k
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise DigestLookupError(
            f"session id {key!r} is ambiguous — matches {', '.join(matches)}", matches
        )
    if len(k) < MIN_ID_PREFIX:
        raise DigestLookupError(
            f"no close-digest for session {key!r} (prefixes need >= {MIN_ID_PREFIX} chars)"
        )
    raise DigestLookupError(f"no close-digest for session {key!r}")


def _parse_ts(raw: object) -> datetime | None:
    try:
        ts = datetime.fromisoformat(str(raw or ""))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def verify_path(digest: dict, now: datetime | None = None) -> dict:
    """Can /rsi close still verify this digest against its session transcript?

    No once the transcript is gone from `transcript_path`, or once the digest is older
    than the transcript-prune horizon — the archive job takes the transcript then, and
    every surface uses the same clock whether or not that job has run yet.
    """
    now = now or datetime.now(timezone.utc)
    path = str(digest.get("transcript_path") or "")
    exists = bool(path) and Path(path).is_file()
    ts = _parse_ts(digest.get("ts"))
    age = round((now - ts).total_seconds() / 86400, 1) if ts else None
    past_horizon = age is not None and age > TRANSCRIPT_HORIZON_DAYS
    why = "transcript gone" if not exists else ("past the transcript horizon" if past_horizon else "")
    return {
        "expired": bool(why),
        "why": why,
        "transcript_exists": exists,
        "age_days": age,
        "horizon_days": TRANSCRIPT_HORIZON_DAYS,
    }


def _scan(rows: list[dict], now: datetime | None = None) -> tuple[list[dict], list[tuple[dict, dict]]]:
    """(pending, expired) over each session's latest un-acked digest, in log order."""
    closed = _closed_keys(rows)
    latest: dict[str, dict] = {}
    for row in rows:
        if row.get("schema") != DIGEST_SCHEMA:
            continue
        sid = str(row.get("session_id") or "")
        if not sid:
            continue
        latest.pop(sid, None)  # re-insert: order follows each session's LATEST digest
        latest[sid] = row
    pending: list[dict] = []
    expired: list[tuple[dict, dict]] = []
    for sid, row in latest.items():
        if _is_closed(sid, closed):
            continue
        verdict = verify_path(row, now)
        if verdict["expired"]:
            expired.append((row, verdict))
        else:
            pending.append(row)
    return pending, expired


def _mark_expired(path: Path, now: datetime) -> int:
    """Append one `expired_unverifiable` ack per digest whose verify path is gone.

    Append-only: the digest row stays; the ack stops every nudge/listing and records why.
    The log is re-read under an exclusive lock, so concurrent SessionStart sweeps cannot
    write the same expiry twice.
    """
    with path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            fh.seek(0)
            _, expired = _scan(_parse_rows(fh.read()), now)
            stamp = now.isoformat(timespec="seconds")
            for row, verdict in expired:
                ack = {
                    "schema": ACK_SCHEMA,
                    "session_id": str(row["session_id"]),
                    "rsi_closed": True,
                    "reason": EXPIRED_REASON,
                    "why": verdict["why"],
                    "project": row.get("project"),
                    "digest_ts": row.get("ts"),
                    "transcript_path": row.get("transcript_path") or "",
                    "transcript_exists": verdict["transcript_exists"],
                    "age_days": verdict["age_days"],
                    "horizon_days": verdict["horizon_days"],
                    "ts": stamp,
                }
                fh.write(json.dumps(ack, ensure_ascii=False) + "\n")
            fh.flush()
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    return len(expired)


def pending_digests(
    *, log: Path | None = None, project: str | None = None, sweep: bool = True
) -> list[dict]:
    """THE pending-close definition, oldest first: each session's latest digest.v1 row
    that no ack closes (by full id or prefix) and that is still verifiable; `project`
    narrows it to one project.

    Every surface loads this instead of re-stating it — the SessionStart nudge, the bare
    `--latest-digest`, `--ack-stale` and the loop funnel (control-plane "RSI close pending").
    Listing is where unverifiable digests expire: with `sweep` (default) each one gets an
    `expired_unverifiable` ack appended; without it they are only left out (dry runs).
    """
    path = DIGEST_LOG if log is None else log
    now = datetime.now(timezone.utc)
    pending, expired = _scan(_read_rows(path), now)
    if sweep and expired:
        _mark_expired(path, now)
    return [row for row in pending if project is None or row.get("project") == project]


def expired_digests(*, log: Path | None = None) -> list[dict]:
    """The `expired_unverifiable` ack rows — closes the loop lost to transcript expiry."""
    return [row for row in _read_rows(log) if row.get("reason") == EXPIRED_REASON]


def latest_digest(session_id: str | None = None, *, project: str | None = None) -> dict | None:
    """Latest reflect.close-digest.v1 row — NEVER an ack.

    The digest log is a mixed event stream (digest.v1 + close-ack.v1 about the same
    lifecycle), so any consumer must select by schema; blind `tail -1` returns whatever
    was appended last — in practice an ack (the /rsi SKILL.md Step-1 failure). This owns
    that selection so consumers load it instead of re-stating it.

    With session_id (full id or unique prefix): that session's latest digest, acked or
    not (explicit ask, any project); None when no digest matches; DigestLookupError when
    a prefix is ambiguous. Without: the newest pending close, in `project` when given —
    the CLI passes the invoking project, so an arc-agi close never picks up another
    project's claims (steward 2026-07-21).
    """
    if session_id is None:
        pending = pending_digests(project=project)
        return pending[-1] if pending else None
    rows = _read_rows()
    try:
        sid = resolve_session(session_id, rows)
    except DigestLookupError as exc:
        if exc.candidates:
            raise
        return None
    found: dict | None = None
    for row in rows:
        if row.get("schema") == DIGEST_SCHEMA and str(row.get("session_id")) == sid:
            found = row  # latest wins
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


def ack_digest(
    session_id: str,
    *,
    hindsight: dict | list[dict] | None = None,
    here: str | None = None,
) -> int:
    """Append rsi_closed marker; optionally append HINDSIGHT Mode 3 grade(s). Returns count appended.

    The ack is written under the FULL session id that `session_id` (full id or unique
    prefix) resolves to; an id naming no digest, or an ambiguous prefix, raises
    DigestLookupError and writes nothing (a prefix ack used to land as an inert row).
    With `here`, a digest from another project is refused too: closing it means
    verifying claims without that project's context (the CLI's --any-project lifts it).
    """
    sid = resolve_session(session_id)
    if here is not None:
        owner = str((latest_digest(sid) or {}).get("project") or "")
        if owner != here:
            raise DigestLookupError(
                f"digest {sid} belongs to project {owner!r}, not {here!r} — close it from "
                f"that project or pass --any-project"
            )
    row = {
        "schema": ACK_SCHEMA,
        "session_id": sid,
        "rsi_closed": True,
        "ts": _utc_now(),
    }
    with DIGEST_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    if not hindsight:
        return 0
    digest = latest_digest(sid) or {}
    project = str(digest.get("project") or "")
    rows = hindsight if isinstance(hindsight, list) else [hindsight]
    n = 0
    for raw in rows:
        item = raw if raw.get("item") else operator_hindsight_from_digest(digest, raw, grade=raw.get("grade", ""))
        if append_hindsight_grade(project, item):
            n += 1
    return n


def ack_stale_digests(older_than_days: int, *, note: str, dry_run: bool = False) -> list[dict]:
    """Ack every un-acked digest older than N days, LABELED as unreviewed.

    A queue nobody drains is the flooding GOALS.md forbids: 28 pending digests (oldest
    2026-07-06) nagged every SessionStart while no session ever ran /rsi close on them.
    The ack row carries ``reason: stale-unreviewed`` so the ledger never reads these as
    verified closes — a labeled screen, not a silent substitute (2026-09-02 queue freeze).
    Returns the digests acked (or, with dry_run, the ones that would be). Digests whose
    verify path is already gone expire as `expired_unverifiable` first and are not listed.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    stale: list[dict] = []
    for row in pending_digests(sweep=not dry_run):
        ts = _parse_ts(row.get("ts"))
        if ts is None or ts >= cutoff:
            continue
        stale.append(
            {"session_id": str(row["session_id"]), "project": row.get("project"), "digest_ts": row.get("ts")}
        )
    if dry_run or not stale:
        return stale
    with DIGEST_LOG.open("a", encoding="utf-8") as fh:
        for item in stale:
            ack = {
                "schema": ACK_SCHEMA,
                "session_id": item["session_id"],
                "rsi_closed": True,
                "reason": "stale-unreviewed",
                "note": note,
                "digest_ts": item["digest_ts"],
                "ts": _utc_now(),
            }
            fh.write(json.dumps(ack, ensure_ascii=False) + "\n")
    return stale


def _current_project() -> str:
    """Project asking for a nudge/close — the capture path's own cwd → project mapping."""
    try:
        return project_from_cwd(Path.cwd())
    except OSError:
        return ""


def pending_nudge(here: str | None = None) -> str | None:
    """One-line SessionStart nudge, THIS-PROJECT only (2026-07-10).

    Cross-project digests are not SessionStart noise — drain via `/rsi close` or
    `just loop-funnel` when the operator chooses. The queue is still drained by
    whichever session runs `/rsi close`; this governs only the unprompted nudge.
    Prints the FULL session id so the closer's `--ack` needs no prefix resolution, and the
    date the digest stops being verifiable (it then expires instead of nagging).
    """
    if here is None:
        here = _current_project()
    if not here:
        return None
    in_project = pending_digests(project=here)
    if not in_project:
        return None
    digest = in_project[-1]  # latest in-project wins
    session_id = str(digest.get("session_id", ""))
    ts = _parse_ts(digest.get("ts"))
    window = ""
    if ts is not None:
        until = (ts + timedelta(days=TRANSCRIPT_HORIZON_DAYS)).date().isoformat()
        window = f" from {ts.date().isoformat()} (verifiable until {until})"
    return (
        f"Prior {here} session {session_id} has an RSI close digest{window}. "
        f"Run `/rsi close` to verify one claim and attach evidence."
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="RSI session-close digest drain")
    parser.add_argument("--drain", action="store_true", help="Process close-queue entries")
    parser.add_argument("--nudge", action="store_true", help="Print SessionStart nudge if any")
    parser.add_argument(
        "--ack",
        metavar="SESSION_ID",
        help="Mark session RSI-closed (stops nudge); full id or unique >=8-char prefix, "
        "written as the full id. Exit 1, nothing written, if it names no digest",
    )
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
        help="Print latest close-digest row (never an ack): with SESSION_ID (full id or "
        "unique prefix) that session's, bare/empty the latest pending one in THIS project. "
        "Exit 1 if none or if a prefix is ambiguous.",
    )
    parser.add_argument(
        "--any-project",
        action="store_true",
        help="let the bare --latest-digest and --ack reach another project's digest",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--ack-stale",
        type=int,
        metavar="DAYS",
        help="Ack every un-acked digest older than DAYS, labeled reason=stale-unreviewed "
        "(queue freeze; never counts as a verified close)",
    )
    parser.add_argument(
        "--note",
        default="bulk ack at the 2026-09-02 RSI queue freeze — never reviewed",
        help="note stored on each --ack-stale row",
    )
    parser.add_argument("--dry-run", action="store_true", help="with --ack-stale: list, write nothing")
    args = parser.parse_args(argv)

    if args.ack_stale is not None:
        stale = ack_stale_digests(args.ack_stale, note=args.note, dry_run=args.dry_run)
        for item in stale:
            print(f"{str(item['session_id'])[:8]}  {item['project']}  {item['digest_ts']}")
        verb = "would ack" if args.dry_run else "acked"
        sys.stderr.write(
            f"[reflect-session-close] {verb} {len(stale)} stale digest(s) older than "
            f"{args.ack_stale}d (reason=stale-unreviewed)\n"
        )
        return 0

    if args.ack:
        hindsight = None
        if args.hindsight:
            try:
                hindsight = json.loads(args.hindsight)
            except json.JSONDecodeError:
                sys.stderr.write("[reflect-session-close] invalid --hindsight JSON\n")
                return 1
        here = None if args.any_project else _current_project()
        try:
            n = ack_digest(args.ack, hindsight=hindsight, here=here)
        except DigestLookupError as exc:
            sys.stderr.write(f"[reflect-session-close] ack refused, nothing written: {exc}\n")
            return 1
        if args.hindsight and n == 0:
            sys.stderr.write("[reflect-session-close] hindsight grade skipped (bad project/grade/item)\n")
        elif n:
            sys.stderr.write(f"[reflect-session-close] {n} hindsight grade(s) appended\n")
        return 0
    if args.latest_digest is not None:
        here = None if args.any_project else _current_project()
        try:
            digest = latest_digest(args.latest_digest or None, project=here)
        except DigestLookupError as exc:
            sys.stderr.write(f"[reflect-session-close] {exc}\n")
            return 1
        if digest is None:
            scope = "any project" if here is None else f"project {here!r}"
            sys.stderr.write(f"[reflect-session-close] no matching close-digest ({scope})\n")
            if args.latest_digest:
                # /rsi close looks up the CURRENT session; a prior session's digest (the
                # SessionStart-nudge case) would otherwise never be closed (steward 2026-08-18).
                pending = pending_digests(project=here)
                if pending:
                    sid = pending[-1]["session_id"]
                    sys.stderr.write(
                        f"[reflect-session-close] pending in {scope}: {sid} "
                        f"({str(pending[-1].get('ts', ''))[:10]}) — `--latest-digest {sid}`\n"
                    )
            return 1
        print(json.dumps(digest, indent=2, default=str))
        verdict = verify_path(digest)
        if verdict["expired"]:
            # Only an explicit id reaches here: the bare lookup never returns one of these.
            sys.stderr.write(
                f"[STALE-DIGEST: {verdict['why']} — digest {verdict['age_days']}d old, "
                f"transcript horizon {verdict['horizon_days']}d; verify path degraded to "
                f"git/agentlogs]\n"
            )
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
