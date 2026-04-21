"""In-process MCP server exposing meta infrastructure to orchestrated agents.

Tools:
  search_sessions — FTS5 search over Claude Code session transcripts
  get_session     — session metadata + first_message by UUID prefix
  search_improvement_log — grep improvement-log.md
  get_hook_metrics — hook trigger stats from hook-roi.py data
  list_recent_findings — recent improvement-log entries

Injected via step_options.inject_agent_infra in orchestrator.py.
Runs in-process (McpSdkServerConfig), no subprocess/stdio overhead.
"""

import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from claude_agent_sdk import create_sdk_mcp_server, tool


def _text_result(text: str, max_result_chars: int = 16000) -> dict:
    """Wrap text in MCP content block with _meta size hint."""
    return {"content": [{"type": "text", "text": text,
            "_meta": {"anthropic/maxResultSizeChars": max_result_chars}}]}

from common.paths import TRIGGERS_FILE as HOOK_TRIGGERS

# agentlogs package lives in src/ — add to path so the MCP can import it.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import agentlogs  # noqa: E402

IMPROVEMENT_LOG = Path(__file__).resolve().parent.parent / "improvement-log.md"


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


@tool(
    "search_sessions",
    "FTS5 keyword search across Claude Code + Codex + Gemini sessions. "
    "Returns session_uuid, project, start_ts, model, first_message, matching_events.",
    {"type": "object", "properties": {
        "query": {"type": "string", "description": "Search keywords (FTS5 syntax)"},
        "n": {"type": "integer", "description": "Max results (default 5)", "default": 5},
        "project": {"type": "string", "description": "Filter by project slug"},
        "vendor": {"type": "string", "description": "Filter by vendor (claude/codex/gemini)"},
    }, "required": ["query"]},
)
async def search_sessions(args):
    if not agentlogs.DEFAULT_DB_PATH.exists():
        return _text_result("agentlogs DB not found. Run: agentlogs index")

    db = agentlogs.connect()
    try:
        hits = agentlogs.search_sessions(
            db,
            args["query"],
            vendor=args.get("vendor"),
            project=args.get("project"),
            limit=args.get("n", 5),
        )
    except sqlite3.OperationalError as exc:
        return _text_result(f"agentlogs query error: {exc}")
    finally:
        db.close()

    results = [
        {
            "session_uuid": h.session_uuid,
            "vendor": h.vendor,
            "project_slug": h.project_slug,
            "start_ts": h.start_ts,
            "first_message": h.first_message,
            "matching_events": h.matching_events,
            "snippet": h.snippet,
        }
        for h in hits
    ]
    text = json.dumps(results, indent=2, default=str)
    return _text_result(text, max_result_chars=max(len(text) * 2, 16000))


@tool(
    "get_session",
    "Get session metadata by session_uuid or uuid-prefix. "
    "Returns vendor, project, start/end ts, duration, model, first_message.",
    {"type": "object", "properties": {
        "uuid_prefix": {"type": "string", "description": "Full UUID or first 8+ chars"},
    }, "required": ["uuid_prefix"]},
)
async def get_session(args):
    if not agentlogs.DEFAULT_DB_PATH.exists():
        return _text_result("agentlogs DB not found.")

    db = agentlogs.connect()
    try:
        prefix = args["uuid_prefix"]
        row = agentlogs.get_session(db, prefix)
        if not row:
            # Try LIKE prefix match on session_uuid
            row = db.execute(
                "SELECT * FROM sessions WHERE session_uuid LIKE ? LIMIT 1",
                (f"{prefix}%",),
            ).fetchone()
    finally:
        db.close()

    if not row:
        return _text_result(f"No session found matching '{args['uuid_prefix']}'")

    text = json.dumps(_row_to_dict(row), indent=2, default=str)
    return _text_result(text, max_result_chars=max(len(text) * 2, 16000))


# ---------------------------------------------------------------------------
# Improvement log
# ---------------------------------------------------------------------------

@tool(
    "search_improvement_log",
    "Search improvement-log.md for patterns/findings by keyword. Returns matching sections.",
    {"type": "object", "properties": {
        "query": {"type": "string", "description": "Search keyword or pattern"},
        "n": {"type": "integer", "description": "Max sections to return (default 5)", "default": 5},
    }, "required": ["query"]},
)
async def search_improvement_log(args):
    if not IMPROVEMENT_LOG.exists():
        return {"content": [{"type": "text", "text": "improvement-log.md not found."}]}

    text = IMPROVEMENT_LOG.read_text()
    query = args["query"].lower()
    n = args.get("n", 5)

    # Split by ## headings
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    matches = []
    for section in sections:
        if query in section.lower():
            matches.append(section.strip()[:2000])
            if len(matches) >= n:
                break

    if not matches:
        return _text_result(f"No matches for '{args['query']}'")
    text = "\n\n---\n\n".join(matches)
    return _text_result(text, max_result_chars=max(len(text) * 2, 16000))


@tool(
    "list_recent_findings",
    "List recent improvement-log.md entries (by date). Returns the most recent N sections.",
    {"type": "object", "properties": {
        "days": {"type": "integer", "description": "How many days back (default 7)", "default": 7},
        "n": {"type": "integer", "description": "Max entries (default 10)", "default": 10},
    }},
)
async def list_recent_findings(args):
    if not IMPROVEMENT_LOG.exists():
        return {"content": [{"type": "text", "text": "improvement-log.md not found."}]}

    text = IMPROVEMENT_LOG.read_text()
    n = args.get("n", 10)

    # Split by ## headings, take last N
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    recent = [s.strip()[:1000] for s in sections[-n:] if s.strip()]

    text = "\n\n---\n\n".join(recent)
    return _text_result(text, max_result_chars=max(len(text) * 2, 16000))


# ---------------------------------------------------------------------------
# Hook metrics
# ---------------------------------------------------------------------------

@tool(
    "get_hook_metrics",
    "Get hook trigger stats from hook-triggers.jsonl. Shows total/warn/block counts per hook.",
    {"type": "object", "properties": {
        "hook_name": {"type": "string", "description": "Filter to specific hook (optional)"},
        "days": {"type": "integer", "description": "Look back N days (default 7)", "default": 7},
    }},
)
async def get_hook_metrics(args):
    if not HOOK_TRIGGERS.exists():
        return {"content": [{"type": "text", "text": "No hook triggers file found."}]}

    days = args.get("days", 7)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    hook_filter = args.get("hook_name")

    counts: dict[str, dict[str, int]] = {}
    with open(HOOK_TRIGGERS) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = entry.get("ts", "")
            if ts < cutoff:
                continue
            name = entry.get("hook", entry.get("name", "?"))
            if hook_filter and name != hook_filter:
                continue
            action = entry.get("action", entry.get("decision", "trigger"))
            if name not in counts:
                counts[name] = {"total": 0, "warn": 0, "block": 0}
            counts[name]["total"] += 1
            if action in ("warn", "advisory"):
                counts[name]["warn"] += 1
            elif action in ("block", "denied"):
                counts[name]["block"] += 1

    return _text_result(json.dumps(counts, indent=2))


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

agent_infra_server = create_sdk_mcp_server(
    "agent-infra",
    tools=[search_sessions, get_session, search_improvement_log,
           list_recent_findings, get_hook_metrics],
)
