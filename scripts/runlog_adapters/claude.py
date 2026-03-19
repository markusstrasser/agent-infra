from __future__ import annotations

import json
from pathlib import Path

from .common import (
    DiscoveredSource,
    EventRow,
    FileTouchRow,
    ParsedSource,
    RunConfigRow,
    RunEdgeRow,
    RunRow,
    SessionRow,
    SourceRecord,
    ToolCallRow,
    file_touches_from_tool,
    mcp_server_from_name,
    merge_tool_call,
    parse_timestamp,
    slug_from_path,
    stable_hash,
    stable_id,
    text_from_content,
    tool_source_from_name,
    utf8_len,
)

PARSER_NAME = "claude"
PARSER_VERSION = "2026-03-05.1"
CLIENT = "claude-code"


def parser_identity() -> tuple[str, str]:
    return PARSER_NAME, PARSER_VERSION


def discover_sources(root: Path | None = None) -> list[DiscoveredSource]:
    from common.paths import PROJECTS_DIR
    base = (root or PROJECTS_DIR).expanduser()
    if not base.exists():
        return []

    main_by_stem: dict[str, Path] = {}
    subagents: list[Path] = []
    for path in sorted(base.rglob("*.jsonl")):
        if "subagents" in path.parts or path.stem.startswith("agent-"):
            subagents.append(path)
            continue
        previous = main_by_stem.get(path.stem)
        if previous is None or path.stat().st_mtime > previous.stat().st_mtime:
            main_by_stem[path.stem] = path

    ordered = sorted(main_by_stem.values(), key=lambda p: (len(p.parts), str(p)))
    ordered.extend(sorted(subagents, key=lambda p: (len(p.parts), str(p))))
    return [DiscoveredSource(vendor="claude", source_kind="transcript_jsonl", path=path) for path in ordered]


def parse_source(source: DiscoveredSource) -> ParsedSource:
    path = source.path
    is_subagent = "subagents" in path.parts or path.stem.startswith("agent-")
    session_vendor_id = _default_session_id(path, is_subagent)
    run_id = f"claude:{path.stem}"

    bundle = ParsedSource()
    tool_calls: dict[str, ToolCallRow] = {}
    project_root: str | None = None
    approval_mode: str | None = None
    branch: str | None = None
    base_url: str | None = None
    model_resolved: str | None = None
    version: str | None = None
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

            project_root = obj.get("cwd") or project_root
            approval_mode = obj.get("permissionMode") or approval_mode
            branch = obj.get("gitBranch") or branch
            version = obj.get("version") or version
            base_url = obj.get("baseUrl") or base_url

            record_type = obj.get("type")
            if record_type == "assistant":
                model_resolved = _parse_assistant_record(bundle, obj, raw_key, run_id, tool_calls) or model_resolved
            elif record_type == "user":
                _parse_user_record(bundle, obj, raw_key, run_id, tool_calls)
            elif record_type in {"progress", "queue-operation", "system", "file-history-snapshot"}:
                _parse_status_record(bundle, obj, raw_key, run_id)

    project_slug = slug_from_path(project_root) or _project_slug_from_path(path)
    session = SessionRow(
        vendor="claude",
        client=CLIENT,
        vendor_session_id=session_vendor_id,
        project_root=project_root,
        project_slug=project_slug,
    )
    bundle.sessions.append(session)
    bundle.runs.append(
        RunRow(
            run_id=run_id,
            session_lookup_key=session.lookup_key,
            vendor="claude",
            client=CLIENT,
            transport="cli",
            protocol="transcript_jsonl",
            provider_name="anthropic",
            base_url=base_url,
            cwd=project_root,
            started_at=started_at,
            ended_at=ended_at,
            status="completed",
            model_resolved=model_resolved,
            approval_mode=approval_mode,
            config_hash=stable_hash(
                {
                    "approval_mode": approval_mode,
                    "branch": branch,
                    "version": version,
                }
            ),
            git_head=branch,
            completeness="full",
        )
    )
    bundle.run_configs.append(
        RunConfigRow(
            run_id=run_id,
            tools=sorted({row.tool_name for row in tool_calls.values()}),
            metadata={
                "git_branch": branch,
                "version": version,
                "slug": project_slug,
                "is_subagent": is_subagent,
            },
        )
    )
    if is_subagent and session_vendor_id and session_vendor_id != path.stem:
        bundle.run_edges.append(
            RunEdgeRow(
                src_run_id=f"claude:{session_vendor_id}",
                dst_run_id=run_id,
                edge_type="spawned_by",
                inference_method="subagent_path",
                confidence=0.75,
            )
        )

    bundle.tool_calls.extend(tool_calls.values())
    for index, event in enumerate(bundle.events, 1):
        event.seq = index
    return bundle


def _record_key(obj: dict, line_no: int) -> str:
    value = obj.get("uuid") or obj.get("messageId")
    return f"claude:{line_no}:{value}" if value else f"claude:line:{line_no}"


def _default_session_id(path: Path, is_subagent: bool) -> str:
    if is_subagent and path.parent.name == "subagents":
        return path.parent.parent.name
    return path.stem


def _next_seq(bundle: ParsedSource) -> int:
    return len(bundle.events) + 1


