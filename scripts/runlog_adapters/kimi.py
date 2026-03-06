from __future__ import annotations

import hashlib
import json
import re
import tomllib
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

PARSER_NAME = "kimi"
PARSER_VERSION = "2026-03-05"
CLIENT = "kimi-cli"


def parser_identity() -> tuple[str, str]:
    return PARSER_NAME, PARSER_VERSION


def discover_sources(root: Path | None = None) -> list[DiscoveredSource]:
    base = (root or (Path.home() / ".kimi")).expanduser()
    sessions_root = base / "sessions" if (base / "sessions").exists() else base
    if not sessions_root.exists():
        return []

    def sort_key(path: Path) -> tuple[int, int, str]:
        lowered = path.stem.lower()
        return (
            len(path.parts),
            1 if "_sub_" in lowered or "context_sub_" in lowered else 0,
            str(path),
        )

    sources: list[DiscoveredSource] = []
    for path in sorted(sessions_root.rglob("*.jsonl"), key=sort_key):
        if path.name == "wire.jsonl":
            source_kind = "wire_jsonl"
        elif path.name.startswith("context"):
            source_kind = "context_jsonl"
        else:
            source_kind = "transcript_jsonl"
        sources.append(DiscoveredSource(vendor="kimi", source_kind=source_kind, path=path))
    return sources


def parse_source(source: DiscoveredSource) -> ParsedSource:
    vendor_root = _vendor_root(source.path)
    workdir_map = _load_workdir_map(vendor_root)
    vendor_config = _load_vendor_config(vendor_root)

    workdir_hash = _workdir_hash(source.path)
    project_root = workdir_map.get(workdir_hash)
    project_slug = slug_from_path(project_root)
    session_vendor_id, run_token, is_subagent = _session_and_run_token(source.path)
    run_id = f"kimi:{run_token}"

    bundle = ParsedSource()
    tool_calls: dict[str, ToolCallRow] = {}
    started_at: str | None = None
    ended_at: str | None = None

    with source.path.open() as handle:
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

            if source.source_kind == "wire_jsonl":
                _parse_wire_record(bundle, obj, raw_key, timestamp, run_id, tool_calls)
            else:
                _parse_context_record(bundle, obj, raw_key, timestamp, run_id, tool_calls)

    session = SessionRow(
        vendor="kimi",
        client=CLIENT,
        vendor_session_id=session_vendor_id,
        project_root=project_root,
        project_slug=project_slug,
    )
    bundle.sessions.append(session)
    mcp_servers = vendor_config.get("mcp_servers") or []
    bundle.runs.append(
        RunRow(
            run_id=run_id,
            session_lookup_key=session.lookup_key,
            vendor="kimi",
            client=CLIENT,
            transport="cli",
            protocol=source.source_kind,
            provider_name=vendor_config.get("provider_name"),
            base_url=vendor_config.get("base_url"),
            cwd=project_root,
            started_at=started_at,
            ended_at=ended_at,
            status=_run_status(bundle.events),
            model_requested=vendor_config.get("default_model"),
            model_resolved=vendor_config.get("model_name"),
            mcp_set_hash=stable_hash(mcp_servers),
            config_hash=stable_hash(
                {
                    "default_model": vendor_config.get("default_model"),
                    "workdir_hash": workdir_hash,
                }
            ),
            completeness="full" if source.source_kind != "wire_jsonl" else "partial",
            completeness_notes=None if source.source_kind != "wire_jsonl" else "wire enrichment only",
        )
    )
    bundle.run_configs.append(
        RunConfigRow(
            run_id=run_id,
            tools=sorted({row.tool_name for row in tool_calls.values()}),
            mcp_servers=mcp_servers,
            metadata={
                "workdir_hash": workdir_hash,
                "source_kind": source.source_kind,
                "is_subagent": is_subagent,
            },
        )
    )
    if is_subagent:
        bundle.run_edges.append(
            RunEdgeRow(
                src_run_id=f"kimi:{session_vendor_id}",
                dst_run_id=run_id,
                edge_type="spawned_by",
                inference_method="filename_suffix",
                confidence=0.8,
            )
        )

    bundle.tool_calls.extend(tool_calls.values())
    for index, event in enumerate(bundle.events, 1):
        event.seq = index
    return bundle


def _vendor_root(path: Path) -> Path:
    parts = list(path.parts)
    if "sessions" in parts:
        idx = parts.index("sessions")
        return Path(*parts[:idx])
    return path.parents[1]


def _workdir_hash(path: Path) -> str | None:
    parts = list(path.parts)
    if "sessions" not in parts:
        return None
    idx = parts.index("sessions")
    return parts[idx + 1] if idx + 1 < len(parts) else None


