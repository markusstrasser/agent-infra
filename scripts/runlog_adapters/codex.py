from __future__ import annotations

import json
from pathlib import Path

from .common import (
    DiscoveredSource,
    EventRow,
    ParsedSource,
    RunConfigRow,
    RunEdgeRow,
    RunRow,
    SessionRow,
    SourceRecord,
    ToolCallRow,
    file_touches_from_tool,
    json_loads_maybe,
    mcp_server_from_name,
    merge_tool_call,
    parse_timestamp,
    slug_from_path,
    stable_hash,
    stable_id,
    text_from_content,
    tool_source_from_name,
    typed_text_parts,
    utf8_len,
)

PARSER_NAME = "codex"
PARSER_VERSION = "2026-03-05.1"
CLIENT = "codex-cli"


def parser_identity() -> tuple[str, str]:
    return PARSER_NAME, PARSER_VERSION


def discover_sources(root: Path | None = None) -> list[DiscoveredSource]:
    base = (root or (Path.home() / ".codex" / "sessions")).expanduser()
    if not base.exists():
        return []
    return [
        DiscoveredSource(vendor="codex", source_kind="transcript_jsonl", path=path)
        for path in sorted(base.rglob("*.jsonl"))
    ]


def parse_source(source: DiscoveredSource) -> ParsedSource:
    path = source.path
    bundle = ParsedSource()
    tool_calls: dict[str, ToolCallRow] = {}
    session_id = path.stem
    project_root: str | None = None
    project_slug: str | None = None
    provider_name: str | None = None
    base_url: str | None = None
    model_requested: str | None = None
    model_resolved: str | None = None
    approval_mode: str | None = None
    sandbox_mode: str | None = None
    git_head: str | None = None
    base_instructions: str | None = None
    turn_context_payload: dict | None = None
    source_payload: object | None = None
    started_at: str | None = None
    ended_at: str | None = None

    with path.open() as handle:
        byte_start = 0
        for line_no, raw_line in enumerate(handle, 1):
            byte_end = byte_start + utf8_len(raw_line)
            raw = raw_line.strip()
            if not raw:
                byte_start = byte_end
                continue
            obj = json.loads(raw)
            timestamp = parse_timestamp(obj.get("timestamp"))
            raw_key = _record_key(obj, line_no)
            bundle.records.append(
                SourceRecord(
                    raw_record_key=raw_key,
                    raw_record_hash=stable_hash(raw),
                    line_no=line_no,
                    byte_start=byte_start,
                    byte_end=byte_end,
                    ts_raw=timestamp,
                )
            )
            byte_start = byte_end

            if timestamp:
                started_at = timestamp if started_at is None else min(started_at, timestamp)
                ended_at = timestamp if ended_at is None else max(ended_at, timestamp)

            outer_type = obj.get("type")
            payload = obj.get("payload") or {}

            if outer_type == "session_meta":
                session_id = payload.get("id") or session_id
                project_root = payload.get("cwd") or project_root
                project_slug = slug_from_path(project_root) or project_slug
                provider_name = payload.get("model_provider") or provider_name
                base_url = payload.get("base_url") or base_url
                base_instructions = payload.get("base_instructions", {}).get("text") or base_instructions
                git_head = payload.get("git", {}).get("branch") or git_head
                source_payload = payload.get("source") if payload.get("source") is not None else source_payload
                continue

            if outer_type == "turn_context":
                turn_context_payload = payload
                project_root = payload.get("cwd") or project_root
                project_slug = slug_from_path(project_root) or project_slug
                model_requested = payload.get("model") or model_requested
                model_resolved = payload.get("model") or model_resolved
                approval_mode = payload.get("approval_policy") or approval_mode
                sandbox_mode = _sandbox_mode(payload.get("sandbox_policy")) or sandbox_mode
                continue

            if outer_type == "response_item":
                _parse_response_item(bundle, payload, raw_key, timestamp, tool_calls, run_id=f"codex:{session_id}")
                continue

            if outer_type == "event_msg":
                _parse_event_msg(bundle, payload, raw_key, timestamp, run_id=f"codex:{session_id}")
                continue

            if outer_type == "compacted":
                bundle.events.append(
                    EventRow(
                        event_id=stable_id("evt_", session_id, raw_key, "compacted"),
                        run_id=f"codex:{session_id}",
                        seq=len(bundle.events) + 1,
                        ts=timestamp,
                        kind="status_update",
                        vendor_kind="compacted",
                        role="system",
                        text="context compacted",
                        payload=obj,
                        record_key=raw_key,
                    )
                )

    run_id = f"codex:{session_id}"
    session = SessionRow(
        vendor="codex",
        client=CLIENT,
        vendor_session_id=session_id,
        project_root=project_root,
        project_slug=project_slug,
    )
    bundle.sessions.append(session)
    mcp_servers = sorted({row.mcp_server for row in tool_calls.values() if row.mcp_server})
    bundle.runs.append(
        RunRow(
            run_id=run_id,
            session_lookup_key=session.lookup_key,
            vendor="codex",
            client=CLIENT,
            transport=_source_transport(source_payload) or "cli",
            protocol="transcript_jsonl",
            provider_name=provider_name,
            base_url=base_url,
            cwd=project_root,
            started_at=started_at,
            ended_at=ended_at,
            status=_run_status(bundle.events),
            model_requested=model_requested,
            model_resolved=model_resolved,
            approval_mode=approval_mode,
            sandbox_mode=sandbox_mode,
            instruction_hash=stable_hash({"base_instructions": base_instructions, "turn_context": turn_context_payload}),
            config_hash=stable_hash(
                {
                    "approval_mode": approval_mode,
                    "sandbox_mode": sandbox_mode,
                    "source": source_payload,
                }
            ),
            mcp_set_hash=stable_hash(mcp_servers),
            git_head=git_head,
            completeness="full",
        )
    )
    bundle.run_configs.append(
        RunConfigRow(
            run_id=run_id,
            instruction_ref=stable_hash(base_instructions) if base_instructions else None,
            tools=sorted({str(row.tool_name) for row in tool_calls.values()}),
            mcp_servers=mcp_servers,
            metadata={
                "turn_context": turn_context_payload,
                "base_instructions": base_instructions,
                "session_source": source_payload,
            },
        )
    )
    parent_run_id = _parent_run_id(source_payload)
    if parent_run_id:
        bundle.run_edges.append(
            RunEdgeRow(
                src_run_id=parent_run_id,
                dst_run_id=run_id,
                edge_type="spawned_by",
                inference_method="session_meta_source",
                confidence=0.95,
            )
        )
    bundle.tool_calls.extend(tool_calls.values())
    for index, event in enumerate(bundle.events, 1):
        event.seq = index
    return bundle


