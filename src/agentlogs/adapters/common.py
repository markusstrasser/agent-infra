from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


@dataclass(slots=True)
class DiscoveredSource:
    vendor: str
    source_kind: str
    path: Path


@dataclass(slots=True)
class SourceRecord:
    raw_record_key: str
    raw_record_hash: str
    line_no: int | None = None
    byte_start: int | None = None
    byte_end: int | None = None
    ts_raw: str | None = None


@dataclass(slots=True)
class SessionRow:
    vendor: str
    client: str
    vendor_session_id: str | None = None
    synthetic_session_key: str | None = None
    project_root: str | None = None
    project_slug: str | None = None
    # True iff this session is a subagent/sidechain dispatch (Task/Agent tool spawn),
    # NOT an operator (top-level interactive) session. Derived per-adapter from the
    # raw transcript marker (claude: agent-*.jsonl / subagents/ path, == isSidechain).
    is_subagent: bool = False

    @property
    def lookup_key(self) -> tuple[str, str, str]:
        key = self.vendor_session_id or self.synthetic_session_key or "unknown"
        return (self.vendor, self.client, key)


@dataclass(slots=True)
class RunRow:
    run_id: str
    session_lookup_key: tuple[str, str, str]
    vendor: str
    client: str
    transport: str | None = None
    protocol: str | None = None
    provider_name: str | None = None
    base_url: str | None = None
    cwd: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    status: str | None = None
    model_requested: str | None = None
    model_resolved: str | None = None
    approval_mode: str | None = None
    sandbox_mode: str | None = None
    instruction_hash: str | None = None
    config_hash: str | None = None
    mcp_set_hash: str | None = None
    git_head: str | None = None
    completeness: str | None = None
    completeness_notes: str | None = None


@dataclass(slots=True)
class EventRow:
    event_id: str
    run_id: str
    seq: int
    kind: str
    vendor_kind: str | None = None
    vendor_event_id: str | None = None
    role: str | None = None
    text: str | None = None
    payload: Any = None
    record_key: str | None = None
    ts: str | None = None
    parent_event_id: str | None = None
    correlation_id: str | None = None
    tool_call_id: str | None = None


@dataclass(slots=True)
class ToolCallRow:
    tool_call_id: str
    run_id: str
    tool_name: str
    tool_source: str | None = None
    mcp_server: str | None = None
    ts_start: str | None = None
    ts_end: str | None = None
    args: Any = None
    result: Any = None
    status: str | None = None
    exit_code: int | None = None
    correlation_id: str | None = None
    start_record_key: str | None = None
    end_record_key: str | None = None


@dataclass(slots=True)
class FileTouchRow:
    run_id: str
    path: str
    op: str
    tool_call_id: str | None = None
    record_key: str | None = None


@dataclass(slots=True)
class RunEdgeRow:
    src_run_id: str
    dst_run_id: str
    edge_type: str
    inference_method: str
    confidence: float


@dataclass(slots=True)
class RunConfigRow:
    run_id: str
    instruction_ref: str | None = None
    tools: Any = None
    mcp_servers: Any = None
    metadata: Any = None


@dataclass(slots=True)
class ParsedSource:
    records: list[SourceRecord] = field(default_factory=list)
    sessions: list[SessionRow] = field(default_factory=list)
    runs: list[RunRow] = field(default_factory=list)
    run_edges: list[RunEdgeRow] = field(default_factory=list)
    events: list[EventRow] = field(default_factory=list)
    tool_calls: list[ToolCallRow] = field(default_factory=list)
    file_touches: list[FileTouchRow] = field(default_factory=list)
    run_configs: list[RunConfigRow] = field(default_factory=list)


PATH_KEY_CANDIDATES = (
    "path",
    "file_path",
    "filename",
    "dir_path",
    "csv_path",
    "save_path",
    "output_csv_path",
)

LIST_PATH_KEY_CANDIDATES = ("paths", "files")


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    digest = hashlib.sha1(payload.encode("utf-8", "surrogatepass")).hexdigest()[:16]
    return f"{prefix}{digest}"


