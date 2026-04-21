"""Dispatch a session through an LLM for analysis via llmx."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from .show import render_text


# FTS anti-pattern queries run before dispatch; hits prepended to the prompt so
# diagnostic signal survives transcript compression (see sessions.py lineage).
_ANTI_PATTERN_QUERIES: list[tuple[str, str]] = [
    ("repeated-read",         '"Read" AND "Read" AND "Read"'),
    ("search-flood",          '"WebSearch" AND "WebSearch"'),
    ("sycophancy",            '"great idea" OR "excellent point" OR "absolutely"'),
    ("capability-abandon",    '"training cutoff" OR "cannot verify"'),
    ("build-then-undo",       '"revert" OR "undo" OR "rollback"'),
]


def scan_anti_patterns(db, session_pk: int) -> str:
    """FTS5 pre-scan for anti-pattern signatures. Returns markdown hit summary."""
    hits: list[str] = []
    for label, query in _ANTI_PATTERN_QUERIES:
        try:
            row = db.execute(
                """
                SELECT COUNT(*) AS n,
                       snippet(events_fts, -1, '>>>', '<<<', '…', 16) AS snip
                FROM events_fts
                JOIN events e ON e.rowid = events_fts.rowid
                JOIN runs  r  ON r.run_id = e.run_id
                WHERE r.session_pk = ? AND events_fts MATCH ?
                """,
                (session_pk, query),
            ).fetchone()
            if row and row["n"]:
                hits.append(f"- **{label}** ({row['n']}×): {row['snip']}")
        except Exception:
            continue
    if not hits:
        return ""
    return "## FTS5 anti-pattern pre-scan\n" + "\n".join(hits)


def dispatch_session(
    db,
    session_pk: int,
    *,
    prompt: str,
    model: str = "gemini-3.1-pro-preview",
    timeout_s: int = 300,
) -> int:
    """Render session, prepend anti-pattern scan + prompt, pipe to llmx.

    Returns the subprocess exit code.
    """
    transcript = render_text(db, session_pk)
    scan_md = scan_anti_patterns(db, session_pk)
    body = f"{prompt}\n\n{scan_md}\n\n{transcript}" if scan_md else f"{prompt}\n\n{transcript}"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(body)
        tmp_path = Path(tmp.name)

    try:
        # llmx's positional prompt is last; use -f for the large context.
        cmd = ["llmx", "chat", "-m", model, "-f", str(tmp_path), prompt]
        print(
            f"Dispatching session {session_pk} to {model} "
            f"({len(body):,} chars)",
            file=sys.stderr,
        )
        proc = subprocess.run(cmd, timeout=timeout_s)
        return proc.returncode
    finally:
        tmp_path.unlink(missing_ok=True)
