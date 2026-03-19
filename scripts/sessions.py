#!/usr/bin/env python3
"""Session search & dispatch infrastructure for Claude Code.

Indexes, searches, and dispatches session transcripts across all projects.
SQLite + FTS5 for keyword/structured queries, optional emb integration for
semantic search.

Usage:
    sessions.py index [--verbose] [--force]
    sessions.py list [filters]
    sessions.py search <query> [--semantic] [filters]
    sessions.py show <uuid-prefix>
    sessions.py dispatch <uuid-prefix> --to session-analyst|model-review|custom

Shared filters: --project, --since, --until, --model, --min-cost, -n
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
RECEIPTS_PATH = CLAUDE_DIR / "session-receipts.jsonl"
DB_PATH = CLAUDE_DIR / "sessions.db"
EMB_JSONL_PATH = CLAUDE_DIR / "sessions-emb.jsonl"
EMB_INDEX_PATH = CLAUDE_DIR / "sessions-emb-index.json"
EMB_PROJECT = Path.home() / "Projects" / "emb"

# Import extract_transcript for show/dispatch
EXTRACT_SCRIPT = Path.home() / "Projects" / "skills" / "session-analyst" / "scripts"

# System-reminder pattern to skip when extracting first user message
SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>", re.IGNORECASE)

# File-touching tool names
FILE_TOOLS = {"Read", "Edit", "Write", "Glob", "Grep", "NotebookEdit"}

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

SCHEMA_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    uuid TEXT PRIMARY KEY,
    slug TEXT,
    project TEXT,
    project_dir TEXT,
    jsonl_path TEXT UNIQUE,
    start_ts TEXT,
    end_ts TEXT,
    model TEXT,
    duration_min REAL,
    cost_usd REAL,
    context_pct INTEGER,
    first_message TEXT,
    content_text TEXT,
    files_touched TEXT,
    files_touched_fts TEXT,
    tools_used TEXT,
    commits TEXT,
    commits_fts TEXT,
    lines_added INTEGER,
    lines_removed INTEGER,
    subagent_count INTEGER,
    transcript_lines INTEGER,
    has_receipt INTEGER DEFAULT 0,
    indexed_at TEXT,
    file_mtime REAL
);
"""

# FTS5 + triggers created separately (must be rebuilt on schema migration)
SCHEMA_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
    uuid UNINDEXED,
    first_message,
    content_text,
    files_touched_fts,
    commits_fts,
    content='sessions',
    content_rowid='rowid',
    tokenize='porter ascii'
);

CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
    INSERT INTO sessions_fts(rowid, uuid, first_message, content_text, files_touched_fts, commits_fts)
    VALUES (new.rowid, new.uuid, new.first_message, new.content_text, new.files_touched_fts, new.commits_fts);
END;

CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, uuid, first_message, content_text, files_touched_fts, commits_fts)
    VALUES ('delete', old.rowid, old.uuid, old.first_message, old.content_text, old.files_touched_fts, old.commits_fts);
END;

CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, uuid, first_message, content_text, files_touched_fts, commits_fts)
    VALUES ('delete', old.rowid, old.uuid, old.first_message, old.content_text, old.files_touched_fts, old.commits_fts);
    INSERT INTO sessions_fts(rowid, uuid, first_message, content_text, files_touched_fts, commits_fts)
    VALUES (new.rowid, new.uuid, new.first_message, new.content_text, new.files_touched_fts, new.commits_fts);