def _load_workdir_map(vendor_root: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    kimi_index = vendor_root / "kimi.json"
    if not kimi_index.exists():
        return mapping
    try:
        data = json.loads(kimi_index.read_text())
    except json.JSONDecodeError:
        return mapping
    for item in data.get("work_dirs", []):
        path = item.get("path")
        if not path:
            continue
        mapping[hashlib.md5(path.encode("utf-8")).hexdigest()] = path
    return mapping


def _load_vendor_config(vendor_root: Path) -> dict[str, object]:
    result = {
        "default_model": None,
        "model_name": None,
        "provider_name": None,
        "base_url": None,
        "mcp_servers": [],
    }
    config_path = vendor_root / "config.toml"
    if config_path.exists():
        with config_path.open("rb") as handle:
            config = tomllib.load(handle)
        default_model = config.get("default_model")
        result["default_model"] = default_model
        if default_model and isinstance(config.get("models"), dict):
            model_cfg = config["models"].get(default_model, {})
            if isinstance(model_cfg, dict):
                result["provider_name"] = model_cfg.get("provider")
                result["model_name"] = model_cfg.get("model")
        provider_name = result.get("provider_name")
        if provider_name and isinstance(config.get("providers"), dict):
            provider_cfg = config["providers"].get(provider_name, {})
            if isinstance(provider_cfg, dict):
                result["base_url"] = provider_cfg.get("base_url")
    mcp_path = vendor_root / "mcp.json"
    if mcp_path.exists():
        try:
            config = json.loads(mcp_path.read_text())
        except json.JSONDecodeError:
            config = {}
        if isinstance(config.get("mcpServers"), dict):
            result["mcp_servers"] = sorted(config["mcpServers"].keys())
    return result


def _session_and_run_token(path: Path) -> tuple[str, str, bool]:
    if path.name in {"context.jsonl", "wire.jsonl"}:
        session_id = path.parent.name
        return session_id, session_id, False
    if path.name.startswith("context_sub_"):
        sub_id = path.stem.split("context_sub_", 1)[1]
        session_id = path.parent.name
        return session_id, f"{session_id}:sub_{sub_id}", True
    if path.name.startswith("context_"):
        session_id = path.parent.name
        return session_id, session_id, False
    match = re.match(r"(.+)_sub_(\d+)$", path.stem)
    if match:
        session_id, sub_id = match.groups()
        return session_id, path.stem, True
    return path.stem, path.stem, False


def _record_key(obj: dict, line_no: int) -> str:
    role = obj.get("role") or obj.get("type")
    explicit_id = obj.get("id") or obj.get("tool_call_id") or obj.get("message", {}).get("type")
    if explicit_id:
        return f"kimi:{line_no}:{role}:{explicit_id}"
    return f"kimi:line:{line_no}"


def _parse_context_record(
    bundle: ParsedSource,
    obj: dict,
    raw_key: str,
    timestamp: str | None,
    run_id: str,
    tool_calls: dict[str, ToolCallRow],
):
    role = obj.get("role")
    if role == "_usage":
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "usage"),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=timestamp,
                kind="token_usage",
                vendor_kind=role,
                role="system",
                text=str(obj.get("token_count")),
                payload=obj,
                record_key=raw_key,
            )
        )
        return
    if role == "_checkpoint":
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "checkpoint"),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=timestamp,
                kind="status_update",
                vendor_kind=role,
                role="system",
                text=f"checkpoint {obj.get('id')}",
                payload=obj,
                record_key=raw_key,
            )
        )
        return
    if role == "user":
        text = "\n".join(typed_text_parts(obj.get("content"))).strip()
        if text:
            bundle.events.append(
                EventRow(
                    event_id=stable_id("evt_", run_id, raw_key, "user"),
                    run_id=run_id,
                    seq=len(bundle.events) + 1,
                    ts=timestamp,
                    kind="user_message",
                    vendor_kind=role,
                    role="user",
                    text=text,
                    payload=obj,
                    record_key=raw_key,
                )
            )
        return
    if role == "assistant":
        text = "\n".join(typed_text_parts(obj.get("content"))).strip()
        if text:
            bundle.events.append(
                EventRow(
                    event_id=stable_id("evt_", run_id, raw_key, "assistant"),
                    run_id=run_id,
                    seq=len(bundle.events) + 1,
                    ts=timestamp,
                    kind="assistant_message",
                    vendor_kind=role,
                    role="assistant",
                    text=text,
                    payload=obj,
                    record_key=raw_key,
                )
            )
        for index, call in enumerate(obj.get("tool_calls") or []):
            native_id = call.get("id") or f"{raw_key}:tool:{index}"
            tool_call_id = f"kimi:{native_id}"
            tool_name = call.get("function", {}).get("name") or call.get("name", "unknown")
            args = json_loads_maybe(call.get("function", {}).get("arguments")) or call.get("args")
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
                    event_id=stable_id("evt_", run_id, raw_key, index, "tool_call"),
                    run_id=run_id,
                    seq=len(bundle.events) + 1,
                    ts=timestamp,
                    kind="tool_call",
                    vendor_kind="tool_call",
                    vendor_event_id=native_id,
                    role="assistant",
                    text=tool_name,
                    payload=call,
                    record_key=raw_key,
                    correlation_id=native_id,
                    tool_call_id=tool_call_id,
                )
            )
        return
    if role == "tool":
        native_id = obj.get("tool_call_id") or raw_key
        tool_call_id = f"kimi:{native_id}"
        existing = tool_calls.get(tool_call_id)
        text = "\n".join(typed_text_parts(obj.get("content"))).strip()
        status = "error" if "error" in text.lower() else "success"
        tool_calls[tool_call_id] = merge_tool_call(
            existing,
            ToolCallRow(
                tool_call_id=tool_call_id,
                run_id=run_id,
                tool_name=existing.tool_name if existing else "unknown",
                ts_end=timestamp,
                result=obj.get("content"),
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
                result=obj,
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
                vendor_kind="tool_result",
                vendor_event_id=native_id,
                role="tool",
                text=text,
                payload=obj,
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
                    vendor_kind="tool_result_error",
                    role="tool",
                    text=text,
                    payload=obj,
                    record_key=raw_key,
                    correlation_id=native_id,
                    tool_call_id=tool_call_id,
                )
            )


