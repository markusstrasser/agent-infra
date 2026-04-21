from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .common import (
    DiscoveredSource,
    EventRow,
    ParsedSource,
    RunConfigRow,
    RunRow,
    SessionRow,
    SourceRecord,
    ToolCallRow,
    file_touches_from_tool,
    mcp_server_from_name,
    merge_tool_call,
    parse_timestamp,
    stable_hash,
    stable_id,
    text_from_content,
    tool_source_from_name,
)

PARSER_NAME = "gemini"
PARSER_VERSION = "2026-03-05"
CLIENT = "gemini-cli"


def parser_identity() -> tuple[str, str]:
    return PARSER_NAME, PARSER_VERSION


def discover_sources(root: Path | None = None) -> list[DiscoveredSource]:
    base = (root or (Path.home() / ".gemini")).expanduser()
    tmp_root = base / "tmp" if (base / "tmp").exists() else base
    if not tmp_root.exists():
        return []

    chat_hashes: set[Path] = set()
    sources: list[DiscoveredSource] = []
    for path in sorted(tmp_root.rglob("chats/session-*.json")):
        chat_hashes.add(path.parent.parent)
        sources.append(DiscoveredSource(vendor="gemini", source_kind="state_json", path=path))
    for path in sorted(tmp_root.rglob("logs.json")):
        if path.parent in chat_hashes:
            continue
        sources.append(DiscoveredSource(vendor="gemini", source_kind="log_json", path=path))
    return sources


def parse_source(source: DiscoveredSource) -> ParsedSource:
    if source.source_kind == "state_json":
        return _parse_chat_session(source)
    return _parse_logs(source)


def _parse_chat_session(source: DiscoveredSource) -> ParsedSource:
    data = json.loads(source.path.read_text())
    bundle = ParsedSource()
    tool_calls: dict[str, ToolCallRow] = {}
    run_id = f"gemini:{data['sessionId']}"
    seq_by_run = defaultdict(int)

    for index, message in enumerate(data.get("messages", []), 1):
        raw_key = f"gemini:{message.get('id', index)}"
        timestamp = parse_timestamp(message.get("timestamp"))
        bundle.records.append(
            SourceRecord(
                raw_record_key=raw_key,
                raw_record_hash=stable_hash(message),
                line_no=index,
                ts_raw=timestamp,
            )
        )
        message_type = message.get("type")
        if message_type == "user":
            _add_event(
                bundle,
                seq_by_run,
                EventRow(
                    event_id=stable_id("evt_", run_id, raw_key, "user"),
                    run_id=run_id,
                    seq=0,
                    ts=timestamp,
                    kind="user_message",
                    vendor_kind=message_type,
                    role="user",
                    text=str(message.get("content", "")),
                    payload=message,
                    record_key=raw_key,
                ),
            )
            continue
        if message_type != "gemini":
            continue

        content = str(message.get("content", "")).strip()
        if content:
            _add_event(
                bundle,
                seq_by_run,
                EventRow(
                    event_id=stable_id("evt_", run_id, raw_key, "assistant"),
                    run_id=run_id,
                    seq=0,
                    ts=timestamp,
                    kind="assistant_message",
                    vendor_kind=message_type,
                    role="assistant",
                    text=content,
                    payload=message,
                    record_key=raw_key,
                ),
            )
        for call_index, call in enumerate(message.get("toolCalls") or []):
            native_id = call.get("id") or f"{raw_key}:tool:{call_index}"
            tool_call_id = f"gemini:{native_id}"
            tool_name = call.get("name", "unknown")
            args = call.get("args")
            tool_ts = parse_timestamp(call.get("timestamp")) or timestamp
            tool_calls[tool_call_id] = merge_tool_call(
                tool_calls.get(tool_call_id),
                ToolCallRow(
                    tool_call_id=tool_call_id,
                    run_id=run_id,
                    tool_name=tool_name,
                    tool_source=tool_source_from_name(tool_name),
                    mcp_server=mcp_server_from_name(tool_name),
                    ts_start=tool_ts,
                    ts_end=tool_ts,
                    args=args,
                    result=call.get("result"),
                    status=call.get("status"),
                    correlation_id=native_id,
                    start_record_key=raw_key,
                    end_record_key=raw_key,
                ),
            )
            bundle.file_touches.extend(
                file_touches_from_tool(
                    run_id=run_id,
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    args=args,
                    result=call.get("result"),
                    record_key=raw_key,
                )
            )
            _add_event(
                bundle,
                seq_by_run,
                EventRow(
                    event_id=stable_id("evt_", run_id, raw_key, call_index, "tool_call"),
                    run_id=run_id,
                    seq=0,
                    ts=tool_ts,
                    kind="tool_call",
                    vendor_kind="tool_call",
                    vendor_event_id=native_id,
                    role="assistant",
                    text=tool_name,
                    payload=call,
                    record_key=raw_key,
                    correlation_id=native_id,
                    tool_call_id=tool_call_id,
                ),
            )
            _add_event(
                bundle,
                seq_by_run,
                EventRow(
                    event_id=stable_id("evt_", run_id, raw_key, call_index, "tool_result"),
                    run_id=run_id,
                    seq=0,
                    ts=tool_ts,
                    kind="tool_result",
                    vendor_kind="tool_result",
                    vendor_event_id=native_id,
                    role="tool",
                    text=text_from_content(call.get("result")),
                    payload=call.get("result"),
                    record_key=raw_key,
                    correlation_id=native_id,
                    tool_call_id=tool_call_id,
                ),
            )
            if call.get("status") == "error":
                _add_event(
                    bundle,
                    seq_by_run,
                    EventRow(
                        event_id=stable_id("evt_", run_id, raw_key, call_index, "error"),
                        run_id=run_id,
                        seq=0,
                        ts=tool_ts,
                        kind="error",
                        vendor_kind="tool_error",
                        role="tool",
                        text=text_from_content(call.get("result")),
                        payload=call,
                        record_key=raw_key,
                        correlation_id=native_id,
                        tool_call_id=tool_call_id,
                    ),
                )
        if message.get("tokens"):
            _add_event(
                bundle,
                seq_by_run,
                EventRow(
                    event_id=stable_id("evt_", run_id, raw_key, "tokens"),
                    run_id=run_id,
                    seq=0,
                    ts=timestamp,
                    kind="token_usage",
                    vendor_kind="tokens",
                    role="system",
                    text=json.dumps(message["tokens"], sort_keys=True),
                    payload=message["tokens"],
                    record_key=raw_key,
                ),
            )

    session = SessionRow(
        vendor="gemini",
        client=CLIENT,
        vendor_session_id=data["sessionId"],
        project_root=_project_root_for_chat(source.path),
        project_slug=None,
    )
    bundle.sessions.append(session)
    bundle.runs.append(
        RunRow(
            run_id=run_id,
            session_lookup_key=session.lookup_key,
            vendor="gemini",
            client=CLIENT,
            transport="cli",
            protocol="state_json",
            provider_name="google",
            cwd=session.project_root,
            started_at=data.get("startTime"),
            ended_at=data.get("lastUpdated"),
            status="error" if any(event.kind == "error" for event in bundle.events) else "completed",
            model_resolved=_last_model(data.get("messages", [])),
            completeness="full",
        )
    )
    bundle.run_configs.append(
        RunConfigRow(
            run_id=run_id,
            tools=sorted({row.tool_name for row in tool_calls.values()}),
            metadata={"project_hash": data.get("projectHash"), "source_kind": source.source_kind},
        )
    )
    bundle.tool_calls.extend(tool_calls.values())
    return bundle


