#!/usr/bin/env python3
"""Normalize Codex/OpenAI runs into a common receipt schema.

Usage:
    uv run python3 scripts/agent_receipts.py sync-codex [--days N]
    uv run python3 scripts/agent_receipts.py import-openai path/to/responses.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"
CODEX_RECEIPTS = CLAUDE_DIR / "codex-session-receipts.jsonl"
OPENAI_RECEIPTS = CLAUDE_DIR / "openai-response-receipts.jsonl"

BACKGROUND_STATES = {"queued", "in_progress", "completed", "failed", "cancelled"}
SKIP_TASK_PREFIXES = (
    "# AGENTS.md instructions",
    "The user interrupted the previous turn on purpose.",
    "<INSTRUCTIONS>",
    "</INSTRUCTIONS>",
    "<environment_context>",
    "</environment_context>",
    "<permissions instructions>",
    "</permissions instructions>",
)


def parse_ts(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def isoformat_or_empty(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")


def normalize_tags(value) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, str):
        parts = value.replace(",", " ").split()
    elif isinstance(value, (list, tuple, set)):
        parts = []
        for item in value:
            if item is None:
                continue
            parts.extend(str(item).replace(",", " ").split())
    else:
        parts = [str(value)]

    tags = []
    for part in parts:
        tag = str(part).strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def normalize_metadata_tags(metadata: dict | None) -> list[str]:
    if not isinstance(metadata, dict):
        return []
    tags: list[str] = []
    for key in ("project", "task", "task_label", "task_tags", "tags"):
        if key not in metadata:
            continue
        if key in ("task_tags", "tags"):
            tags.extend(normalize_tags(metadata.get(key)))
        else:
            value = str(metadata.get(key, "")).strip()
            if value:
                tags.append(value)

    deduped = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return deduped


def first_task_line(text: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line in {"DO", "OK", "--", "---", "..", "..."}:
            continue
        if len(line) <= 3 and line.isupper():
            continue
        if any(line.startswith(prefix) for prefix in SKIP_TASK_PREFIXES):
            continue
        if line.startswith("{") or line.startswith("["):
            continue
        if line.startswith("<") and line.endswith(">"):
            continue
        return line[:120]
    return ""


def extract_codex_message_text(payload: dict) -> str:
    parts = []
    for item in payload.get("content", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"input_text", "output_text"}:
            text = item.get("text", "")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def count_openai_tool_calls(obj) -> int:
    count = 0
    if isinstance(obj, dict):
        if obj.get("type") in {"function_call", "custom_tool_call", "tool_call", "web_search_call"}:
            count += 1
        for value in obj.values():
            count += count_openai_tool_calls(value)
    elif isinstance(obj, list):
        for item in obj:
            count += count_openai_tool_calls(item)
    return count


def collect_codex_receipts(cutoff: datetime | None = None) -> list[dict]:
    if not CODEX_SESSIONS_DIR.exists():
        return []
    if cutoff is not None and cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)

    receipts = []
    for path in sorted(CODEX_SESSIONS_DIR.rglob("*.jsonl")):
        if cutoff is not None:
            try:
                if datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc) < cutoff:
                    continue
            except OSError:
                pass
        receipt = parse_codex_session(path)
        if receipt is None:
            continue
        if cutoff is not None:
            ts = parse_ts(receipt.get("ts"))
            if ts is not None and ts < cutoff:
                continue
        receipts.append(receipt)
    return receipts


def parse_codex_session(path: Path) -> dict | None:
    session_id = path.stem
    start_ts = None
    end_ts = None
    cwd = ""
    project = ""
    provider = "openai"
    model = ""
    reasoning_effort = ""
    branch = ""
    task_label = ""
    last_user_text = ""
    status = "in_progress"
    usage = {}
    rate_limits = {}
    function_call_count = 0
    web_search_call_count = 0
    custom_tool_call_count = 0

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts = parse_ts(obj.get("timestamp"))
                if ts is not None:
                    start_ts = ts if start_ts is None else min(start_ts, ts)
                    end_ts = ts if end_ts is None else max(end_ts, ts)

                outer_type = obj.get("type")
                payload = obj.get("payload", {})

                if outer_type == "session_meta":
                    session_id = payload.get("id", session_id)
                    cwd = payload.get("cwd", cwd)
                    project = Path(cwd).name if cwd else project
                    provider = payload.get("model_provider", provider)
                    branch = payload.get("git", {}).get("branch", branch)

                elif outer_type == "turn_context":
                    model = payload.get("model", model)
                    reasoning_effort = payload.get("effort", reasoning_effort)
                    cwd = payload.get("cwd", cwd)
                    project = Path(cwd).name if cwd else project

                elif outer_type == "response_item":
                    inner_type = payload.get("type")
                    if inner_type == "function_call":
                        function_call_count += 1
                    elif inner_type == "web_search_call":
                        web_search_call_count += 1
                    elif inner_type == "custom_tool_call":
                        custom_tool_call_count += 1
                    elif inner_type == "message" and payload.get("role") == "user":
                        text = extract_codex_message_text(payload)
                        if text:
                            last_user_text = text
                            derived = first_task_line(text)
                            if derived:
                                task_label = derived

                elif outer_type == "event_msg":
                    inner_type = payload.get("type")
                    if inner_type == "token_count":
                        info = payload.get("info")
                        if not isinstance(info, dict):
                            info = {}
                        usage = info.get("total_token_usage", {})
                        rate_limits = payload.get("rate_limits") or {}
                    elif inner_type == "task_complete":
                        status = "completed"

    except OSError:
        return None

    if not session_id:
        return None

    duration_min = 0.0
    if start_ts is not None and end_ts is not None:
        duration_min = round((end_ts - start_ts).total_seconds() / 60.0, 1)

    tool_call_count = function_call_count + web_search_call_count + custom_tool_call_count
    receipt = {
        "ts": isoformat_or_empty(end_ts or start_ts),
        "run_id": session_id,
        "session": session_id,
        "provider": provider or "openai",
        "source": "codex_cli",
        "project": project,
        "task_label": task_label or first_task_line(last_user_text),
        "task_tags": [],
        "metadata_tags": [project] if project else [],
        "cwd": cwd,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "status": status,
        "background_state": None,
        "duration_min": duration_min,
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "cached_input_tokens": int(usage.get("cached_input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "reasoning_output_tokens": int(usage.get("reasoning_output_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
        "tool_call_count": tool_call_count,
        "function_call_count": function_call_count,
        "web_search_call_count": web_search_call_count,
        "custom_tool_call_count": custom_tool_call_count,
    }

    primary = rate_limits.get("primary") or {}
    secondary = rate_limits.get("secondary") or {}
    if primary:
        receipt["rate_limit_primary_pct"] = float(primary.get("used_percent", 0) or 0)
    if secondary:
        receipt["rate_limit_secondary_pct"] = float(secondary.get("used_percent", 0) or 0)
    if branch:
        receipt["branch"] = branch
    return receipt


def load_openai_receipts(path: Path = OPENAI_RECEIPTS) -> list[dict]:
    return load_jsonl(path)


def iter_openai_objects(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = path.read_text().strip()
    if not raw:
        return []
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return [json.loads(line) for line in raw.splitlines() if line.strip()]
    if isinstance(obj, list):
        return [item for item in obj if isinstance(item, dict)]
    if isinstance(obj, dict):
        return [obj]
    return []


def normalize_openai_response(entry: dict) -> dict | None:
    response = entry.get("response") if isinstance(entry.get("response"), dict) else entry
    if not isinstance(response, dict):
        return None

    response_id = response.get("id") or entry.get("response_id") or ""
    if not response_id:
        return None

    metadata = response.get("metadata")
    if not isinstance(metadata, dict):
        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}

    status = str(response.get("status") or entry.get("status") or "completed")
    created_at = parse_ts(response.get("created_at") or entry.get("created_at"))
    completed_at = parse_ts(
        response.get("completed_at")
        or response.get("finished_at")
        or entry.get("completed_at")
        or entry.get("finished_at")
    )
    duration_min = 0.0
    if created_at and completed_at:
        duration_min = round((completed_at - created_at).total_seconds() / 60.0, 1)

    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    input_details = usage.get("input_tokens_details") if isinstance(usage.get("input_tokens_details"), dict) else {}
    output_details = usage.get("output_tokens_details") if isinstance(usage.get("output_tokens_details"), dict) else {}

    task_tags = normalize_tags(metadata.get("task_tags") or metadata.get("tags"))
    task_label = str(metadata.get("task") or metadata.get("task_label") or metadata.get("name") or "").strip()
    project = str(metadata.get("project") or metadata.get("project_name") or metadata.get("project_tag") or "").strip()

    receipt = {
        "ts": isoformat_or_empty(completed_at or created_at),
        "run_id": response_id,
        "response_id": response_id,
        "provider": "openai",
        "source": "openai_responses",
        "project": project,
        "task_label": task_label,
        "task_tags": task_tags,
        "metadata_tags": normalize_metadata_tags(metadata),
        "model": str(response.get("model", "")),
        "reasoning_effort": str(
            metadata.get("reasoning_effort")
            or (response.get("reasoning") or {}).get("effort", "")
        ),
        "status": status,
        "background_state": status if status in BACKGROUND_STATES else None,
        "duration_min": duration_min,
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "cached_input_tokens": int(input_details.get("cached_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "reasoning_output_tokens": int(output_details.get("reasoning_tokens", 0) or 0),
        "total_tokens": int(
            usage.get("total_tokens")
            or (usage.get("input_tokens", 0) or 0) + (usage.get("output_tokens", 0) or 0)
        ),
        "tool_call_count": count_openai_tool_calls(response.get("output", response)),
        "metadata": metadata,
    }
    return receipt


def import_openai_receipts(paths: list[Path], output: Path, append: bool = True) -> list[dict]:
    existing = {}
    if append:
        for row in load_jsonl(output):
            run_id = row.get("response_id") or row.get("run_id")
            if run_id:
                existing[run_id] = row

    for path in paths:
        for entry in iter_openai_objects(path):
            receipt = normalize_openai_response(entry)
            if receipt is None:
                continue
            run_id = receipt.get("response_id") or receipt.get("run_id")
            existing[run_id] = receipt

    rows = sorted(
        existing.values(),
        key=lambda row: parse_ts(row.get("ts")) or datetime.min.replace(tzinfo=timezone.utc),
    )
    write_jsonl(output, rows)
    return rows


def sync_codex_receipts(output: Path, days: int | None = None) -> list[dict]:
    cutoff = None
    if days is not None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    rows = collect_codex_receipts(cutoff=cutoff)
    write_jsonl(output, rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    codex = sub.add_parser("sync-codex", help="Normalize Codex CLI session logs into receipts.")
    codex.add_argument("--days", type=int, default=None, help="Only include sessions newer than N days.")
    codex.add_argument("--output", type=Path, default=CODEX_RECEIPTS)

    openai = sub.add_parser("import-openai", help="Import stored OpenAI Responses objects into receipts.")
    openai.add_argument("paths", nargs="+", type=Path)
    openai.add_argument("--output", type=Path, default=OPENAI_RECEIPTS)
    openai.add_argument("--replace", action="store_true", help="Replace the output file instead of appending+deduping.")

    args = parser.parse_args()

    if args.command == "sync-codex":
        rows = sync_codex_receipts(args.output, days=args.days)
        print(f"Wrote {len(rows)} Codex receipts to {args.output}")
        return 0

    if args.command == "import-openai":
        rows = import_openai_receipts(args.paths, args.output, append=not args.replace)
        print(f"Wrote {len(rows)} OpenAI receipts to {args.output}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
