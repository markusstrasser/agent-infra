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
from datetime import datetime, timedelta
from pathlib import Path

from claude_agent_sdk import create_sdk_mcp_server, tool


def _text_result(text: str, max_result_chars: int = 16000) -> dict:
    """Wrap text in MCP content block with _meta size hint."""
    return {"content": [{"type": "text", "text": text,
            "_meta": {"anthropic/maxResultSizeChars": max_result_chars}}]}

from common.paths import SESSIONS_DB, TRIGGERS_FILE as HOOK_TRIGGERS
IMPROVEMENT_LOG = Path(__file__).resolve().parent.parent / "improvement-log.md"


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def _get_sessions_db() -> sqlite3.Connection:
    from common.db import open_db
    return open_db(SESSIONS_DB)


def _fts5_sanitize(query: str) -> str:
    tokens = query.split()
    if not tokens:
        return query
    special = re.compile(r'["\-\+\*\(\)\{\}\[\]\^~:]')
    if any(special.search(t) for t in tokens):
        return " ".join(f'"{t}"' for t in tokens)
    return query


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


@tool(
    "search_sessions",
    "FTS5 keyword search over past Claude Code sessions. Returns uuid, project, date, model, cost, first_message.",
    {"type": "object", "properties": {
        "query": {"type": "string", "description": "Search keywords"},
        "n": {"type": "integer", "description": "Max results (default 5)", "default": 5},
        "project": {"type": "string", "description": "Filter by project name"},
    }, "required": ["query"]},
)
async def search_sessions(args):
    if not SESSIONS_DB.exists():
        return _text_result("Sessions DB not found. Run: sessions.py index")

    db = _get_sessions_db()
    q = _fts5_sanitize(args["query"])
    n = args.get("n", 5)

    where_extra = ""
    params = [q]
    if args.get("project"):
        where_extra = "AND s.project = ?"
        params.append(args["project"])
    params.append(n)

    sql = f"""
        WITH matched AS (
            SELECT rowid, rank FROM sessions_fts WHERE sessions_fts MATCH ?
        )
        SELECT s.uuid, s.project, s.start_ts, s.model, s.cost_usd,
               s.duration_min, s.first_message, s.files_touched, s.commits
        FROM matched m JOIN sessions s ON s.rowid = m.rowid
        {where_extra}
        ORDER BY m.rank LIMIT ?
    """
    try:
        rows = db.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return _text_result("FTS index not built. Run: sessions.py index")
    finally:
        db.close()

    results = [_row_to_dict(r) for r in rows]
    text = json.dumps(results, indent=2, default=str)
    return _text_result(text, max_result_chars=max(len(text) * 2, 16000))


@tool(
    "get_session",
    "Get full metadata for a session by UUID prefix (first 8 chars).",
    {"type": "object", "properties": {
        "uuid_prefix": {"type": "string", "description": "First 8+ characters of session UUID"},
    }, "required": ["uuid_prefix"]},
)
async def get_session(args):
    if not SESSIONS_DB.exists():
        return _text_result("Sessions DB not found.")

    db = _get_sessions_db()
    prefix = args["uuid_prefix"]
    row = db.execute(
        "SELECT * FROM sessions WHERE uuid LIKE ? LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    db.close()

    if not row:
        return _text_result(f"No session found matching '{prefix}'")

    d = _row_to_dict(row)
    # Truncate large fields (raised from 2000 → 8000 now that _meta allows larger results)
    for field in ("content_text", "files_touched_fts", "commits_fts"):
        if d.get(field) and len(str(d[field])) > 8000:
            d[field] = str(d[field])[:8000] + "..."
    text = json.dumps(d, indent=2, default=str)
    return _text_result(text, max_result_chars=max(len(text) * 2, 32000))


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