END;
"""

# Max chars for content_text (all user+assistant text per session)
CONTENT_TEXT_MAX = 8000


def get_db() -> sqlite3.Connection:
    from common.db import open_db
    db = open_db(DB_PATH)
    db.executescript(SCHEMA_SESSIONS)
    _migrate_schema(db)
    db.executescript(SCHEMA_FTS)
    return db


def _migrate_schema(db: sqlite3.Connection):
    """Add columns and rebuild FTS if schema changed."""
    cols = {row[1] for row in db.execute("PRAGMA table_info(sessions)").fetchall()}
    if "content_text" not in cols:
        db.execute("ALTER TABLE sessions ADD COLUMN content_text TEXT")
        # Drop old FTS and triggers (will be recreated by SCHEMA_FTS)
        for name in ("sessions_ai", "sessions_ad", "sessions_au"):
            db.execute(f"DROP TRIGGER IF EXISTS {name}")
        db.execute("DROP TABLE IF EXISTS sessions_fts")
        db.commit()
        print("Migrated: added content_text, rebuilt FTS index", file=sys.stderr)


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------

def load_receipts() -> dict[str, dict]:
    """Load all receipts keyed by session UUID."""
    receipts = {}
    if not RECEIPTS_PATH.exists():
        return receipts
    with open(RECEIPTS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                sid = r.get("session")
                if sid:
                    receipts[sid] = r
            except json.JSONDecodeError:
                continue
    return receipts


# ---------------------------------------------------------------------------
# Project name extraction
# ---------------------------------------------------------------------------

from config import extract_project_name


# ---------------------------------------------------------------------------
# JSONL parsing (streaming, per-file)
# ---------------------------------------------------------------------------

def parse_jsonl(path: Path) -> dict:
    """Extract metadata from a session JSONL file. Streaming, fail-open."""
    result = {
        "uuid": path.stem,
        "slug": None,
        "model": None,
        "start_ts": None,
        "end_ts": None,
        "first_message": None,
        "content_parts": [],  # structured text segments for FTS
        "content_len": 0,     # running char count
        "files": set(),
        "tools": set(),
        "subagents": set(),
        "commits": [],
        "transcript_lines": 0,
    }

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                result["transcript_lines"] += 1
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get("type")
                timestamp = obj.get("timestamp")

                if timestamp:
                    if result["start_ts"] is None:
                        result["start_ts"] = timestamp
                    result["end_ts"] = timestamp

                # Slug from any record
                if obj.get("slug") and not result["slug"]:
                    result["slug"] = obj["slug"]

                if msg_type == "user":
                    _extract_user_fields(obj, result)
                elif msg_type == "assistant":
                    _extract_assistant_fields(obj, result)
                elif msg_type == "progress":
                    _extract_progress_fields(obj, result)

    except Exception as e:
        print(f"  WARN: parse error {path.name}: {e}", file=sys.stderr)

    # Build structured content_text from parts
    result["content_text"] = "\n".join(result["content_parts"])[:CONTENT_TEXT_MAX]
    del result["content_parts"]
    del result["content_len"]

    return result


def _append_content(result: dict, prefix: str, text: str, max_per_msg: int = 400):
    """Append a semantically-tagged line to content_parts if under budget."""
    if result["content_len"] >= CONTENT_TEXT_MAX:
        return
    text = text.strip()
    if not text:
        return
    line = f"[{prefix}] {text[:max_per_msg]}"
    result["content_parts"].append(line)
    result["content_len"] += len(line) + 1


def _extract_user_fields(obj: dict, result: dict):
    """Extract first_message and content from user records."""
    # Skip tool_result responses (these are tool outputs, not user messages)
    if obj.get("toolUseResult"):
        return

    content = obj.get("message", {}).get("content", "")
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        text = "\n".join(parts)

    # Skip system-reminder injections
    if not text or SYSTEM_REMINDER_RE.search(text[:100]):
        return

    if result["first_message"] is None:
        result["first_message"] = text[:500]

    _append_content(result, "user", text)


def _extract_assistant_fields(obj: dict, result: dict):
    """Extract model, tools, files, and text content from assistant records."""
    msg = obj.get("message", {})

    if not result["model"]:
        result["model"] = msg.get("model")

    content = msg.get("content", [])
    if not isinstance(content, list):
        return

    for block in content:
        if not isinstance(block, dict):
            continue

        btype = block.get("type")

        # Collect assistant text
        if btype == "text":
            text = block.get("text", "")
            if text.strip():
                _append_content(result, "assistant", text)
            continue

        if btype != "tool_use":
            continue

        name = block.get("name", "")
        result["tools"].add(name)

        inp = block.get("input", {})

        # Log tool usage with key param for searchability
        if name in FILE_TOOLS:
            fp = inp.get("file_path") or inp.get("path") or inp.get("pattern")
            if fp:
                result["files"].add(fp)
                _append_content(result, f"tool:{name}", fp, max_per_msg=200)
        elif name == "Bash":
            cmd = inp.get("command", "")
            _append_content(result, "tool:Bash", cmd, max_per_msg=200)
            if "git commit" in cmd:
                m = re.search(r'-m\s+["\'](.+?)["\']', cmd)
                if m:
                    result["commits"].append(m.group(1)[:120])
        elif name == "Agent":
            desc = inp.get("description", "")
            _append_content(result, "tool:Agent", desc, max_per_msg=200)
        elif name.startswith("mcp__"):
            # MCP tool — log name and query/key param
            query = inp.get("query") or inp.get("question") or inp.get("companyName") or ""
            _append_content(result, f"tool:{name}", query, max_per_msg=200)
        elif name in ("WebSearch", "WebFetch"):
            q = inp.get("query") or inp.get("url") or ""
            _append_content(result, f"tool:{name}", q, max_per_msg=200)


def _extract_progress_fields(obj: dict, result: dict):
    """Extract subagent IDs from progress records."""
    data = obj.get("data", {})
    if data.get("type") == "agent_progress":
        # Agent progress records contain nested message with agentId
        msg = data.get("message", {})
        if isinstance(msg, dict):
            aid = msg.get("agentId") or msg.get("agent_id")
            if aid:
                result["subagents"].add(aid)
        # Also check top-level data
        aid = data.get("agentId") or data.get("agent_id")
        if aid:
            result["subagents"].add(aid)

    # Check for slug in progress data
    if data.get("slug") and not result.get("slug"):
        result["slug"] = data["slug"]


# ---------------------------------------------------------------------------
# Indexer
# ---------------------------------------------------------------------------

def cmd_index(args):
    """Build/update SQLite index from all JSONL files + receipts."""
    db = get_db()
    receipts = load_receipts()
    verbose = args.verbose
    force = args.force

    # Discover all JSONL files, deduplicate by UUID (prefer latest mtime)
    candidates: dict[str, tuple[Path, Path]] = {}  # uuid -> (proj_dir, jsonl_path)
    for proj_dir in sorted(PROJECTS_DIR.iterdir()):
        if not proj_dir.is_dir():
            continue
        for jsonl in proj_dir.glob("*.jsonl"):
            uid = jsonl.stem
            if uid not in candidates or jsonl.stat().st_mtime > candidates[uid][1].stat().st_mtime:
                candidates[uid] = (proj_dir, jsonl)
    all_files = list(candidates.values())

    if verbose:
        print(f"Discovered {len(all_files)} unique sessions across "
              f"{len(set(d for d, _ in all_files))} projects", file=sys.stderr)

    # Get existing index state
    existing = {}
    if not force:
        for row in db.execute("SELECT uuid, file_mtime, has_receipt FROM sessions"):
            existing[row["uuid"]] = (row["file_mtime"], row["has_receipt"])

    indexed = 0
    updated = 0
    skipped = 0
    errors = 0

    for proj_dir, jsonl_path in all_files:
        uuid = jsonl_path.stem
        mtime = jsonl_path.stat().st_mtime
        project_dir_name = proj_dir.name
        project = extract_project_name(project_dir_name)

        # Check if we can skip
        if uuid in existing and not force:
            old_mtime, old_has_receipt = existing[uuid]
            if abs(old_mtime - mtime) < 0.01:
                # File unchanged — but check if receipt appeared
                if not old_has_receipt and uuid in receipts:
                    _update_receipt(db, uuid, receipts[uuid])
                    updated += 1
                    if verbose:
                        print(f"  + receipt: {uuid[:8]}... ({project})", file=sys.stderr)
                else:
                    skipped += 1
                continue

        # Parse the JSONL
        try:
            parsed = parse_jsonl(jsonl_path)
        except Exception as e:
            print(f"  ERROR: {jsonl_path.name}: {e}", file=sys.stderr)
            errors += 1
            continue

        # Merge receipt data if available
        receipt = receipts.get(uuid, {})
        has_receipt = 1 if uuid in receipts else 0

        files_list = sorted(parsed["files"])
        tools_list = sorted(parsed["tools"])
        commits_list = receipt.get("commits", []) or parsed["commits"]

        row = {
            "uuid": uuid,
            "slug": parsed["slug"],
            "project": project,
            "project_dir": project_dir_name,
            "jsonl_path": str(jsonl_path),
            "start_ts": parsed["start_ts"],
            "end_ts": parsed["end_ts"],
            "model": parsed["model"],
            "duration_min": receipt.get("duration_min"),
            "cost_usd": receipt.get("cost_usd"),
            "context_pct": receipt.get("context_pct"),
            "first_message": parsed["first_message"],
            "content_text": parsed["content_text"],
            "files_touched": json.dumps(files_list),
            "files_touched_fts": "\n".join(files_list),
            "tools_used": json.dumps(tools_list),
            "commits": json.dumps(commits_list),
            "commits_fts": "\n".join(commits_list),
            "lines_added": receipt.get("lines_added"),
            "lines_removed": receipt.get("lines_removed"),
            "subagent_count": len(parsed["subagents"]),
            "transcript_lines": parsed["transcript_lines"],
            "has_receipt": has_receipt,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "file_mtime": mtime,
        }

        # INSERT OR REPLACE — triggers handle FTS sync
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        db.execute(f"INSERT OR REPLACE INTO sessions ({cols}) VALUES ({placeholders})",
                   list(row.values()))
        indexed += 1

        if verbose:
            label = f"{uuid[:8]}... ({project})"
            if has_receipt:
                label += f" ${receipt.get('cost_usd', 0):.2f}"
            print(f"  {label}", file=sys.stderr)

    db.commit()

    # G5: Re-check receiptless sessions for new receipts
    if not force:
        receiptless = db.execute(
            "SELECT uuid FROM sessions WHERE has_receipt = 0"
        ).fetchall()
        for row in receiptless:
            uid = row["uuid"]
            if uid in receipts:
                _update_receipt(db, uid, receipts[uid])
                updated += 1
                if verbose:
                    print(f"  + receipt: {uid[:8]}...", file=sys.stderr)
        db.commit()

    # Emit emb JSONL for semantic search
    _emit_emb_jsonl(db)

    total = db.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
    with_receipts = db.execute("SELECT COUNT(*) as c FROM sessions WHERE has_receipt = 1").fetchone()["c"]
    print(f"Indexed: {indexed} new, {updated} receipt-updated, {skipped} skipped, {errors} errors",
          file=sys.stderr)
    print(f"Total: {total} sessions ({with_receipts} with receipts)", file=sys.stderr)


def _update_receipt(db: sqlite3.Connection, uuid: str, receipt: dict):
    """Update a session row with receipt data."""
    commits = receipt.get("commits", [])
    db.execute("""
        UPDATE sessions SET
            duration_min = ?,
            cost_usd = ?,
            context_pct = ?,
            lines_added = ?,
            lines_removed = ?,
            commits = ?,
            commits_fts = ?,
            has_receipt = 1,
            indexed_at = ?
        WHERE uuid = ?
    """, [
        receipt.get("duration_min"),
        receipt.get("cost_usd"),
        receipt.get("context_pct"),
        receipt.get("lines_added"),
        receipt.get("lines_removed"),
        json.dumps(commits) if commits else None,
        "\n".join(commits) if commits else None,
        datetime.now(timezone.utc).isoformat(),
        uuid,
    ])


def _emit_emb_jsonl(db: sqlite3.Connection):
    """Write sessions-emb.jsonl for semantic search via emb."""
    rows = db.execute("""
        SELECT uuid, first_message, project, start_ts, slug, model,
               cost_usd, duration_min, tools_used, subagent_count
        FROM sessions
        WHERE first_message IS NOT NULL
    """).fetchall()

    with open(EMB_JSONL_PATH, "w") as f:
        for row in rows:
            entry = {
                "id": row["uuid"],
                "text": row["first_message"],
                "source": row["project"],
                "date": row["start_ts"],
                "metadata": {
                    k: row[k] for k in ("slug", "model", "cost_usd", "duration_min", "subagent_count")
                    if row[k] is not None
                },
            }
            # Add tools to metadata
            tools = row["tools_used"]
            if tools:
                try:
                    entry["metadata"]["tools_used"] = json.loads(tools)
                except json.JSONDecodeError:
                    pass
            f.write(json.dumps(entry) + "\n")

    print(f"Wrote {len(rows)} entries to {EMB_JSONL_PATH}", file=sys.stderr)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def cmd_list(args):
    """One-line-per-session listing."""
    db = get_db()
    query, params = _build_filter_query(args)
    sql = f"""
        SELECT uuid, slug, project, start_ts, model, cost_usd,
               duration_min, first_message, has_receipt
        FROM sessions
        {query}
        ORDER BY start_ts DESC
        LIMIT ?
    """
    params.append(args.n)
    rows = db.execute(sql, params).fetchall()

    if not rows:
        print("No sessions found.", file=sys.stderr)
        return

    for row in rows:
        uid = row["uuid"][:8]
        proj = (row["project"] or "?")[:12].ljust(12)
        ts = (row["start_ts"] or "")[:10]
        model = _short_model(row["model"])
        cost = f"${row['cost_usd']:.2f}" if row["cost_usd"] else "    "
        dur = f"{row['duration_min']:.0f}m" if row["duration_min"] else "  "
        topic = (row["first_message"] or "")[:60].replace("\n", " ")
        receipt = "*" if row["has_receipt"] else " "

        print(f"{uid} {ts} {proj} {model:>10} {cost:>6} {dur:>4}{receipt} {topic}")


def _short_model(model: str | None) -> str:
    """Shorten model name for display."""
    if not model:
        return ""
    if "opus" in model.lower():
        return "opus"
    if "sonnet" in model.lower():
        return "sonnet"
    if "haiku" in model.lower():
        return "haiku"
    # Return last segment
    parts = model.split("-")
    return parts[-1][:10] if parts else model[:10]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

# FTS5 special chars that act as operators
_FTS5_SPECIAL = re.compile(r'["\-\+\*\(\)\{\}\[\]\^~:]')


def _fts5_sanitize(query: str) -> str:
    """Sanitize user query for FTS5. Quote each token to avoid operator interpretation."""
    # Split into words, quote each one so hyphens/special chars are literal
    tokens = query.split()
    if not tokens:
        return query
    # If any token has special chars, wrap each in double quotes
    if any(_FTS5_SPECIAL.search(t) for t in tokens):
        return " ".join(f'"{t}"' for t in tokens)
    return query


def cmd_search(args):
    """FTS5 keyword search or semantic search via emb."""
    if args.semantic:
        _search_semantic(args)
        return

    db = get_db()
    raw_query = _fts5_sanitize(args.query)

    # --meta: search only first_message/files/commits (skip content_text)
    # default: search all columns including conversation content
    if getattr(args, "meta", False):
        query_text = f"{{first_message files_touched_fts commits_fts}}: {raw_query}"
    else:
        query_text = raw_query

    sql = f"""
        WITH matched AS (
            SELECT rowid, rank
            FROM sessions_fts
            WHERE sessions_fts MATCH ?
        )
        SELECT s.uuid, s.slug, s.project, s.start_ts, s.model,
               s.cost_usd, s.duration_min, s.first_message, s.has_receipt,
               m.rank
        FROM matched m
        JOIN sessions s ON s.rowid = m.rowid
        {_filter_where_suffix(args)}
        ORDER BY m.rank
        LIMIT ?
    """
    params = [query_text] + _filter_params(args) + [args.n]

    try:
        rows = db.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print("Index not built. Run: sessions.py index", file=sys.stderr)
            sys.exit(1)
        raise

    if not rows:
        print(f"No results for '{query_text}'", file=sys.stderr)
        return

    for row in rows:
        uid = row["uuid"][:8]
        proj = (row["project"] or "?")[:12].ljust(12)
        ts = (row["start_ts"] or "")[:10]
        model = _short_model(row["model"])
        cost = f"${row['cost_usd']:.2f}" if row["cost_usd"] else "    "
        topic = (row["first_message"] or "")[:60].replace("\n", " ")
        receipt = "*" if row["has_receipt"] else " "

        print(f"{uid} {ts} {proj} {model:>10} {cost:>6}{receipt} {topic}")


def _search_semantic(args):
    """Semantic search via emb CLI."""
    if not EMB_INDEX_PATH.exists():
        print("Semantic index not built. Run:", file=sys.stderr)
        print(f"  uv run --project {EMB_PROJECT} emb embed {EMB_JSONL_PATH} "
              f"-o {EMB_INDEX_PATH} --chunk", file=sys.stderr)
        sys.exit(1)

    cmd = [
        "uv", "run", "--project", str(EMB_PROJECT),
        "emb", "search", str(EMB_INDEX_PATH), args.query,
        "-k", str(args.n), "--hybrid", "--json",
    ]

    # Source filter for project
    if args.project:
        cmd.extend(["-s", args.project])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        print("emb not found. Install: uv run --project ~/Projects/emb emb --help", file=sys.stderr)
        sys.exit(1)

    if proc.returncode != 0:
        print(f"emb error: {proc.stderr}", file=sys.stderr)
        sys.exit(1)

    # Parse emb JSON output and join with SQLite metadata
    try:
        results = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout)
        return

    if not results:
        print(f"No semantic results for '{args.query}'", file=sys.stderr)
        return

    db = get_db()
    for r in results:
        uid = r.get("id", "")
        score = r.get("score", 0)
        row = db.execute(
            "SELECT project, start_ts, model, cost_usd, first_message, has_receipt "
            "FROM sessions WHERE uuid = ?", [uid]
        ).fetchone()
        if not row:
            continue

        proj = (row["project"] or "?")[:12].ljust(12)
        ts = (row["start_ts"] or "")[:10]
        model = _short_model(row["model"])
        cost = f"${row['cost_usd']:.2f}" if row["cost_usd"] else "    "
        topic = (row["first_message"] or "")[:60].replace("\n", " ")
        receipt = "*" if row["has_receipt"] else " "

        print(f"{uid[:8]} {ts} {proj} {model:>10} {cost:>6}{receipt} [{score:.2f}] {topic}")


# ---------------------------------------------------------------------------
# Show
# ---------------------------------------------------------------------------

def cmd_show(args):
    """Compressed transcript via extract_transcript."""
    db = get_db()
    row = _resolve_uuid(db, args.uuid_prefix)
    if not row:
        return

    jsonl_path = Path(row["jsonl_path"])
    if not jsonl_path.exists():
        print(f"JSONL file not found: {jsonl_path}", file=sys.stderr)
        sys.exit(1)

    # Import extract_transcript
    sys.path.insert(0, str(EXTRACT_SCRIPT))
    try:
        from extract_transcript import process_transcript, format_markdown
    except ImportError:
        print(f"Cannot import extract_transcript from {EXTRACT_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    session_data = process_transcript(jsonl_path)
    markdown = format_markdown([session_data], row["project"] or "unknown")
    print(markdown)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

DISPATCH_TARGETS = {
    "session-analyst": {
        "model": "gemini-3.1-pro-preview",
        "prompt": (
            "Analyze this Claude Code session transcript for behavioral anti-patterns. "
            "Look for: sycophancy (folding under pushback), over-engineering, build-then-undo, "
            "token waste (unnecessary tool calls), failure to pushback on bad ideas, "
            "premature abstraction, and any other quality issues. "
            "Output structured findings with severity, evidence quotes, and suggested mitigations."
        ),
    },
    "model-review": {
        "model": "gemini-3.1-pro-preview",
        "prompt": (
            "Review this Claude Code session transcript. Identify: "
            "1) Technical decisions that could have gone differently, "
            "2) Missed opportunities for better solutions, "
            "3) Quality of reasoning and problem-solving approach, "
            "4) Any factual errors or hallucinations. "
            "Be critical and specific. Quote evidence from the transcript."
        ),
    },
}


def cmd_dispatch(args):
    """Compress + pipe to llmx with metadata frontmatter."""
    db = get_db()
    row = _resolve_uuid(db, args.uuid_prefix)
    if not row:
        return

    jsonl_path = Path(row["jsonl_path"])
    if not jsonl_path.exists():
        print(f"JSONL file not found: {jsonl_path}", file=sys.stderr)
        sys.exit(1)

    # Get compressed transcript
    sys.path.insert(0, str(EXTRACT_SCRIPT))
    try:
        from extract_transcript import process_transcript, format_markdown
    except ImportError:
        print(f"Cannot import extract_transcript from {EXTRACT_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    session_data = process_transcript(jsonl_path)
    transcript_md = format_markdown([session_data], row["project"] or "unknown")

    # Build metadata frontmatter (G10)
    frontmatter = _build_frontmatter(row)

    # Determine target config
    target = args.to
    if target == "custom":
        if not args.prompt:
            print("--prompt required for custom dispatch", file=sys.stderr)
            sys.exit(1)
        config = {
            "model": args.model or "gemini-3.1-pro-preview",
            "prompt": args.prompt,
        }
    elif target in DISPATCH_TARGETS:
        config = DISPATCH_TARGETS[target]
    else:
        print(f"Unknown target: {target}. Use: session-analyst, model-review, custom",
              file=sys.stderr)
        sys.exit(1)

    # Compose full prompt
    full_prompt = f"{config['prompt']}\n\n{frontmatter}\n\n{transcript_md}"

    # Dispatch via llmx
    model = args.model or config["model"]
    cmd = ["llmx", "-m", model, full_prompt]

    print(f"Dispatching {row['uuid'][:8]}... to {target} via {model}...", file=sys.stderr)
    print(f"Transcript: {len(transcript_md):,} chars", file=sys.stderr)

    try:
        proc = subprocess.run(cmd, timeout=300)
        sys.exit(proc.returncode)
    except FileNotFoundError:
        print("llmx not found. Install llmx or dispatch manually.", file=sys.stderr)
        sys.exit(1)


def _build_frontmatter(row: sqlite3.Row) -> str:
    """Build markdown metadata frontmatter for dispatch."""
    lines = ["---", "## Session Metadata"]
    lines.append(f"- **UUID:** {row['uuid']}")
    if row["project"]:
        lines.append(f"- **Project:** {row['project']}")
    if row["start_ts"]:
        lines.append(f"- **Start:** {row['start_ts']}")
    if row["end_ts"]:
        lines.append(f"- **End:** {row['end_ts']}")
    if row["model"]:
        lines.append(f"- **Model:** {row['model']}")
    if row["duration_min"]:
        lines.append(f"- **Duration:** {row['duration_min']:.1f} min")
    if row["cost_usd"]:
        lines.append(f"- **Cost:** ${row['cost_usd']:.2f}")
    if row["context_pct"]:
        lines.append(f"- **Context:** {row['context_pct']}%")
    if row["lines_added"] or row["lines_removed"]:
        lines.append(f"- **Lines:** +{row['lines_added'] or 0} -{row['lines_removed'] or 0}")
    if row["tools_used"]:
        try:
            tools = json.loads(row["tools_used"])
            lines.append(f"- **Tools:** {', '.join(tools)}")
        except json.JSONDecodeError:
            pass
    if row["commits"]:
        try:
            commits = json.loads(row["commits"])
            if commits:
                lines.append(f"- **Commits:** {len(commits)}")
                for c in commits[:5]:
                    lines.append(f"  - {c}")
        except json.JSONDecodeError:
            pass
    if row["subagent_count"]:
        lines.append(f"- **Subagents:** {row['subagent_count']}")
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _resolve_uuid(db: sqlite3.Connection, prefix: str) -> sqlite3.Row | None:
    """Resolve a UUID prefix to a full session row."""
    rows = db.execute(
        "SELECT * FROM sessions WHERE uuid LIKE ?", [prefix + "%"]
    ).fetchall()

    if len(rows) == 0:
        print(f"No session matching '{prefix}'", file=sys.stderr)
        sys.exit(1)
    if len(rows) > 1:
        print(f"Ambiguous prefix '{prefix}' matches {len(rows)} sessions:", file=sys.stderr)
        for r in rows[:10]:
            proj = r["project"] or "?"
            ts = (r["start_ts"] or "")[:10]
            topic = (r["first_message"] or "")[:40].replace("\n", " ")
            print(f"  {r['uuid'][:12]}  {ts}  {proj}  {topic}", file=sys.stderr)
        sys.exit(1)

    return rows[0]


def _build_filter_query(args) -> tuple[str, list]:
    """Build WHERE clause from shared filter args."""
    clauses = []
    params = []

    if getattr(args, "project", None):
        clauses.append("project = ?")
        params.append(args.project)
    if getattr(args, "since", None):
        clauses.append("start_ts >= ?")
        params.append(args.since)
    if getattr(args, "until", None):
        clauses.append("start_ts <= ?")
        params.append(args.until)
    if getattr(args, "model", None):
        clauses.append("model LIKE ?")
        params.append(f"%{args.model}%")
    if getattr(args, "min_cost", None):
        clauses.append("cost_usd >= ?")
        params.append(args.min_cost)

    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params


def _filter_where_suffix(args) -> str:
    """Build WHERE suffix for search queries that already have a WHERE."""
    parts = []
    if getattr(args, "project", None):
        parts.append("s.project = ?")
    if getattr(args, "since", None):
        parts.append("s.start_ts >= ?")
    if getattr(args, "until", None):
        parts.append("s.start_ts <= ?")
    if getattr(args, "model", None):
        parts.append("s.model LIKE ?")
    if getattr(args, "min_cost", None):
        parts.append("s.cost_usd >= ?")

    return ("WHERE " + " AND ".join(parts)) if parts else ""


def _filter_params(args) -> list:
    """Get params matching _filter_where_suffix order."""
    params = []
    if getattr(args, "project", None):
        params.append(args.project)
    if getattr(args, "since", None):
        params.append(args.since)
    if getattr(args, "until", None):
        params.append(args.until)
    if getattr(args, "model", None):
        params.append(f"%{args.model}%")
    if getattr(args, "min_cost", None):
        params.append(args.min_cost)
    return params


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def add_shared_filters(parser: argparse.ArgumentParser):
    """Add shared filter arguments."""
    parser.add_argument("--project", "-p", help="Filter by project name")
    parser.add_argument("--since", help="Sessions after this date (ISO8601)")
    parser.add_argument("--until", help="Sessions before this date (ISO8601)")
    parser.add_argument("--model", help="Filter by model name (substring)")
    parser.add_argument("--min-cost", type=float, help="Minimum cost in USD")
    parser.add_argument("-n", type=int, default=20, help="Max results (default: 20)")


def main():
    parser = argparse.ArgumentParser(
        description="Session search & dispatch for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # index
    p_index = sub.add_parser("index", help="Build/update session index")
    p_index.add_argument("--verbose", "-v", action="store_true")
    p_index.add_argument("--force", "-f", action="store_true", help="Re-index all")

    # list
    p_list = sub.add_parser("list", help="List sessions")
    add_shared_filters(p_list)

    # search
    p_search = sub.add_parser("search", help="Search sessions")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--semantic", action="store_true", help="Use emb semantic search")
    p_search.add_argument("--meta", action="store_true",
                          help="Search metadata only (first message, files, commits)")
    add_shared_filters(p_search)

    # show
    p_show = sub.add_parser("show", help="Show compressed transcript")
    p_show.add_argument("uuid_prefix", help="UUID prefix to show")

    # dispatch
    p_dispatch = sub.add_parser("dispatch", help="Dispatch session for analysis")
    p_dispatch.add_argument("uuid_prefix", help="UUID prefix to dispatch")
    p_dispatch.add_argument("--to", required=True,
                            help="Target: session-analyst, model-review, custom")
    p_dispatch.add_argument("--prompt", help="Custom prompt (required for --to custom)")
    p_dispatch.add_argument("--model", help="Override model")

    args = parser.parse_args()

    commands = {
        "index": cmd_index,
        "list": cmd_list,
        "search": cmd_search,
        "show": cmd_show,
        "dispatch": cmd_dispatch,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
