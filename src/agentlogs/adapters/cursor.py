from __future__ import annotations

import json
from datetime import datetime, timezone
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
    merge_tool_call,
    mcp_server_from_name,
    stable_hash,
    stable_id,
    text_from_content,
    tool_source_from_name,
    utf8_len,
)

PARSER_NAME = "cursor"
PARSER_VERSION = "2026-06-15.1"
CLIENT = "cursor-agent"


def parser_identity() -> tuple[str, str]:
    return PARSER_NAME, PARSER_VERSION


def discover_sources(root: Path | None = None) -> list[DiscoveredSource]:
    """Discover Cursor Agent CLI session JSONLs.

    Layout: ~/.cursor/projects/<project-key>/agent-transcripts/<uuid>/<uuid>.jsonl
    """
    base = (root or (Path.home() / ".cursor" / "projects")).expanduser()
    if not base.exists():
        return []
    sources: list[DiscoveredSource] = []
    for path in sorted(base.glob("*/agent-transcripts/*/*.jsonl")):
        if path.parent.name != path.stem:
            continue
        sources.append(DiscoveredSource(vendor="cursor", source_kind="transcript_jsonl", path=path))
    return sources


def parse_source(source: DiscoveredSource) -> ParsedSource:
    path = source.path
    bundle = ParsedSource()
    tool_calls: dict[str, ToolCallRow] = {}

    session_id = path.stem
    project_dir = path.parents[2].name if len(path.parents) >= 3 else "unknown"
    project_root = _project_root_from_dir(project_dir)
    project_slug = _project_slug_from_dir(project_dir)
    run_id = f"cursor:{project_dir}:{session_id}"

    mtime = _file_mtime(path)
    started_at = mtime
    ended_at = mtime

    with path.open() as handle:
        byte_start = 0
        for line_no, raw_line in enumerate(handle, 1):
            byte_end = byte_start + utf8_len(raw_line)
            raw = raw_line.strip()
            if not raw:
                byte_start = byte_end
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                byte_start = byte_end
                continue

            raw_key = f"cursor:{session_id}:line:{line_no}"
            bundle.records.append(
                SourceRecord(
                    raw_record_key=raw_key,
                    raw_record_hash=stable_hash(raw),
                    line_no=line_no,
                    byte_start=byte_start,
                    byte_end=byte_end,
                    ts_raw=None,
                )
            )
            byte_start = byte_end

            role = obj.get("role")
            message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
            content = message.get("content", obj.get("content"))

            if role == "user":
                text = _text_from_cursor_content(content)
                if text:
                    bundle.events.append(
                        EventRow(
                            event_id=stable_id("evt_", run_id, raw_key, "user"),
                            run_id=run_id,
                            seq=len(bundle.events) + 1,
                            ts=None,
                            kind="user_message",
                            vendor_kind="user",
                            role="user",
                            text=text,
                            payload=obj,
                            record_key=raw_key,
                        )
                    )
                continue

            if role == "assistant":
                _parse_assistant(bundle, content, raw_key, run_id, line_no, tool_calls)
                continue

    session = SessionRow(
        vendor="cursor",
        client=CLIENT,
        vendor_session_id=session_id,
        project_root=project_root,
        project_slug=project_slug,
    )
    bundle.sessions.append(session)

    mcp_servers = sorted({row.mcp_server for row in tool_calls.values() if row.mcp_server})
    status = "error" if any(event.kind == "error" for event in bundle.events) else "completed"

    bundle.runs.append(
        RunRow(
            run_id=run_id,
            session_lookup_key=session.lookup_key,
            vendor="cursor",
            client=CLIENT,
            transport="cli",
            protocol="transcript_jsonl",
            provider_name="cursor",
            cwd=project_root,
            started_at=started_at,
            ended_at=ended_at,
            status=status,
            mcp_set_hash=stable_hash(mcp_servers),
            completeness="partial" if tool_calls and not any(tc.status == "success" for tc in tool_calls.values()) else "full",
            completeness_notes="cursor transcripts omit tool_result events" if tool_calls else None,
        )
    )
    bundle.run_configs.append(
        RunConfigRow(
            run_id=run_id,
            tools=sorted({str(row.tool_name) for row in tool_calls.values()}),
            mcp_servers=mcp_servers,
            metadata={
                "project_dir": project_dir,
                "source_kind": source.source_kind,
                "no_timestamps": True,
            },
        )
    )
    bundle.tool_calls.extend(tool_calls.values())
    for index, event in enumerate(bundle.events, 1):
        event.seq = index
    return bundle


def _parse_assistant(
    bundle: ParsedSource,
    content: object,
    raw_key: str,
    run_id: str,
    line_no: int,
    tool_calls: dict[str, ToolCallRow],
) -> None:
    text_parts: list[str] = []
    if isinstance(content, list):
        for index, item in enumerate(content):
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "text":
                value = item.get("text")
                if value:
                    text_parts.append(str(value))
            elif item_type == "tool_use":
                tool_name = str(item.get("name") or "unknown")
                args = item.get("input")
                native_id = f"{line_no}:{index}"
                tool_call_id = f"cursor:{run_id}:{native_id}"
                tool_calls[tool_call_id] = merge_tool_call(
                    tool_calls.get(tool_call_id),
                    ToolCallRow(
                        tool_call_id=tool_call_id,
                        run_id=run_id,
                        tool_name=tool_name,
                        tool_source=tool_source_from_name(tool_name),
                        mcp_server=mcp_server_from_name(tool_name),
                        ts_start=None,
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
                        ts=None,
                        kind="tool_call",
                        vendor_kind="tool_use",
                        role="assistant",
                        text=tool_name,
                        payload=item,
                        record_key=raw_key,
                        correlation_id=native_id,
                        tool_call_id=tool_call_id,
                    )
                )
    elif isinstance(content, str):
        text_parts.append(content)

    if text_parts:
        bundle.events.append(
            EventRow(
                event_id=stable_id("evt_", run_id, raw_key, "assistant"),
                run_id=run_id,
                seq=len(bundle.events) + 1,
                ts=None,
                kind="assistant_message",
                vendor_kind="assistant",
                role="assistant",
                text="\n".join(text_parts).strip(),
                payload={"content": content},
                record_key=raw_key,
            )
        )


def _text_from_cursor_content(content: object) -> str:
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()
    return text_from_content(content)


def _project_slug_from_dir(dirname: str) -> str:
    if "-Projects-" in dirname:
        return dirname.split("-Projects-", 1)[1]
    return dirname


def _project_root_from_dir(dirname: str) -> str | None:
    if "-Projects-" not in dirname:
        return None
    slug = _project_slug_from_dir(dirname)
    return str(Path.home() / "Projects" / slug)


def _file_mtime(path: Path) -> str:
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ts.replace(microsecond=0).isoformat().replace("+00:00", "Z")
