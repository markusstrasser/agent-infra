#!/usr/bin/env python3
# Gov-ID: lib:supervision-session
# goal: single JSONL pass → typed supervision events + direction vector per session.
#       Shared by supervision-kpi (pulse), observe/supervision mode, and tests.
# verifier: scripts/tests/test_supervision_session.py
# blast_radius: local
"""Session-level supervision analysis — one parser, one taxonomy, inspectable events.

Consumers:
  • supervision-kpi.py  — CLI + pulse sensor
  • observe supervision mode — `--report` artifact for /observe
  • blindspot_miner.py  — emb tier only; regex tier lives here

Every text correction is a `SupervisionEvent` carrying the taxonomy `Match` (method, score,
evidence). Structural types (denial, repeated_instruction) are counted by the parser, not
re-classified elsewhere.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from common.paths import PROJECTS_DIR
from config import extract_project_name

import supervision_taxonomy as tax

SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>", re.IGNORECASE)
SYSTEM_INJECTED_RE = re.compile(
    r"^(?:<task-notification>|<command-message>|<command-name>"
    r"|Base directory for this skill:"
    r"|Stop hook feedback:"
    r"|Uncommitted changes:"
    r"|You MUST call)",
)


@dataclass
class SupervisionEvent:
    turn: int
    type_id: str
    direction: str
    method: str
    score: float
    evidence: str
    text_preview: str


@dataclass
class SessionRecord:
    session_id: str
    project: str
    date: str | None
    user_turns: int
    by_type: dict[str, int]
    vector: dict[str, int]
    load: int
    hooks_shown: int
    corrections_after_hooks: int
    air: float | None
    events: list[SupervisionEvent] = field(default_factory=list)

    def to_kpi_dict(self) -> dict[str, Any]:
        """JSON-serializable session row (no per-event detail — KPI JSONL)."""
        return {
            "session_id": self.session_id,
            "project": self.project,
            "date": self.date,
            "user_turns": self.user_turns,
            "by_type": self.by_type,
            "vector": self.vector,
            "load": self.load,
            "hooks_shown": self.hooks_shown,
            "corrections_after_hooks": self.corrections_after_hooks,
            "air": self.air,
        }


def find_sessions_by_date(since: datetime, until: datetime | None = None) -> list[Path]:
    since_ts = since.timestamp()
    until_ts = until.timestamp() if until else datetime.now().timestamp() + 86400
    out: list[Path] = []
    for proj_dir in sorted(PROJECTS_DIR.iterdir()):
        if not proj_dir.is_dir():
            continue
        for jsonl in proj_dir.glob("*.jsonl"):
            if "agent-" in jsonl.name or "compact" in jsonl.name:
                continue
            if since_ts <= jsonl.stat().st_mtime <= until_ts:
                out.append(jsonl)
    return sorted(out, key=lambda p: p.stat().st_mtime)


def analyze_session(path: Path) -> SessionRecord:
    """Single-pass JSONL analysis. One primary taxonomy type per user turn."""
    session_id: str | None = None
    project = extract_project_name(path.parent.name)
    by_type: dict[str, int] = {t.id: 0 for t in tax.TAXONOMY}
    events: list[SupervisionEvent] = []
    user_messages: list[str] = []

    turn_index = 0
    hook_turn_indices: list[int] = []
    correction_turn_indices: list[int] = []
    first_timestamp: str | None = None

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not session_id:
                session_id = obj.get("sessionId")
            ts = obj.get("timestamp")
            if ts and first_timestamp is None:
                first_timestamp = ts

            msg_type = obj.get("type")

            if msg_type == "user" and not obj.get("toolUseResult"):
                text = _extract_user_text(obj)
                if not text:
                    continue
                turn_index += 1
                user_messages.append(text)
                m = tax.classify_regex(text)
                if m is not None:
                    by_type[m.type_id] += 1
                    correction_turn_indices.append(turn_index)
                    events.append(SupervisionEvent(
                            turn=turn_index,
                            type_id=m.type_id,
                            direction=m.direction.value,
                            method=m.method,
                            score=m.score,
                            evidence=m.evidence,
                            text_preview=text[:240],
                        ))

            elif msg_type == "user" and obj.get("toolUseResult"):
                if _is_denial(obj["toolUseResult"]):
                    by_type["denial"] += 1
                    correction_turn_indices.append(turn_index)
                    events.append(SupervisionEvent(
                            turn=turn_index,
                            type_id="denial",
                            direction=tax.Direction.REDUCE_ERROR.value,
                            method="structural",
                            score=1.0,
                            evidence="toolUseResult:denied",
                            text_preview=_extract_user_text(obj) or "",
                        ))

            elif msg_type == "progress":
                data = obj.get("data", {})
                if data.get("type") == "hook_progress" and data.get("hookEvent") == "Stop":
                    hook_turn_indices.append(turn_index)

            elif msg_type == "attachment":
                att = obj.get("attachment") or {}
                if att.get("type") == "hook_success" and (
                    att.get("stdout") or att.get("stderr")
                    or att.get("hookAdditionalContext") or att.get("hook_additional_context")
                ):
                    hook_turn_indices.append(turn_index)

    by_type["repeated_instruction"] = _count_repeated_instructions(user_messages)

    hook_turn_indices = sorted(set(hook_turn_indices))
    vector = tax.empty_vector()
    for type_id, n in by_type.items():
        tax.add_to_vector(vector, type_id, n)

    corrections_after_hooks = _count_corrections_after_hooks(
        hook_turn_indices, correction_turn_indices, window=3,
    )
    air = (
        round(corrections_after_hooks / len(hook_turn_indices), 3)
        if hook_turn_indices else None
    )

    return SessionRecord(
        session_id=(session_id or path.stem),
        project=project,
        date=first_timestamp[:10] if first_timestamp else None,
        user_turns=len(user_messages),
        by_type=by_type,
        vector=vector,
        load=tax.gross_load(by_type, by_type=True),
        hooks_shown=len(hook_turn_indices),
        corrections_after_hooks=corrections_after_hooks,
        air=air,
        events=events,
    )


def filter_by_start_date(records: list[SessionRecord], since: datetime) -> list[SessionRecord]:
    since_str = since.strftime("%Y-%m-%d")
    today_str = datetime.now().strftime("%Y-%m-%d")
    return [r for r in records if r.date and since_str <= r.date <= today_str]


def aggregate_vector(records: list[SessionRecord]) -> dict[str, int]:
    agg = tax.empty_vector()
    for r in records:
        for k, v in r.vector.items():
            agg[k] = agg.get(k, 0) + v
    return agg


def aggregate_by_type(records: list[SessionRecord]) -> dict[str, int]:
    agg: dict[str, int] = defaultdict(int)
    for r in records:
        for k, v in r.by_type.items():
            agg[k] += v
    return dict(agg)


def compute_direction_trends(records: list[SessionRecord], window: int = 30) -> dict[str, float] | None:
    recent = sorted(records, key=lambda r: r.date or "")[-window:]
    if len(recent) < 5:
        return None
    trends: dict[str, float] = {}
    for d in tax.Direction:
        ys = [r.vector.get(d.value, 0) for r in recent]
        trends[d.value] = round(-_slope(ys), 4)
    trends["load"] = round(-_slope([r.load for r in recent]), 4)
    return trends


def autonomy_reading(trends: dict[str, float] | None) -> str:
    if not trends:
        return "insufficient_data"
    gain = (
        trends.get("raise_autonomy", 0) > 0
        and trends.get("reduce_error", 0) >= 0
        and trends.get("grow_coverage", 0) >= 0
    )
    if gain:
        return "genuine_gain"
    if trends.get("raise_autonomy", 0) > 0 and trends.get("reduce_error", 0) < 0:
        return "timidity_down_errors_up"
    if trends.get("raise_autonomy", 0) < 0:
        return "timidity_rising"
    return "mixed"


def build_report(
    records: list[SessionRecord],
    *,
    days: int | None,
    since: datetime,
    project_filter: str | None,
    include_session_rows: bool = False,
) -> dict[str, Any]:
    """Observe-ready aggregate report — direction vector is the headline."""
    user_turns = sum(r.user_turns for r in records)
    by_type = aggregate_by_type(records)
    vector = aggregate_vector(records)
    correction_events = sum(by_type.values())
    trends = compute_direction_trends(records)

    air_sessions = [r for r in records if r.air is not None]
    total_hooks = sum(r.hooks_shown for r in air_sessions)
    total_after = sum(r.corrections_after_hooks for r in air_sessions)

    metric_warnings: list[str] = []
    if len(records) >= 5 and total_hooks == 0:
        metric_warnings.append(
            "hooks_shown=0 across analyzed sessions — AIR and hook-effectiveness "
            "metrics may be silently zero (check hook_success events in agentlogs)"
        )

    examples: list[dict[str, Any]] = []
    for r in sorted(records, key=lambda x: -x.load):
        for ev in r.events[:3]:
            examples.append({
                "session_id": r.session_id[:12],
                "project": r.project,
                "date": r.date,
                **asdict(ev),
            })
        if len(examples) >= 24:
            break

    top_sessions = sorted(records, key=lambda r: -r.load)[:10]
    by_project: dict[str, dict[str, int]] = defaultdict(lambda: tax.empty_vector())
    for r in records:
        for k, v in r.vector.items():
            by_project[r.project][k] = by_project[r.project].get(k, 0) + v

    report: dict[str, Any] = {
        "schema": "supervision.report.v1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "period": {
            "days": days,
            "since": since.strftime("%Y-%m-%d"),
            "until": datetime.now().strftime("%Y-%m-%d"),
        },
        "project_filter": project_filter or "all",
        "sessions_analyzed": len(records),
        "user_turns": user_turns,
        "correction_events": correction_events,
        "correction_rate_pct": round(100 * correction_events / user_turns, 2) if user_turns else 0.0,
        "by_type": by_type,
        "vector": vector,
        "gross_load": sum(r.load for r in records),
        "direction_labels": {
            "raise_autonomy": "agent was TIMID → loosen/act (pure autonomy signal)",
            "reduce_error": "agent was WRONG → correctness guardrail",
            "grow_coverage": "agent missed CONTEXT → add detector",
            "amplify_taste": "agent missed TASTE → options, keep human judge",
        },
        "autonomy_reading": autonomy_reading(trends),
        "direction_trends": trends,
        "air": {
            "overall": round(total_after / total_hooks, 3) if total_hooks else None,
            "corrections_after_hooks": total_after,
            "hooks_shown": total_hooks,
            "sessions_with_hooks": len(air_sessions),
        },
        "metric_integrity": {
            "hooks_visibility_ok": not metric_warnings,
            "warnings": metric_warnings,
        },
        "by_project_vector": dict(by_project),
        "top_sessions": [
            {
                "session_id": r.session_id[:12],
                "project": r.project,
                "date": r.date,
                "load": r.load,
                "vector": r.vector,
                "by_type": {k: v for k, v in r.by_type.items() if v},
            }
            for r in top_sessions
        ],
        "examples": examples,
        "taxonomy_source": "scripts/supervision_taxonomy.py",
    }
    if include_session_rows:
        report["sessions"] = [r.to_kpi_dict() for r in records]
    return report


def _extract_user_text(obj: dict) -> str | None:
    content = obj.get("message", {}).get("content", "")
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "\n".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    if not text:
        return None
    text = text.strip()
    if SYSTEM_REMINDER_RE.search(text[:100]) or SYSTEM_INJECTED_RE.match(text):
        return None
    return text


def _is_denial(result) -> bool:
    if isinstance(result, str):
        return "denied" in result.lower()[:500]
    if not isinstance(result, dict):
        return False
    result_str = ""
    content = result.get("content", "")
    if isinstance(content, str):
        result_str = content
    elif isinstance(content, list):
        for block in content[:3]:
            if isinstance(block, dict):
                result_str += block.get("text", "") + " "
    result_str += " " + str(result.get("stdout", ""))
    low = result_str.lower()[:500]
    return "denied" in low or "permission denied" in low


def _count_repeated_instructions(messages: list[str], window: int = 5) -> int:
    if len(messages) < 2:
        return 0
    count = 0
    normalized = [set(re.findall(r"\w+", m.lower())) for m in messages]
    for i in range(1, len(normalized)):
        for j in range(max(0, i - window), i):
            if not normalized[i] or not normalized[j]:
                continue
            sim = len(normalized[i] & normalized[j]) / len(normalized[i] | normalized[j])
            if 0.4 < sim < 0.95:
                count += 1
                break
    return count


def _count_corrections_after_hooks(
    hook_turns: list[int], correction_turns: list[int], window: int = 3,
) -> int:
    if not hook_turns or not correction_turns:
        return 0
    correction_set = set(correction_turns)
    return sum(
        1 for ht in hook_turns
        if any(ht + off in correction_set for off in range(1, window + 1))
    )


def _slope(ys: list[float]) -> float:
    n = len(ys)
    xs = list(range(n))
    xm, ym = sum(xs) / n, sum(ys) / n
    denom = sum((x - xm) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denom