def _parse_assistant_record(
    bundle: ParsedSource,
    obj: dict,
    raw_key: str,
    run_id: str,
    tool_calls: dict[str, ToolCallRow],
) -> str | None:
    message = obj.get("message", {})
    model = message.get("model")
    text_parts: list[str] = []
    timestamp = parse_timestamp(obj.get("timestamp"))

    for index, item in enumerate(message.get("content") or []):
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "text":
            text = item.get("text")
            if text:
                text_parts.append(str(text))
            continue
        if item_type != "tool_use":
            continue

        native_id = item.get("id") or f"{raw_key}:tool:{index}"
        tool_call_id = f"claude:{native_id}"
        tool_name = item.get("name", "unknown")
        args = item.get("input")
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
                seq=_next_seq(bundle),
                ts=timestamp,
                kind="tool_call",
                vendor_kind=item_type,
                vendor_event_id=native_id,
                role="assistant",
                text=tool_name,
                payload=item,
                record_key=raw_key,
                correlation_id=native_id,
                tool_call_id=tool_call_id,
            )
        )

    if text_parts:
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "assistant"),
                run_id=run_id,
                seq=_next_seq(bundle),
                ts=timestamp,
                kind="assistant_message",
                vendor_kind="assistant",
                vendor_event_id=obj.get("uuid"),
                role="assistant",
                text="\n".join(text_parts).strip(),
                payload=message,
                record_key=raw_key,
            )
        )
    return model


def _parse_user_record(
    bundle: ParsedSource,
    obj: dict,
    raw_key: str,
    run_id: str,
    tool_calls: dict[str, ToolCallRow],
):
    message = obj.get("message", {})
    content = message.get("content")
    timestamp = parse_timestamp(obj.get("timestamp"))

    if obj.get("toolUseResult") or _has_tool_result_items(content):
        result_payload = obj.get("toolUseResult")
        for index, item in enumerate(content or []):
            if not isinstance(item, dict) or item.get("type") != "tool_result":
                continue
            native_id = item.get("tool_use_id") or f"{raw_key}:tool:{index}"
            tool_call_id = f"claude:{native_id}"
            existing = tool_calls.get(tool_call_id)
            tool_name = existing.tool_name if existing else "unknown"
            result = result_payload or item
            text = text_from_content(item.get("content")) or text_from_content(result)
            status = "error" if "error" in text.lower() else "success"
            tool_calls[tool_call_id] = merge_tool_call(
                existing,
                ToolCallRow(
                    tool_call_id=tool_call_id,
                    run_id=run_id,
                    tool_name=tool_name,
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
                    event_id=stable_id("evt_", run_id, raw_key, index, "tool_result"),
                    run_id=run_id,
                    seq=_next_seq(bundle),
                    ts=timestamp,
                    kind="tool_result",
                    vendor_kind="tool_result",
                    vendor_event_id=native_id,
                    role="tool",
                    text=text,
                    payload=result,
                    record_key=raw_key,
                    correlation_id=native_id,
                    tool_call_id=tool_call_id,
                )
            )
            if status == "error":
                bundle.events.append(
                    EventRow(
                        event_id=stable_id("evt_", run_id, raw_key, index, "error"),
                        run_id=run_id,
                        seq=_next_seq(bundle),
                        ts=timestamp,
                        kind="error",
                        vendor_kind="tool_result_error",
                        role="tool",
                        text=text,
                        payload=result,
                        record_key=raw_key,
                        correlation_id=native_id,
                        tool_call_id=tool_call_id,
                    )
                )
        return

    text = text_from_content(content)
    if text:
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "user"),
                run_id=run_id,
                seq=_next_seq(bundle),
                ts=timestamp,
                kind="user_message",
                vendor_kind="user",
                vendor_event_id=obj.get("uuid"),
                role="user",
                text=text,
                payload=message,
                record_key=raw_key,
            )
        )


def _parse_status_record(bundle: ParsedSource, obj: dict, raw_key: str, run_id: str):
    record_type = obj.get("type")
    payload = obj.get("data") or obj.get("message") or obj.get("snapshot") or obj
    text = text_from_content(payload)
    kind = _permission_kind(payload, text) or ("error" if record_type == "system" and "error" in text.lower() else "status_update")
    vendor_kind = payload.get("type") if isinstance(payload, dict) else record_type
    bundle.events.append(
        EventRow(
            event_id=stable_id("evt_", run_id, raw_key, record_type),
            run_id=run_id,
            seq=_next_seq(bundle),
            ts=parse_timestamp(obj.get("timestamp")),
            kind=kind,
            vendor_kind=vendor_kind or record_type,
            vendor_event_id=obj.get("uuid"),
            role="system",
            text=text or record_type,
            payload=payload,
            record_key=raw_key,
        )
    )


def _has_tool_result_items(content: object) -> bool:
    return isinstance(content, list) and any(isinstance(item, dict) and item.get("type") == "tool_result" for item in content)


def _permission_kind(payload: object, text: str) -> str | None:
    raw = json.dumps(payload, sort_keys=True) if isinstance(payload, dict) else text
    lower = raw.lower()
    if "permission denied" in lower or "approval denied" in lower:
        return "permission_denied"
    if "approval granted" in lower or "permission granted" in lower:
        return "permission_granted"
    if "approval request" in lower or "permission request" in lower:
        return "permission_requested"
    if "auto approved" in lower or "bypasspermissions" in lower:
        return "permission_auto_approved"
    return None


def _project_slug_from_path(path: Path) -> str | None:
    for part in path.parts:
        if "-Projects-" in part:
            return part.split("-Projects-", 1)[1]
    return None