def _record_key(obj: dict, line_no: int) -> str:
    payload = obj.get("payload") or {}
    vendor_id = payload.get("call_id") or payload.get("turn_id") or payload.get("id")
    if vendor_id:
        return f"codex:{obj.get('type')}:{line_no}:{vendor_id}"
    return f"codex:line:{line_no}"


def _parse_response_item(
    bundle: ParsedSource,
    payload: dict,
    raw_key: str,
    timestamp: str | None,
    tool_calls: dict[str, ToolCallRow],
    *,
    run_id: str,
):
    inner_type = payload.get("type")
    if inner_type == "message":
        role = payload.get("role")
        text = "\n".join(typed_text_parts(payload.get("content"))).strip()
        if role in {"user", "assistant"} and text:
            bundle.events.append(
                EventRow(
                    event_id=stable_id("evt_", run_id, raw_key, role),
                    run_id=run_id,
                    seq=len(bundle.events) + 1,
                    ts=timestamp,
                    kind="user_message" if role == "user" else "assistant_message",
                    vendor_kind=inner_type,
                    role=role,
                    text=text,
                    payload=payload,
                    record_key=raw_key,
                )
            )
        return

    if inner_type in {"function_call", "web_search_call", "custom_tool_call"}:
        native_id = payload.get("call_id") or payload.get("id") or raw_key
        tool_name = _tool_name(payload.get("name") or payload.get("action") or inner_type)
        args = json_loads_maybe(payload.get("arguments")) or payload.get("args")
        tool_call_id = f"codex:{native_id}"
        tool_calls[tool_call_id] = merge_tool_call(
            tool_calls.get(tool_call_id),
            ToolCallRow(
                tool_call_id=tool_call_id,
                run_id=run_id,
                tool_name=tool_name,
                tool_source=tool_source_from_name(tool_name),
                mcp_server=mcp_server_from_name(tool_name),
                ts_start=timestamp,
                args=args,
                status="started",
                correlation_id=native_id,
                start_record_key=raw_key,
            ),
        )
        bundle.file_touches.extend(
            file_touches_from_tool(
                run_id=run_id,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                args=args,
                record_key=raw_key,
            )
        )
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "tool_call"),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=timestamp,
                kind="tool_call",
                vendor_kind=inner_type,
                vendor_event_id=native_id,
                role="assistant",
                text=tool_name,
                payload=payload,
                record_key=raw_key,
                correlation_id=native_id,
                tool_call_id=tool_call_id,
            )
        )
        return

    if inner_type in {"function_call_output", "custom_tool_call_output"}:
        native_id = payload.get("call_id") or payload.get("id") or raw_key
        tool_call_id = f"codex:{native_id}"
        existing = tool_calls.get(tool_call_id)
        result = payload.get("output")
        text = text_from_content(result)
        status = "error" if _is_error_payload(result) else "success"
        tool_calls[tool_call_id] = merge_tool_call(
            existing,
            ToolCallRow(
                tool_call_id=tool_call_id,
                run_id=run_id,
                tool_name=existing.tool_name if existing else _tool_name(payload.get("name", "unknown")),
                ts_end=timestamp,
                result=result,
                status=status,
                correlation_id=native_id,
                end_record_key=raw_key,
            ),
        )
        bundle.file_touches.extend(
            file_touches_from_tool(
                run_id=run_id,
                tool_call_id=tool_call_id,
                tool_name=tool_calls[tool_call_id].tool_name,
                result=result,
                record_key=raw_key,
            )
        )
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "tool_result"),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=timestamp,
                kind="tool_result",
                vendor_kind=inner_type,
                vendor_event_id=native_id,
                role="tool",
                text=text,
                payload=payload,
                record_key=raw_key,
                correlation_id=native_id,
                tool_call_id=tool_call_id,
            )
        )
        if status == "error":
            bundle.events.append(
                EventRow(
                    event_id=stable_id("evt_", run_id, raw_key, "error"),
                    run_id=run_id,
                    seq=len(bundle.events) + 1,
                    ts=timestamp,
                    kind="error",
                    vendor_kind=inner_type,
                    role="tool",
                    text=text,
                    payload=payload,
                    record_key=raw_key,
                    correlation_id=native_id,
                    tool_call_id=tool_call_id,
                )
            )