def _parse_wire_record(
    bundle: ParsedSource,
    obj: dict,
    raw_key: str,
    timestamp: str | None,
    run_id: str,
    tool_calls: dict[str, ToolCallRow],
):
    message = obj.get("message") or {}
    message_type = obj.get("type") or message.get("type")
    payload = message.get("payload") if isinstance(message, dict) else None

    if message_type == "metadata":
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "metadata"),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=timestamp,
                kind="status_update",
                vendor_kind="metadata",
                role="system",
                text=text_from_content(obj),
                payload=obj,
                record_key=raw_key,
            )
        )
        return
    if message_type == "ApprovalRequest":
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "approval_request"),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=timestamp,
                kind="permission_requested",
                vendor_kind=message_type,
                role="system",
                text=text_from_content(payload) or payload.get("description"),
                payload=payload,
                record_key=raw_key,
                tool_call_id=f"kimi:{payload.get('tool_call_id')}" if isinstance(payload, dict) and payload.get("tool_call_id") else None,
            )
        )
        return
    if message_type == "ApprovalResponse":
        decision = _approval_response_kind(payload)
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "approval_response"),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=timestamp,
                kind=decision,
                vendor_kind=message_type,
                role="system",
                text=text_from_content(payload),
                payload=payload,
                record_key=raw_key,
                tool_call_id=f"kimi:{payload.get('tool_call_id')}" if isinstance(payload, dict) and payload.get("tool_call_id") else None,
            )
        )
        return
    if message_type == "ToolCall":
        payload = payload or {}
        native_id = payload.get("tool_call_id") or payload.get("id") or raw_key
        tool_name = payload.get("name") or payload.get("tool_name") or payload.get("function", {}).get("name") or "unknown"
        args = json_loads_maybe(payload.get("arguments")) or payload.get("args") or payload.get("input")
        tool_call_id = f"kimi:{native_id}"
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
                vendor_kind=message_type,
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
    if message_type == "ToolResult":
        payload = payload or {}
        native_id = payload.get("tool_call_id") or payload.get("id") or raw_key
        tool_call_id = f"kimi:{native_id}"
        existing = tool_calls.get(tool_call_id)
        result = payload.get("return_value") or payload.get("result") or payload
        text = text_from_content(result)
        status = "error" if _is_error_result(result) else "success"
        tool_calls[tool_call_id] = merge_tool_call(
            existing,
            ToolCallRow(
                tool_call_id=tool_call_id,
                run_id=run_id,
                tool_name=existing.tool_name if existing else payload.get("name", "unknown"),
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
                vendor_kind=message_type,
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
                    vendor_kind=message_type,
                    role="tool",
                    text=text,
                    payload=payload,
                    record_key=raw_key,
                    correlation_id=native_id,
                    tool_call_id=tool_call_id,
                )
            )
        return
    if message_type == "StatusUpdate" and isinstance(payload, dict) and payload.get("token_usage"):
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "token_usage"),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=timestamp,
                kind="token_usage",
                vendor_kind=message_type,
                role="system",
                text=text_from_content(payload.get("token_usage")),
                payload=payload,
                record_key=raw_key,
            )
        )
        return

    kind = "error" if message_type == "StepInterrupted" else "status_update"
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
            payload=payload or obj,
            record_key=raw_key,
        )
    )


def _approval_response_kind(payload: object) -> str:
    if not isinstance(payload, dict):
        return "permission_granted"
    raw = json.dumps(payload, sort_keys=True).lower()
    if "auto" in raw:
        return "permission_auto_approved"
    if any(term in raw for term in ("denied", "reject", "declined", "\"approved\":false")):
        return "permission_denied"
    return "permission_granted"


def _is_error_result(result: object) -> bool:
    if isinstance(result, dict):
        if result.get("is_error") or result.get("error"):
            return True
    text = text_from_content(result).lower()
    return "error" in text or "exception" in text


def _run_status(events: list[EventRow]) -> str:
    if any(event.kind == "error" for event in events):
        return "error"
    return "completed"