def stable_hash(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    else:
        raw = str(value)
    return hashlib.sha256(raw.encode("utf-8", "surrogatepass")).hexdigest()


def utf8_len(value: str) -> int:
    return len(value.encode("utf-8", "surrogatepass"))


def json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def json_loads_maybe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


# isolate-by-default worktrees are named "<repo>-wt<pid>" by claude-launch.sh, so an
# isolated session's cwd basename would otherwise index under a distinct slug. Collapse
# the "-wt<digits>" suffix to the canonical repo slug so worktree sessions attribute to
# their repo. No current slug ends in -wt<digits>, so this is a no-op on existing data.
# (project_root keeps the real worktree path; only the grouping slug is canonicalized.)
_WORKTREE_SLUG_SUFFIX = re.compile(r"-wt\d+$")
# claude --worktree dirs: "<repo>--claude-worktrees-<name>" (also in encoded
# transcript dirnames after -Projects-). Collapse to parent repo slug.
_CLAUDE_WORKTREE_SLUG = re.compile(r"--claude-worktrees-.+$")
# Path form AND Claude encoded project dirnames (Users-alien--cache-llmx-…).
_LLMX_CACHE_MARKERS = (
    ".cache/llmx",
    "/cache/llmx/",
    "-cache-llmx-",
    "--cache-llmx-",
)
_LLMX_ATTRIBUTION = Path.home() / ".cache" / "llmx" / "dispatch-attribution.jsonl"


def canonicalize_project_slug(name: str | None) -> str | None:
    """Collapse worktree / isolate suffixes to the parent repo slug."""
    if not name:
        return None
    slug = name.strip()
    if not slug:
        return None
    # Encoded cache dirnames are not projects — refuse to invent `bare`/`cursor`.
    if any(m in slug for m in ("-cache-llmx-", "--cache-llmx-")):
        return None
    slug = _CLAUDE_WORKTREE_SLUG.sub("", slug)
    slug = _WORKTREE_SLUG_SUFFIX.sub("", slug)
    return slug or None


def _slug_from_llmx_cache_cwd(path: Path) -> str | None:
    """Attribute llmx-cache CLI cwd via durable marker/sidecar (Opus 2026-07-12).

    Prefer `.llmx-caller-cwd` inside the cache dir (unique per caller after
    per-caller subdirs). Sidecar is fallback with a short TTL. Never read
    os.environ — that is the indexer env, not the session's.
    """
    from datetime import datetime, timezone, timedelta

    # 1) Marker file in the cache cwd (or parents up to cache root)
    try:
        cur = path.expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        cur = path
    for cand in (cur, *cur.parents):
        marker = cand / ".llmx-caller-cwd"
        if marker.is_file():
            try:
                caller = marker.read_text(encoding="utf-8").strip().splitlines()[0].strip()
            except OSError:
                caller = ""
            if caller and not any(m in caller for m in (".cache/llmx", "/cache/llmx/")):
                return canonicalize_project_slug(Path(caller).name)
        if cand == cand.parent:
            break

    # 2) Sidecar fallback — last matching cli_cwd within 6h
    caller = _lookup_llmx_caller_cwd(path, max_age_hours=6.0)
    if not caller:
        return None
    try:
        caller_path = Path(caller).expanduser()
    except (OSError, TypeError, ValueError):
        return canonicalize_project_slug(caller)
    text = str(caller_path)
    if any(m in text for m in (".cache/llmx", "/cache/llmx/")):
        return None
    return canonicalize_project_slug(caller_path.name)


def _lookup_llmx_caller_cwd(cli_cwd: Path, *, max_age_hours: float = 6.0) -> str | None:
    """Join durable llmx dispatch-attribution sidecar (not indexer os.environ)."""
    from datetime import datetime, timezone, timedelta

    if not _LLMX_ATTRIBUTION.is_file():
        return None
    try:
        target = str(cli_cwd.expanduser().resolve())
    except (OSError, RuntimeError, ValueError):
        target = str(cli_cwd)
    best: str | None = None
    best_ts: datetime | None = None
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    try:
        lines = _LLMX_ATTRIBUTION.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines[-2000:]:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # truncated/partial line — skip
        if row.get("cli_cwd") != target or not row.get("caller_cwd"):
            continue
        ts_raw = row.get("ts") or ""
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ts < cutoff:
            continue
        if best_ts is None or ts >= best_ts:
            best_ts = ts
            best = str(row["caller_cwd"])
    return best


def slug_from_path(path: str | None) -> str | None:
    if not path:
        return None
    try:
        p = Path(path).expanduser()
    except (OSError, TypeError, ValueError):
        return None
    text = str(p)
    name = p.name
    if any(m in text or m in name for m in _LLMX_CACHE_MARKERS):
        from_side = _slug_from_llmx_cache_cwd(p)
        if from_side:
            return from_side
        # Don't invent a fake project from cache basename (`bare`, `cursor`).
        return None
    return canonicalize_project_slug(p.name)


def text_from_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        parts: list[str] = []
        for key in ("text", "message", "content", "description", "output", "think"):
            value = content.get(key)
            if value:
                parts.append(text_from_content(value))
        return "\n".join(part for part in parts if part).strip()
    if isinstance(content, list):
        parts = [text_from_content(item) for item in content]
        return "\n".join(part for part in parts if part).strip()
    return str(content)


def typed_text_parts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return [text_from_content(content)] if content else []
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
            continue
        if not isinstance(item, dict):
            parts.append(str(item))
            continue
        item_type = item.get("type")
        if item_type in {"text", "input_text", "output_text"}:
            text = item.get("text")
            if text:
                parts.append(str(text))
        elif item_type == "functionResponse":
            parts.append(text_from_content(item))
        elif item_type == "image_url":
            url = item.get("image_url", {}).get("url")
            if url:
                parts.append(url)
        else:
            rendered = text_from_content(item)
            if rendered:
                parts.append(rendered)
    return [part for part in parts if part]


def tool_source_from_name(name: str | None) -> str:
    if name is not None and not isinstance(name, str):
        name = str(name)
    if not name:
        return "unknown"
    if name.startswith("mcp__"):
        return "mcp"
    lower = name.lower()
    if "task" in lower or "subagent" in lower:
        return "delegated"
    return "builtin"


def mcp_server_from_name(name: str | None) -> str | None:
    if name is not None and not isinstance(name, str):
        name = str(name)
    if not name or not name.startswith("mcp__"):
        return None
    parts = name.split("__")
    return parts[1] if len(parts) >= 3 else None


def tool_op_from_name(name: str | None) -> str:
    if name is not None and not isinstance(name, str):
        name = str(name)
    if not name:
        return "unknown"
    lower = name.lower()
    if "delete" in lower or "remove" in lower:
        return "delete"
    if "write" in lower or "create" in lower or "addnote" in lower or "storemedia" in lower:
        return "write"
    if "edit" in lower or "patch" in lower or "update" in lower:
        return "edit"
    if "glob" in lower or "list_directory" in lower or "readfolder" in lower:
        return "glob"
    if "grep" in lower or "search" in lower:
        return "grep"
    if "read" in lower or "view" in lower or "show" in lower:
        return "read"
    return "unknown"


def file_touches_from_tool(
    *,
    run_id: str,
    tool_call_id: str,
    tool_name: str,
    args: Any = None,
    result: Any = None,
    record_key: str | None = None,
) -> list[FileTouchRow]:
    touches: list[FileTouchRow] = []
    seen: set[tuple[str, str]] = set()
    op = tool_op_from_name(tool_name)

    def add(path_value: Any, path_op: str | None = None):
        if path_value in (None, ""):
            return
        if isinstance(path_value, (list, tuple, set)):
            for item in path_value:
                add(item, path_op)
            return
        path = str(path_value).strip()
        if not path:
            return
        key = (path, path_op or op)
        if key in seen:
            return
        seen.add(key)
        touches.append(
            FileTouchRow(
                run_id=run_id,
                tool_call_id=tool_call_id,
                path=path,
                op=path_op or op,
                record_key=record_key,
            )
        )

    for candidate in extract_path_candidates(args):
        add(candidate)
    for candidate in extract_path_candidates(result):
        add(candidate)

    if tool_name == "apply_patch" and isinstance(args, dict):
        patch_text = args.get("patch")
        if isinstance(patch_text, str):
            for match in re.finditer(r"^\*\*\* (Add|Update|Delete) File: (.+)$", patch_text, re.MULTILINE):
                action, path = match.groups()
                action = action.lower()
                if action == "add":
                    add(path, "create")
                elif action == "update":
                    add(path, "edit")
                else:
                    add(path, "delete")
    return touches


def extract_path_candidates(obj: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(obj, dict):
        for key in PATH_KEY_CANDIDATES:
            if key in obj:
                value = obj.get(key)
                if value not in (None, ""):
                    paths.append(str(value))
        for key in LIST_PATH_KEY_CANDIDATES:
            value = obj.get(key)
            if isinstance(value, list):
                for item in value:
                    if item not in (None, ""):
                        paths.append(str(item))
        if "file" in obj and isinstance(obj["file"], dict):
            file_path = obj["file"].get("filePath") or obj["file"].get("path")
            if file_path:
                paths.append(str(file_path))
        if "functionResponse" in obj and isinstance(obj["functionResponse"], dict):
            response = obj["functionResponse"].get("response", {})
            if isinstance(response, dict):
                paths.extend(extract_path_candidates(response))
        for value in obj.values():
            if isinstance(value, (dict, list)):
                paths.extend(extract_path_candidates(value))
    elif isinstance(obj, list):
        for item in obj:
            paths.extend(extract_path_candidates(item))
    return paths


def make_record_key(prefix: str, value: Any, fallback: int) -> str:
    if value not in (None, ""):
        return f"{prefix}:{value}"
    return f"{prefix}:line:{fallback}"


def parse_timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return str(value)


def merge_tool_call(existing: ToolCallRow | None, incoming: ToolCallRow) -> ToolCallRow:
    if existing is None:
        return incoming
    return ToolCallRow(
        tool_call_id=existing.tool_call_id,
        run_id=existing.run_id,
        tool_name=incoming.tool_name or existing.tool_name,
        tool_source=incoming.tool_source or existing.tool_source,
        mcp_server=incoming.mcp_server or existing.mcp_server,
        ts_start=incoming.ts_start or existing.ts_start,
        ts_end=incoming.ts_end or existing.ts_end,
        args=incoming.args if incoming.args is not None else existing.args,
        result=incoming.result if incoming.result is not None else existing.result,
        status=incoming.status or existing.status,
        exit_code=incoming.exit_code if incoming.exit_code is not None else existing.exit_code,
        correlation_id=incoming.correlation_id or existing.correlation_id,
        start_record_key=incoming.start_record_key or existing.start_record_key,
        end_record_key=incoming.end_record_key or existing.end_record_key,
    )