def _parse_logs(source: DiscoveredSource) -> ParsedSource:
    rows = json.loads(source.path.read_text())
    bundle = ParsedSource()
    seq_by_run = defaultdict(int)
    sessions: dict[str, SessionRow] = {}
    runs: dict[str, RunRow] = {}
    started: dict[str, str] = {}
    ended: dict[str, str] = {}

    for index, row in enumerate(rows, 1):
        session_id = row.get("sessionId")
        if not session_id:
            continue
        run_id = f"gemini:{session_id}"
        timestamp = parse_timestamp(row.get("timestamp"))
        raw_key = f"gemini:{session_id}:{row.get('messageId', index)}"
        bundle.records.append(
            SourceRecord(
                raw_record_key=raw_key,
                raw_record_hash=stable_hash(row),
                line_no=index,
                ts_raw=timestamp,
            )
        )
        if timestamp:
            started[run_id] = timestamp if run_id not in started else min(started[run_id], timestamp)
            ended[run_id] = timestamp if run_id not in ended else max(ended[run_id], timestamp)

        sessions.setdefault(
            session_id,
            SessionRow(vendor="gemini", client=CLIENT, vendor_session_id=session_id),
        )
        runs.setdefault(
            run_id,
            RunRow(
                run_id=run_id,
                session_lookup_key=sessions[session_id].lookup_key,
                vendor="gemini",
                client=CLIENT,
                transport="cli",
                protocol="log_json",
                provider_name="google",
                completeness="partial",
                completeness_notes="logs.json only",
            ),
        )
        kind = "assistant_message" if row.get("type") == "gemini" else "user_message"
        role = "assistant" if kind == "assistant_message" else "user"
        _add_event(
            bundle,
            seq_by_run,
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, kind),
                run_id=run_id,
                seq=0,
                ts=timestamp,
                kind=kind,
                vendor_kind=row.get("type"),
                role=role,
                text=str(row.get("message", "")),
                payload=row,
                record_key=raw_key,
            ),
        )

    bundle.sessions.extend(sessions.values())
    for run_id, run in runs.items():
        run.started_at = started.get(run_id)
        run.ended_at = ended.get(run_id)
        run.status = "completed"
        bundle.runs.append(run)
        bundle.run_configs.append(
            RunConfigRow(
                run_id=run_id,
                metadata={"source_kind": source.source_kind, "sparse": True},
            )
        )
    return bundle


def _add_event(bundle: ParsedSource, seq_by_run: dict[str, int], event: EventRow):
    seq_by_run[event.run_id] += 1
    event.seq = seq_by_run[event.run_id]
    bundle.events.append(event)


def _project_root_for_chat(path: Path) -> str | None:
    project_root_marker = path.parent.parent / ".project_root"
    if project_root_marker.exists():
        return project_root_marker.read_text().strip() or None
    return None


def _last_model(messages: list[dict]) -> str | None:
    for message in reversed(messages):
        model = message.get("model")
        if model:
            return model
    return None
