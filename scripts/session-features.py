#!/usr/bin/env python3
"""Extract structured epistemic features from Claude Code session transcripts.

Data exhaust logging for trajectory-level calibration (ACC-lite). Reads JSONL
session files and outputs behavioral features per session.

Usage:
    session-features.py --session UUID
    session-features.py --today
    session-features.py --days 7 --output artifacts/epistemic-metrics.jsonl
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import extract_project_name

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

from common.paths import PROJECTS_DIR

# Tools that count as "search"
SEARCH_TOOLS = {
    "Grep", "Glob", "WebSearch", "WebFetch",
    "mcp__brave-search__brave_web_search",
    "mcp__brave-search__brave_local_search",
    "mcp__exa__web_search_exa",
    "mcp__exa__web_search_advanced_exa",
    "mcp__exa__crawling_exa",
    "mcp__exa__company_research_exa",
    "mcp__exa__people_search_exa",
    "mcp__perplexity__perplexity_search",
    "mcp__perplexity__perplexity_ask",
    "mcp__perplexity__perplexity_reason",
    "mcp__perplexity__perplexity_research",
    "mcp__firecrawl__firecrawl_search",
    "mcp__firecrawl__firecrawl_scrape",
    "mcp__scite__search_literature",
    "mcp__paper-search__search_arxiv",
    "mcp__paper-search__search_pubmed",
    "mcp__paper-search__search_google_scholar",
    "mcp__paper-search__search_biorxiv",
    "mcp__paper-search__search_medrxiv",
    "mcp__research__search_papers",
    "mcp__research__ask_papers",
    "mcp__research__verify_claim",
    "mcp__meta-knowledge__search_meta",
    "mcp__context7__resolve-library-id",
    "mcp__context7__query-docs",
}

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}

# Error indicators in tool results
ERROR_PATTERNS = re.compile(
    r"error|traceback|exception|failed|ENOENT|EPERM|"
    r"command not found|No such file|Permission denied|"
    r"Exit code [1-9]",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# JSONL Parsing — extract features in a single pass
# ---------------------------------------------------------------------------

def extract_features(path: Path) -> dict:
    """Extract all behavioral features from a session JSONL file."""
    # Accumulators
    tool_calls = []  # (name, input_dict)
    tool_results = []  # raw result dicts
    assistant_lengths = []
    timestamps = []
    files_read = set()
    session_id = None
    model = None

    # For backtrack detection: track tool calls that follow errors
    last_tool_errored = False
    last_tool_target = None  # file path or query
    backtrack_count = 0

    # For query reformulation: track search queries
    search_queries = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            ts = obj.get("timestamp")
            if ts:
                timestamps.append(ts)

            if not session_id:
                session_id = obj.get("sessionId")

            msg_type = obj.get("type")

            # --- Assistant messages: extract tool_use blocks and text ---
            if msg_type == "assistant":
                msg = obj.get("message", {})
                if not model:
                    model = msg.get("model")

                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue

                turn_text_len = 0
                for block in content:
                    if not isinstance(block, dict):
                        continue

                    if block.get("type") == "text":
                        turn_text_len += len(block.get("text", ""))

                    elif block.get("type") == "tool_use":
                        name = block.get("name", "")
                        inp = block.get("input", {})
                        tool_calls.append((name, inp))

                        # Track file reads
                        if name == "Read":
                            fp = inp.get("file_path", "")
                            if fp:
                                files_read.add(fp)

                        # Extract target for backtrack detection
                        target = _tool_target(name, inp)

                        # Check if this is a backtrack (same target after error)
                        if last_tool_errored and target and target == last_tool_target:
                            backtrack_count += 1

                        last_tool_target = target
                        last_tool_errored = False

                        # Collect search queries for reformulation detection
                        if name in SEARCH_TOOLS:
                            query = _extract_query(name, inp)
                            if query:
                                search_queries.append(query)

                if turn_text_len > 0:
                    assistant_lengths.append(turn_text_len)

            # --- Tool results: detect errors ---
            elif msg_type == "user" and obj.get("toolUseResult"):
                result = obj["toolUseResult"]
                tool_results.append(result)
                if _is_error_result(result):
                    last_tool_errored = True

    # --- Compute features ---
    tool_call_count = len(tool_calls)
    tool_failure_count = sum(1 for r in tool_results if _is_error_result(r))
    tool_names = Counter(name for name, _ in tool_calls)

    # Duration
    duration_minutes = None
    if len(timestamps) >= 2:
        try:
            t0 = _parse_ts(timestamps[0])
            t1 = _parse_ts(timestamps[-1])
            if t0 and t1:
                duration_minutes = round((t1 - t0).total_seconds() / 60, 1)
        except Exception:
            pass

    # Query reformulation: pairs of search queries with high similarity
    reformulation_count = _count_reformulations(search_queries)

    # Project from path
    project_dir = path.parent.name
    project = extract_project_name(project_dir)

    # Date from first timestamp
    date = None
    if timestamps:
        date = timestamps[0][:10]

    return {
        "session_id": session_id or path.stem,
        "project": project,
        "date": date,
        "model": model,
        "tool_call_count": tool_call_count,
        "tool_failure_count": tool_failure_count,
        "tool_failure_rate": round(tool_failure_count / tool_call_count, 3) if tool_call_count else 0.0,
        "backtrack_count": backtrack_count,
        "query_reformulation_count": reformulation_count,
        "unique_files_read": len(files_read),
        "total_assistant_turns": len(assistant_lengths),
        "mean_assistant_length": round(sum(assistant_lengths) / len(assistant_lengths), 0) if assistant_lengths else 0,
        "search_tool_count": sum(tool_names.get(t, 0) for t in SEARCH_TOOLS),
        "edit_count": sum(tool_names.get(t, 0) for t in EDIT_TOOLS),
        "session_duration_minutes": duration_minutes,
    }


def _tool_target(name: str, inp: dict) -> str | None:
    """Extract the primary target (file path or query) from a tool call."""
    if name in ("Read", "Edit", "Write", "NotebookEdit"):
        return inp.get("file_path")
    if name == "Bash":
        return inp.get("command", "")[:100]
    if name in ("Grep", "Glob"):
        return inp.get("pattern", "") + "|" + inp.get("path", "")
    # Search tools — use query
    return _extract_query(name, inp)


def _extract_query(name: str, inp: dict) -> str | None:
    """Extract the search query from a tool call input."""
    for key in ("query", "pattern", "question", "search_query"):
        val = inp.get(key)
        if val and isinstance(val, str):
            return val
    return None


def _is_error_result(result) -> bool:
    """Detect if a tool result indicates an error."""
    if not isinstance(result, dict):
        return False

    # Bash-style results: check stderr and exit code in stdout
    stderr = result.get("stderr", "")
    if stderr and len(stderr.strip()) > 5:
        # Filter benign stderr (warnings, info messages)
        if ERROR_PATTERNS.search(stderr[:500]):
            return True

    stdout = result.get("stdout", "")
    if isinstance(stdout, str) and "Exit code" in stdout[:200]:
        m = re.search(r"Exit code (\d+)", stdout[:200])
        if m and int(m.group(1)) != 0:
            return True

    # interrupted flag
    if result.get("interrupted") == "True" or result.get("interrupted") is True:
        return True

    # Agent results
    if result.get("status") == "error":
        return True

    # Content-based results (Read, Edit, etc.)
    content = result.get("content", "")
    if isinstance(content, str) and ERROR_PATTERNS.search(content[:500]):
        return True
    if isinstance(content, list):
        for block in content[:3]:
            if isinstance(block, dict):
                text = block.get("text", "")
                if ERROR_PATTERNS.search(text[:500]):
                    return True

    return False


def _parse_ts(ts_str: str) -> datetime | None:
    """Parse ISO8601 timestamp."""
    try:
        # Handle Z suffix
        ts_str = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def _count_reformulations(queries: list[str]) -> int:
    """Count query pairs that look like reformulations (similar but not identical)."""
    if len(queries) < 2:
        return 0

    count = 0
    normalized = [_normalize_query(q) for q in queries]

    for i in range(1, len(normalized)):
        for j in range(max(0, i - 5), i):  # look back up to 5 queries
            sim = _jaccard_similarity(normalized[j], normalized[i])
            if 0.3 < sim < 0.95:  # similar but not identical
                count += 1
                break  # count each query as reformulation at most once

    return count


def _normalize_query(query: str) -> set[str]:
    """Normalize a query to a set of lowercase tokens."""
    return set(re.findall(r"\w+", query.lower()))


def _jaccard_similarity(a: set, b: set) -> float:
    """Jaccard similarity between two sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------

