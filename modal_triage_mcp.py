"""Modal Triage MCP — structured status and diagnostics for Modal apps.

Replaces raw `modal app list | grep` + `modal app logs | head` patterns that
produced hallucinated status claims (e.g., "uptime 90m" when it was 10m, missing
crash loops, misreading CUDA OOM as normal completion).

**Ground-truth enforcement:** every tool returns a structured payload with
verified_at (ISO timestamp), uptime_seconds (int), and is_running (bool). Agents
should cite these fields rather than paraphrase free-text logs.

Tools:
- list_apps(state_filter, limit): current app inventory with structured states.
- status(app_id): single-app status — is_running, uptime_seconds, task_count.
- triage(app_id, tail_n): status + extracted fatals + OOM/CUDA signals.
- grep_logs(app_id, pattern, context, max_matches): targeted log search.

Modal CLI must be on PATH. If agent is in genomics/, `uv run --project` is used
automatically via MODAL_CLI env override.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import FastMCP

INSTRUCTIONS = """\
Structured Modal app diagnostics. Use BEFORE claiming a remote job is
running/crashed/completed. Do not paraphrase raw logs — cite the structured fields
(is_running, uptime_seconds, verified_at) returned by these tools.

Tools:
- list_apps(state_filter=None, limit=20) — current apps, structured.
- status(app_id) — single app, is_running + uptime_seconds (never guess from text).
- triage(app_id, tail_n=80) — status + fatal exceptions + OOM/CUDA signals.
- grep_logs(app_id, pattern, context=3, max_matches=20) — targeted log search.