def _parse_event_msg(bundle: ParsedSource, payload: dict, raw_key: str, timestamp: str | None, *, run_id: str):
    message_type = payload.get("type")
    if message_type == "token_count":
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "token_count"),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=timestamp,
                kind="token_usage",
                vendor_kind=message_type,
                role="system",
                text=text_from_content(payload),
                payload=payload,
                record_key=raw_key,
            )
        )
        return
    if message_type in {"user_message", "agent_message"}:
        role = "user" if message_type == "user_message" else "assistant"
        text = text_from_content(payload)
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, message_type),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=timestamp,
                kind="user_message" if role == "user" else "assistant_message",
                vendor_kind=message_type,
                role=role,
                text=text,
                payload=payload,
                record_key=raw_key,
            )
        )
        return

    kind = "error" if message_type == "turn_aborted" else "status_update"
    bundle.events.append(
        EventRow(
            event_id=stable_id("evt_", run_id, raw_key, message_type or "status"),
            run_id=run_id,
            seq=len(bundle.events) + 1,
            ts=timestamp,
            kind=kind,
            vendor_kind=message_type,
            role="system",
            text=text_from_content(payload) or message_type,
            payload=payload,
            record_key=raw_key,
        )
    )


def _sandbox_mode(value: object) -> str | None:
    if isinstance(value, dict):
        return value.get("type")
    if value in (None, ""):
        return None
    return str(value)


def _is_error_payload(payload: object) -> bool:
    text = text_from_content(payload).lower()
    if "error" in text or "exception" in text or "denied" in text:
        return True
    if isinstance(payload, dict):
        return bool(payload.get("is_error") or payload.get("error"))
    return False


def _run_status(events: list[EventRow]) -> str:
    if any(event.kind == "error" for event in events):
        return "error"
    if any(event.vendor_kind == "task_complete" for event in events):
        return "completed"
    if any(event.vendor_kind == "turn_aborted" for event in events):
        return "aborted"
    return "completed"


def _tool_name(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("name", "type", "action", "title"):
            if value.get(key):
                return str(value[key])
        return json.dumps(value, sort_keys=True)
    return str(value)


def _source_transport(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    thread_spawn = value.get("subagent", {}).get("thread_spawn")
    if isinstance(thread_spawn, dict):
        return "subagent.thread_spawn"
    if value.get("type"):
        return str(value["type"])
    keys = sorted(str(key) for key in value.keys())
    return ".".join(keys) if keys else None


def _parent_run_id(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    thread_spawn = value.get("subagent", {}).get("thread_spawn")
    if not isinstance(thread_spawn, dict):
        return None
    parent_thread_id = thread_spawn.get("parent_thread_id")
    if not parent_thread_id:
        return None
    return f"codex:{parent_thread_id}"
