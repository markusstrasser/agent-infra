from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
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
    slug_from_path,
    stable_hash,
    stable_id,
    text_from_content,
    tool_source_from_name,
    utf8_len,
)

PARSER_NAME = "kimi"
PARSER_VERSION = "2026-04-21.1"
CLIENT = "kimi-cli"


def parser_identity() -> tuple[str, str]:
    return PARSER_NAME, PARSER_VERSION


def discover_sources(root: Path | None = None) -> list[DiscoveredSource]:
    """Discover Kimi session JSONLs.

    Two layouts seen in the wild:
      - New: ~/.kimi/sessions/<md5(project)>/<session-uuid>{,_sub_N}.jsonl
      - Old: ~/.kimi/sessions/<md5(project)>/<session-uuid>/context.jsonl
             (sibling wire.jsonl has API-wire traffic, not user-facing turns)
    """
    base = (root or (Path.home() / ".kimi" / "sessions")).expanduser()
    if not base.exists():
        return []
    sources: list[DiscoveredSource] = []
    for path in sorted(base.rglob("*.jsonl")):
        # Skip old-layout wire.jsonl — raw API frames, not the turn structure
        # our event model expects. context.jsonl is the transcript.
        if path.name == "wire.jsonl":
            continue
        sources.append(DiscoveredSource(vendor="kimi", source_kind="transcript_jsonl", path=path))
    return sources


def parse_source(source: DiscoveredSource) -> ParsedSource:
    path = source.path
    bundle = ParsedSource()
    tool_calls: dict[str, ToolCallRow] = {}

    # Session identity: new layout uses UUID stem; old layout has
    # <session-uuid>/context.jsonl, so session_id comes from the parent dir.
    if path.name == "context.jsonl":
        session_id = path.parent.name
        project_hash_dir = path.parent.parent.name
        parent_session_id = None
        sub_index = None
    else:
        session_id = path.stem
        project_hash_dir = path.parent.name
        parent_session_id, sub_index = _split_session_id(path.stem)
    is_subagent = sub_index is not None
    run_id = f"kimi:{project_hash_dir}:{session_id}"
    project_root = _project_root_from_hash(project_hash_dir)
    project_slug = slug_from_path(project_root)

    # No timestamps in Kimi JSONLs — derive from file mtime.
    mtime = _file_mtime(path)
    started_at = mtime
    ended_at = mtime
    total_tokens: int | None = None
    last_usage: int | None = None

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
            raw_key = f"kimi:{session_id}:line:{line_no}"
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
            if role == "_checkpoint":
                continue
            if role == "_usage":
                token_count = obj.get("token_count")
                if isinstance(token_count, int):
                    total_tokens = token_count  # monotonic; last wins
                    last_usage = token_count
                    bundle.events.append(
                        EventRow(
                            event_id=stable_id("evt_", run_id, raw_key, "usage"),
                            run_id=run_id,
                            seq=len(bundle.events) + 1,
                            ts=None,
                            kind="token_usage",
                            vendor_kind="_usage",
                            role="system",
                            text=str(token_count),
                            payload=obj,
                            record_key=raw_key,
                        )
                    )
                continue
            if role == "user":
                text = text_from_content(obj.get("content"))
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
                _parse_assistant(bundle, obj, raw_key, run_id, tool_calls)
                continue
            if role == "tool":
                _parse_tool_result(bundle, obj, raw_key, run_id, tool_calls)
                continue

    session = SessionRow(
        vendor="kimi",
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
            vendor="kimi",
            client=CLIENT,
            transport="cli",
            protocol="transcript_jsonl",
            provider_name="moonshot-ai",
            cwd=project_root,
            started_at=started_at,
            ended_at=ended_at,
            status=status,
            approval_mode=None,
            sandbox_mode=None,
            mcp_set_hash=stable_hash(mcp_servers),
            completeness="full",
        )
    )
    bundle.run_configs.append(
        RunConfigRow(
            run_id=run_id,
            tools=sorted({str(row.tool_name) for row in tool_calls.values()}),
            mcp_servers=mcp_servers,
            metadata={
                "is_subagent": is_subagent,
                "sub_index": sub_index,
                "project_hash": project_hash_dir,
                "final_token_count": last_usage,
                "total_token_count": total_tokens,
                "source_kind": source.source_kind,
                "no_timestamps": True,
                "layout": "old" if path.name == "context.jsonl" else "new",
            },
        )
    )
    if is_subagent and parent_session_id:
        bundle.run_edges.append(
            RunEdgeRow(
                src_run_id=f"kimi:{project_hash_dir}:{parent_session_id}",
                dst_run_id=run_id,
                edge_type="spawned_by",
                inference_method="subagent_filename_suffix",
                confidence=0.9,
            )
        )

    bundle.tool_calls.extend(tool_calls.values())
    for index, event in enumerate(bundle.events, 1):
        event.seq = index
    return bundle