Returns JSON with verified_at timestamp. If you don't see verified_at, treat the
claim as unverified.
"""

mcp = FastMCP("modal-triage", instructions=INSTRUCTIONS)

_MODAL_CLI = os.environ.get(
    "MODAL_CLI",
    str(Path.home() / "Projects" / "genomics" / ".venv" / "bin" / "modal"),
)

_FATAL_PATTERNS = [
    (re.compile(r"^Traceback \(most recent call last\):", re.MULTILINE), "python_traceback"),
    (re.compile(r"\b(ModuleNotFoundError|ImportError): (.+)$", re.MULTILINE), "import_error"),
    (re.compile(r"\b(torch\.cuda\.OutOfMemoryError|CUDA out of memory)", re.IGNORECASE), "cuda_oom"),
    (re.compile(r"\bOOMKilled\b|\bMemory cgroup out of memory\b|\bKilled\b\s*$", re.MULTILINE), "oom_killed"),
    (re.compile(r"\bSIGKILL\b|\bSIGTERM\b"), "signal_kill"),
    (re.compile(r"^\s*raise\s+\w+Error\b", re.MULTILINE), "raised_exception"),
    (re.compile(r"\bconnection (refused|reset|closed)\b", re.IGNORECASE), "connection_error"),
]

_SPAM_LINE = re.compile(
    r"^\s*(Downloading|Installing|Collecting|Resolved|Building wheel|Stored in|"
    r"Requirement already satisfied)\b|^\s*\[\d{4}-\d{2}-\d{2}T.+\] DEBUG\b"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _modal_cli() -> str:
    cli = _MODAL_CLI
    if Path(cli).exists():
        return cli
    found = shutil.which("modal")
    if found:
        return found
    raise RuntimeError(
        f"modal CLI not found. Tried MODAL_CLI={_MODAL_CLI!r} and PATH. "
        "Set MODAL_CLI env var to the correct path."
    )


def _run_modal(args: list[str], timeout: int = 60) -> tuple[int, str, str]:
    cli = _modal_cli()
    result = subprocess.run(
        [cli, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def _app_record(record: dict) -> dict:
    """Normalize a `modal app list --json` record into structured output."""
    created = _parse_iso(record.get("Created at"))
    stopped = _parse_iso(record.get("Stopped at"))
    now = datetime.now(timezone.utc)

    state = (record.get("State") or "").lower()
    is_running = "stopped" not in state and stopped is None

    uptime_seconds: int | None = None
    if created and is_running:
        uptime_seconds = int((now - created).total_seconds())
    elif created and stopped:
        uptime_seconds = int((stopped - created).total_seconds())

    try:
        task_count = int(record.get("Tasks") or 0)
    except (TypeError, ValueError):
        task_count = 0

    return {
        "app_id": record.get("App ID"),
        "description": record.get("Description"),
        "state": record.get("State"),
        "is_running": is_running,
        "task_count": task_count,
        "created_at": record.get("Created at"),
        "stopped_at": record.get("Stopped at"),
        "uptime_seconds": uptime_seconds,
    }


@mcp.tool
def list_apps(state_filter: str | None = None, limit: int = 20) -> str:
    """List Modal apps with structured state and uptime.

    Args:
        state_filter: Optional substring match on State field (e.g., 'ephemeral',
            'stopped', 'deployed'). Case-insensitive.
        limit: Max apps to return (default 20, cap 100).
    """
    limit = max(1, min(int(limit), 100))
    rc, stdout, stderr = _run_modal(["app", "list", "--json"])
    if rc != 0:
        return json.dumps({
            "error": "modal app list failed",
            "returncode": rc,
            "stderr": stderr.strip()[-500:],
            "verified_at": _now_iso(),
        }, indent=2)
    try:
        records = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return json.dumps({
            "error": f"failed to parse modal JSON: {exc}",
            "stdout_head": stdout[:300],
            "verified_at": _now_iso(),
        }, indent=2)

    apps = [_app_record(r) for r in records]
    if state_filter:
        sf = state_filter.lower()
        apps = [a for a in apps if sf in (a.get("state") or "").lower()]
    apps = apps[:limit]

    return json.dumps({
        "verified_at": _now_iso(),
        "total_returned": len(apps),
        "apps": apps,
    }, indent=2)


def _find_record(app_id: str) -> dict | None:
    rc, stdout, _ = _run_modal(["app", "list", "--json"])
    if rc != 0:
        return None
    try:
        for r in json.loads(stdout):
            if r.get("App ID") == app_id or r.get("Description") == app_id:
                return r
    except json.JSONDecodeError:
        return None
    return None


@mcp.tool
def status(app_id: str) -> str:
    """Verified status for a single Modal app. Use this before asserting a job's
    state — output includes is_running (bool) and uptime_seconds (int).

    Args:
        app_id: Modal App ID (ap-...) or unique Description.
    """
    record = _find_record(app_id)
    if record is None:
        return json.dumps({
            "error": f"app not found: {app_id}",
            "verified_at": _now_iso(),
        }, indent=2)
    payload = _app_record(record)
    payload["verified_at"] = _now_iso()
    return json.dumps(payload, indent=2)


def _extract_signals(log_text: str) -> dict:
    signals: dict[str, list[str]] = {}
    for pattern, name in _FATAL_PATTERNS:
        matches = pattern.findall(log_text)
        if matches:
            if isinstance(matches[0], tuple):
                items = [" | ".join(m) for m in matches]
            else:
                items = list(matches)
            signals[name] = items[:5]
    return signals


def _tail_nonspam(log_text: str, n: int) -> list[str]:
    lines = [ln for ln in log_text.splitlines() if ln.strip() and not _SPAM_LINE.match(ln)]
    return lines[-n:]


@mcp.tool
def triage(app_id: str, tail_n: int = 80) -> str:
    """Full triage for a Modal app: status + fatal signals + tail logs.

    Returns structured JSON with:
    - is_running (bool), uptime_seconds (int), verified_at (ISO)
    - signals: dict of detected fatal patterns (traceback, OOM, CUDA, import errors)
    - tail_lines: last N non-spam log lines

    Args:
        app_id: Modal App ID or Description.
        tail_n: Number of tail lines to return (default 80, cap 500).
    """
    tail_n = max(1, min(int(tail_n), 500))

    record = _find_record(app_id)
    if record is None:
        return json.dumps({
            "error": f"app not found: {app_id}",
            "verified_at": _now_iso(),
        }, indent=2)

    resolved_id = record.get("App ID") or app_id

    rc, logs, stderr = _run_modal(["app", "logs", resolved_id], timeout=90)
    log_text = logs if rc == 0 else ""
    log_error = stderr.strip()[-300:] if rc != 0 else None

    base = _app_record(record)
    base.update({
        "verified_at": _now_iso(),
        "signals": _extract_signals(log_text),
        "tail_lines": _tail_nonspam(log_text, tail_n),
        "log_fetch_error": log_error,
    })
    return json.dumps(base, indent=2, default=str)


@mcp.tool
def grep_logs(
    app_id: str,
    pattern: str,
    context: int = 3,
    max_matches: int = 20,
) -> str:
    """Search logs for a pattern. Returns matched lines with N lines of context.

    Args:
        app_id: Modal App ID or Description.
        pattern: Regex pattern. Case-sensitive; use (?i) for insensitive.
        context: Lines of context before/after each match (default 3, cap 10).
        max_matches: Max matches to return (default 20, cap 100).
    """
    context = max(0, min(int(context), 10))
    max_matches = max(1, min(int(max_matches), 100))

    record = _find_record(app_id)
    if record is None:
        return json.dumps({
            "error": f"app not found: {app_id}",
            "verified_at": _now_iso(),
        }, indent=2)
    resolved_id = record.get("App ID") or app_id

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return json.dumps({"error": f"invalid regex: {exc}"}, indent=2)

    rc, logs, stderr = _run_modal(["app", "logs", resolved_id], timeout=90)
    if rc != 0:
        return json.dumps({
            "error": "modal app logs failed",
            "stderr": stderr.strip()[-300:],
            "verified_at": _now_iso(),
        }, indent=2)

    lines = logs.splitlines()
    matches: list[dict] = []
    for i, line in enumerate(lines):
        if regex.search(line):
            lo = max(0, i - context)
            hi = min(len(lines), i + context + 1)
            matches.append({
                "line_no": i,
                "match": line,
                "context": lines[lo:hi],
            })
            if len(matches) >= max_matches:
                break

    return json.dumps({
        "app_id": resolved_id,
        "pattern": pattern,
        "match_count": len(matches),
        "matches": matches,
        "verified_at": _now_iso(),
    }, indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
