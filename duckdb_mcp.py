"""DuckDB MCP — read-only SQL queries against .duckdb files.

Replaces the ad-hoc `uv run python3 -c "import duckdb..."` pattern that accumulates
escaping bugs and boilerplate across phenome/genomics sessions.

Tools:
- tables(db_path): list tables + views with row counts
- describe(db_path, table): column names and types
- query(db_path, sql, format, limit): run read-only SQL, return markdown or JSON

Read-only enforcement: SQL must start with SELECT, WITH, DESCRIBE, SHOW, PRAGMA,
or EXPLAIN. ATTACH, CREATE, INSERT, UPDATE, DELETE, DROP, COPY are rejected.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
from fastmcp import FastMCP

INSTRUCTIONS = """\
Read-only SQL access to DuckDB files. Use when inspecting data state, verifying
row counts, checking schemas, or exploring pipeline outputs stored in .duckdb files.

Tools:
- tables(db_path) — list tables and views with row counts
- describe(db_path, table) — column types for one table
- query(db_path, sql, format='markdown', limit=100) — run SELECT/WITH/DESCRIBE/SHOW/PRAGMA/EXPLAIN

Absolute paths required. Read-only enforced at SQL level.
"""

mcp = FastMCP("duckdb", instructions=INSTRUCTIONS)

_READONLY_PREFIX = re.compile(
    r"^\s*(SELECT|WITH|DESCRIBE|DESC|SHOW|PRAGMA|EXPLAIN|SUMMARIZE)\b",
    re.IGNORECASE,
)


def _resolve(db_path: str) -> Path:
    p = Path(db_path).expanduser()
    if not p.is_absolute():
        raise ValueError(f"db_path must be absolute, got {db_path!r}")
    if not p.exists():
        raise FileNotFoundError(f"DuckDB file not found: {p}")
    return p


def _connect(db_path: str) -> duckdb.DuckDBPyConnection:
    p = _resolve(db_path)
    return duckdb.connect(str(p), read_only=True)


def _rows_to_markdown(columns: list[str], rows: list[tuple]) -> str:
    if not rows:
        return f"_(0 rows)_\n\ncolumns: {', '.join(columns)}"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body_lines = []
    for row in rows:
        cells = []
        for v in row:
            if v is None:
                cells.append("")
            else:
                s = str(v).replace("\n", " ").replace("|", "\\|")
                if len(s) > 200:
                    s = s[:197] + "..."
                cells.append(s)
        body_lines.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *body_lines])


@mcp.tool
def tables(db_path: str) -> str:
    """List tables and views in a DuckDB file, with estimated row counts.

    Args:
        db_path: Absolute path to .duckdb file.
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT table_schema, table_name, table_type "
            "FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') "
            "ORDER BY table_schema, table_name"
        ).fetchall()
        out = []
        for schema, name, ttype in rows:
            qualified = f'"{schema}"."{name}"' if schema != "main" else f'"{name}"'
            try:
                (count,) = conn.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()
                out.append((schema, name, ttype, count))
            except Exception as exc:
                out.append((schema, name, ttype, f"err: {exc}"))
    return _rows_to_markdown(["schema", "name", "type", "rows"], out)


@mcp.tool
def describe(db_path: str, table: str) -> str:
    """Show column names and types for a table.

    Args:
        db_path: Absolute path to .duckdb file.
        table: Table name. Use 'schema.name' if not in default schema.
    """
    if not re.match(r"^[\w.\"]+$", table):
        raise ValueError(f"table name looks suspicious: {table!r}")
    with _connect(db_path) as conn:
        rows = conn.execute(f"DESCRIBE {table}").fetchall()
        cols = [d[0] for d in conn.description]
    return _rows_to_markdown(cols, rows)


@mcp.tool
def query(
    db_path: str,
    sql: str,
    format: str = "markdown",
    limit: int = 100,
) -> str:
    """Run a read-only SQL query.

    Args:
        db_path: Absolute path to .duckdb file.
        sql: SELECT/WITH/DESCRIBE/SHOW/PRAGMA/EXPLAIN/SUMMARIZE only.
        format: 'markdown' (default) or 'json'.
        limit: Max rows returned (default 100, cap 10000).
    """
    if not _READONLY_PREFIX.match(sql):
        raise ValueError(
            "SQL must start with SELECT, WITH, DESCRIBE, SHOW, PRAGMA, EXPLAIN, "
            "or SUMMARIZE. Mutations not allowed."
        )
    limit = max(1, min(int(limit), 10000))
    with _connect(db_path) as conn:
        rows = conn.execute(sql).fetchmany(limit + 1)
        columns = [d[0] for d in conn.description] if conn.description else []

    truncated = len(rows) > limit
    rows = rows[:limit]

    if format == "json":
        payload = {
            "columns": columns,
            "rows": [list(r) for r in rows],
            "row_count": len(rows),
            "truncated": truncated,
        }
        return json.dumps(payload, default=str, indent=2)

    md = _rows_to_markdown(columns, rows)
    footer = f"\n\n_{len(rows)} row(s)"
    if truncated:
        footer += f" (truncated at limit={limit})"
    footer += "_"
    return md + footer


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
