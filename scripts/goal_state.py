#!/usr/bin/env python3
"""goal_state.py — platform-split goal detection for RSI session-close gating.

Pure core for unit testing; no IO except optional transcript file read helpers.
Fail-loud: unknown marker shapes return status=unknown, never silent false-negative.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

GoalStatus = Literal["achieved", "active", "blocked", "cleared", "unknown"]
GoalSource = Literal["claude_transcript", "codex_app_server", "explicit_rsi_close", "none"]

_GOAL_ACHIEVED_TEXT = re.compile(r"\bgoal achieved\b|\bgoal met\b", re.IGNORECASE)
_RSI_CLOSE = re.compile(r"/rsi\s+close\b", re.IGNORECASE)
_GOAL_ACTIVE_TEXT = re.compile(r"/goal active|◎\s*/goal active", re.IGNORECASE)


def _result(
    *,
    source: GoalSource,
    status: GoalStatus,
    evidence_ts: str | None = None,
    raw_ref: str | None = None,
    objective: str | None = None,
    degraded: bool = False,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source": source,
        "status": status,
        "evidence_ts": evidence_ts,
        "raw_ref": raw_ref,
    }
    if objective:
        row["objective"] = objective[:500]
    if degraded:
        row["degraded"] = True
    return row


def _parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None


def _attachment_goal_status(obj: dict) -> dict | None:
    if obj.get("type") != "attachment":
        return None
    att = obj.get("attachment") or {}
    if att.get("type") != "goal_status":
        return None
    return att


def _text_blob(obj: dict) -> str:
    parts: list[str] = []
    msg = obj.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
    if obj.get("type") == "user" and isinstance(obj.get("message"), dict):
        pass  # already handled
    return " ".join(parts)


def goal_state_from_transcript(lines: list[str]) -> dict[str, Any]:
    """Scan Claude Code JSONL for goal lifecycle markers.

    Priority: first achieved timestamp wins (episode boundary). Attachment
    goal_status.met=true is primary; "Goal achieved" text is fallback.
    """
    attachment_achieved: dict[str, Any] | None = None
    active_goal_achieved: dict[str, Any] | None = None
    text_achieved: dict[str, Any] | None = None
    last_active: dict[str, Any] | None = None
    last_blocked: dict[str, Any] | None = None
    saw_goal_attachment = False
    explicit_rsi = False

    for line in lines:
        obj = _parse_line(line)
        if not obj:
            continue
        ts = obj.get("timestamp")

        att = _attachment_goal_status(obj)
        if att is not None:
            saw_goal_attachment = True
            objective = att.get("condition") or att.get("objective")
            if att.get("met") is True:
                if attachment_achieved is None:
                    attachment_achieved = _result(
                        source="claude_transcript",
                        status="achieved",
                        evidence_ts=ts,
                        raw_ref="attachment.goal_status.met=true",
                        objective=str(objective) if objective else None,
                    )
            elif att.get("met") is False or att.get("active") is True:
                last_active = _result(
                    source="claude_transcript",
                    status="active",
                    evidence_ts=ts,
                    raw_ref="attachment.goal_status.active",
                    objective=str(objective) if objective else None,
                )
            elif att.get("blocked") is True:
                last_blocked = _result(
                    source="claude_transcript",
                    status="blocked",
                    evidence_ts=ts,
                    raw_ref="attachment.goal_status.blocked",
                )

        # activeGoal in metadata-style attachments
        att_raw = obj.get("attachment") or {}
        active_goal = att_raw.get("activeGoal") or att_raw.get("active_goal")
        if isinstance(active_goal, dict):
            saw_goal_attachment = True
            if active_goal.get("met") is True and active_goal_achieved is None:
                active_goal_achieved = _result(
                    source="claude_transcript",
                    status="achieved",
                    evidence_ts=ts,
                    raw_ref="attachment.activeGoal.met=true",
                    objective=str(active_goal.get("objective", "")) or None,
                )
            elif active_goal.get("met") is False:
                last_active = _result(
                    source="claude_transcript",
                    status="active",
                    evidence_ts=ts,
                    raw_ref="attachment.activeGoal.met=false",
                    objective=str(active_goal.get("objective", "")) or None,
                )

        text = _text_blob(obj)
        if text and _GOAL_ACHIEVED_TEXT.search(text):
            if text_achieved is None:
                text_achieved = _result(
                    source="claude_transcript",
                    status="achieved",
                    evidence_ts=ts,
                    raw_ref="text:Goal achieved/met",
                )
        if text and _GOAL_ACTIVE_TEXT.search(text):
            last_active = _result(
                source="claude_transcript",
                status="active",
                evidence_ts=ts,
                raw_ref="text:/goal active",
            )
        if text and _RSI_CLOSE.search(text):
            explicit_rsi = True

        # slash command in user message
        if obj.get("type") == "user":
            for block in (obj.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    user_text = block.get("text", "")
                    if user_text.strip().lower().startswith("/goal clear"):
                        return _result(
                            source="claude_transcript",
                            status="cleared",
                            evidence_ts=ts,
                            raw_ref="slash:/goal clear",
                        )

    if explicit_rsi:
        return _result(
            source="explicit_rsi_close",
            status="achieved",
            raw_ref="slash:/rsi close",
        )
    if attachment_achieved:
        return attachment_achieved
    if active_goal_achieved:
        return active_goal_achieved
    if text_achieved:
        return text_achieved
    if last_blocked:
        return last_blocked
    if last_active:
        return last_active
    if saw_goal_attachment:
        return _result(
            source="claude_transcript",
            status="unknown",
            raw_ref="goal_attachment_unrecognized_shape",
            degraded=True,
        )
    return _result(source="none", status="unknown", raw_ref="no_goal_markers")


def goal_state_from_codex(goal: dict | None) -> dict[str, Any]:
    """Map Codex thread/goal/get payload to unified status."""
    if not goal:
        return _result(source="codex_app_server", status="cleared", raw_ref="goal=null")

    status_raw = str(goal.get("status", "")).lower()
    objective = goal.get("objective")
    ts = goal.get("updatedAt")
    if isinstance(ts, int):
        from datetime import datetime, timezone

        evidence_ts = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
    else:
        evidence_ts = None

    mapping: dict[str, GoalStatus] = {
        "complete": "achieved",
        "completed": "achieved",
        "achieved": "achieved",
        "active": "active",
        "blocked": "blocked",
        "budgetlimited": "blocked",
        "budget_limited": "blocked",
        "usagelimited": "blocked",
        "usage_limited": "blocked",
        "paused": "active",
    }
    mapped = mapping.get(status_raw)
    if mapped:
        return _result(
            source="codex_app_server",
            status=mapped,
            evidence_ts=evidence_ts,
            raw_ref=f"goal.status={status_raw}",
            objective=str(objective) if objective else None,
        )
    return _result(
        source="codex_app_server",
        status="unknown",
        evidence_ts=evidence_ts,
        raw_ref=f"goal.status={status_raw or 'missing'}",
        degraded=True,
    )


def tier1_eligible(
    goal_state: dict[str, Any],
    *,
    correction_strong: bool = False,
) -> tuple[bool, str]:
    """Return (eligible, reason) for Tier 1 digest + /rsi close."""
    status = goal_state.get("status")
    source = goal_state.get("source")

    if correction_strong:
        return True, "operator_correction_signal"
    if source == "explicit_rsi_close":
        return True, "explicit_rsi_close"
    if status == "achieved":
        return True, "goal_achieved"
    if status == "active":
        return False, "goal_still_active"
    if status == "blocked":
        return False, "goal_blocked_capture_only"
    if status == "cleared":
        return False, "goal_cleared_no_achieve"
    if status == "unknown":
        if goal_state.get("degraded"):
            return False, "degraded_unknown_marker"
        return False, "no_goal_signal"
    return False, "unhandled_status"


def slice_transcript_to_episode(lines: list[str], end_ts: str | None) -> list[str]:
    """Keep transcript lines up to first goal-achieved timestamp (inclusive)."""
    if not end_ts:
        return lines
    out: list[str] = []
    for line in lines:
        out.append(line)
        obj = _parse_line(line)
        if obj and obj.get("timestamp") == end_ts:
            break
    return out