def find_session(uuid_prefix: str) -> Path | None:
    """Find a session JSONL file by UUID prefix."""
    for proj_dir in sorted(PROJECTS_DIR.iterdir()):
        if not proj_dir.is_dir():
            continue
        for jsonl in proj_dir.glob(f"{uuid_prefix}*.jsonl"):
            return jsonl
    return None


def find_sessions_by_date(since: datetime, until: datetime | None = None) -> list[Path]:
    """Find session JSONL files modified within a date range."""
    sessions = []
    since_ts = since.timestamp()
    until_ts = until.timestamp() if until else datetime.now().timestamp() + 86400

    for proj_dir in sorted(PROJECTS_DIR.iterdir()):
        if not proj_dir.is_dir():
            continue
        for jsonl in proj_dir.glob("*.jsonl"):
            mtime = jsonl.stat().st_mtime
            if since_ts <= mtime <= until_ts:
                sessions.append(jsonl)

    return sorted(sessions, key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract epistemic features from Claude Code session transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  session-features.py --session abc123
  session-features.py --today
  session-features.py --days 7 --output artifacts/epistemic-metrics.jsonl
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", help="UUID or UUID prefix of a specific session")
    group.add_argument("--today", action="store_true", help="Process today's sessions")
    group.add_argument("--days", type=int, help="Process sessions from last N days")

    parser.add_argument("--output", "-o", help="Append JSONL output to this file")
    parser.add_argument("--project", "-p", help="Filter by project name")

    args = parser.parse_args()

    # Resolve sessions
    sessions: list[Path] = []

    if args.session:
        path = find_session(args.session)
        if not path:
            print(f"No session found matching '{args.session}'", file=sys.stderr)
            sys.exit(1)
        sessions = [path]

    elif args.today:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        sessions = find_sessions_by_date(today)

    elif args.days:
        since = datetime.now() - timedelta(days=args.days)
        sessions = find_sessions_by_date(since)

    # Filter by project
    if args.project:
        sessions = [
            s for s in sessions
            if extract_project_name(s.parent.name) == args.project
        ]

    if not sessions:
        print("No sessions found.", file=sys.stderr)
        sys.exit(0)

    # Process
    results = []
    for path in sessions:
        try:
            features = extract_features(path)
            results.append(features)
        except Exception as e:
            print(f"WARN: failed to process {path.name}: {e}", file=sys.stderr)

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "a") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        print(f"Appended {len(results)} session features to {output_path}", file=sys.stderr)
    else:
        if len(results) == 1:
            print(json.dumps(results[0], indent=2))
        else:
            for r in results:
                print(json.dumps(r))

    # Summary to stderr
    if len(results) > 1:
        avg_failure = sum(r["tool_failure_rate"] for r in results) / len(results)
        avg_tools = sum(r["tool_call_count"] for r in results) / len(results)
        print(
            f"\n{len(results)} sessions processed. "
            f"Avg tool calls: {avg_tools:.0f}, avg failure rate: {avg_failure:.1%}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