def _parse_assistant(
    bundle: ParsedSource,
    obj: dict,
    raw_key: str,
    run_id: str,
    tool_calls: dict[str, ToolCallRow],
):
    content = obj.get("content")
    text_parts: list[str] = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                value = item.get("text")
                if value:
                    text_parts.append(str(value))
            elif isinstance(item, str):
                text_parts.append(item)
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
                payload=obj,
                record_key=raw_key,
            )
        )

    for index, call in enumerate(obj.get("tool_calls") or []):
        if not isinstance(call, dict):
            continue
        native_id = call.get("id") or f"{raw_key}:tool:{index}"
        fn = call.get("function") or {}
        tool_name = fn.get("name") or "unknown"
        args = json_loads_maybe(fn.get("arguments"))
        tool_call_id = f"kimi:{native_id}"
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


def _parse_tool_result(
    bundle: ParsedSource,
    obj: dict,
    raw_key: str,
    run_id: str,
    tool_calls: dict[str, ToolCallRow],
):
    native_id = obj.get("tool_call_id") or raw_key
    tool_call_id = f"kimi:{native_id}"
    existing = tool_calls.get(tool_call_id)
    content = obj.get("content")
    text = text_from_content(content)
    lower = text.lower()
    status = "error" if ("error" in lower or "exception" in lower) else "success"
    tool_calls[tool_call_id] = merge_tool_call(
        existing,
        ToolCallRow(
            tool_call_id=tool_call_id,
            run_id=run_id,
            tool_name=existing.tool_name if existing else _tool_name_from_id(native_id),
            ts_end=None,
            result=content,
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
            result=content,
            record_key=raw_key,
        )
    )
    bundle.events.append(
        EventRow(
            event_id=stable_id("evt_", run_id, raw_key, "tool_result"),
            run_id=run_id,
            seq=len(bundle.events) + 1,
            ts=None,
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
                ts=None,
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


def _split_session_id(stem: str) -> tuple[str | None, int | None]:
    """Return (parent_id, sub_index) for subagent sessions, else (None, None)."""
    if "_sub_" not in stem:
        return None, None
    parent, _, suffix = stem.rpartition("_sub_")
    try:
        return parent, int(suffix)
    except ValueError:
        return None, None


def _project_root_from_hash(dir_hash: str) -> str | None:
    """Reverse the project-path hash by scanning ~/.kimi/kimi.json work_dirs.

    Kimi stores sessions under md5(project_path).hexdigest(). Cache the map
    once per parse_source call lineage (module-level cache).
    """
    cache = _project_map_cache()
    return cache.get(dir_hash)


_PROJECT_MAP: dict[str, str] | None = None


def _project_map_cache() -> dict[str, str]:
    global _PROJECT_MAP
    if _PROJECT_MAP is not None:
        return _PROJECT_MAP
    cache: dict[str, str] = {}
    kimi_json = Path.home() / ".kimi" / "kimi.json"
    if kimi_json.exists():
        try:
            data = json.loads(kimi_json.read_text())
            for entry in data.get("work_dirs") or []:
                path = entry.get("path")
                if not path:
                    continue
                key = hashlib.md5(path.encode()).hexdigest()
                cache[key] = path
        except (json.JSONDecodeError, OSError):
            pass
    _PROJECT_MAP = cache
    return cache


def _file_mtime(path: Path) -> str | None:
    try:
        ts = path.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _tool_name_from_id(native_id: str) -> str:
    """Kimi tool IDs have shape 'ToolName:N' — best-effort extract."""
    if ":" in native_id:
        return native_id.split(":", 1)[0]
    return "unknown"
