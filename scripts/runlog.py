#!/usr/bin/env python3
"""Cross-vendor local run store for Claude, Codex, Kimi, and Gemini CLIs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from runlog_adapters import ADAPTERS
from runlog_adapters.common import DiscoveredSource, json_dumps

SCHEMA_VERSION = "v1"
DB_PATH = Path.home() / ".claude" / "runlogs.db"
SCHEMA_PATH = Path(__file__).with_name("runlog_schema.sql")
QUERY_DIR = Path(__file__).with_name("runlog_queries")
FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "runlogs"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def db_text(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value).encode("utf-8", "backslashreplace").decode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    db.executescript(SCHEMA_PATH.read_text())
    return db


def infer_source_kind(vendor: str, path: Path) -> str:
    name = path.name
    if vendor == "kimi":
        if name == "wire.jsonl":
            return "wire_jsonl"
        if name.startswith("context"):
            return "context_jsonl"
        return "transcript_jsonl"
    if vendor == "gemini":
        return "state_json" if name.endswith(".json") and "session-" in name else "log_json"
    return "transcript_jsonl"


def upsert_source(db: sqlite3.Connection, source: DiscoveredSource, sha256: str) -> int:
    stat = source.path.stat()
    db.execute(
        """
        INSERT INTO sources (vendor, source_kind, path, sha256, discovered_at, file_mtime, size_bytes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            vendor = excluded.vendor,
            source_kind = excluded.source_kind,
            sha256 = excluded.sha256,
            discovered_at = excluded.discovered_at,
            file_mtime = excluded.file_mtime,
            size_bytes = excluded.size_bytes
        """,
        (
            db_text(source.vendor),
            db_text(source.source_kind),
            db_text(str(source.path)),
            sha256,
            utc_now(),
            stat.st_mtime,
            stat.st_size,
        ),
    )
    row = db.execute("SELECT source_id FROM sources WHERE path = ?", (str(source.path),)).fetchone()
    return int(row["source_id"])


def successful_import_exists(
    db: sqlite3.Connection,
    *,
    source_id: int,
    source_sha256: str,
    parser_name: str,
    parser_version: str,
) -> bool:
    row = db.execute(
        """
        SELECT 1
        FROM imports
        WHERE source_id = ?
          AND source_sha256 = ?
          AND parser_name = ?
          AND parser_version = ?
          AND schema_version = ?
          AND success = 1
        """,
        (source_id, source_sha256, parser_name, parser_version, SCHEMA_VERSION),
    ).fetchone()
    return row is not None


def write_import_row(
    db: sqlite3.Connection,
    *,
    source_id: int,
    source_sha256: str,
    parser_name: str,
    parser_version: str,
    success: bool,
    error: dict | None,
) -> int:
    db.execute(
        """
        INSERT INTO imports (
            source_id, source_sha256, parser_name, parser_version, schema_version, imported_at, success, error_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id, source_sha256, parser_name, parser_version, schema_version) DO UPDATE SET
            imported_at = excluded.imported_at,
            success = excluded.success,
            error_json = excluded.error_json
        """,
        (
            source_id,
            source_sha256,
            parser_name,
            parser_version,
            SCHEMA_VERSION,
            utc_now(),
            1 if success else 0,
            json_dumps(error),
        ),
    )
    row = db.execute(
        """
        SELECT import_id
        FROM imports
        WHERE source_id = ?
          AND source_sha256 = ?
          AND parser_name = ?
          AND parser_version = ?
          AND schema_version = ?
        """,
        (source_id, source_sha256, parser_name, parser_version, SCHEMA_VERSION),
    ).fetchone()
    return int(row["import_id"])


def cleanup_source_data(db: sqlite3.Connection, source_id: int) -> None:
    ref_ids = [row["record_ref_id"] for row in db.execute("SELECT record_ref_id FROM record_refs WHERE source_id = ?", (source_id,))]
    if not ref_ids:
        return
    placeholders = ", ".join("?" for _ in ref_ids)
    db.execute(f"DELETE FROM file_touches WHERE record_ref_id IN ({placeholders})", ref_ids)
    db.execute(
        f"DELETE FROM tool_calls WHERE start_record_ref_id IN ({placeholders}) OR end_record_ref_id IN ({placeholders})",
        ref_ids * 2,
    )
    db.execute(f"DELETE FROM events WHERE record_ref_id IN ({placeholders})", ref_ids)
    db.execute("DELETE FROM record_refs WHERE source_id = ?", (source_id,))


def ensure_session_pk(db: sqlite3.Connection, session_row) -> int:
    if session_row.vendor_session_id:
        row = db.execute(
            """
            SELECT session_pk FROM sessions
            WHERE vendor = ? AND client = ? AND vendor_session_id = ?
            """,
            (session_row.vendor, session_row.client, session_row.vendor_session_id),
        ).fetchone()
        if row is not None:
            db.execute(
                """
                UPDATE sessions
                SET project_root = COALESCE(?, project_root),
                    project_slug = COALESCE(?, project_slug)
                WHERE session_pk = ?
                """,
                (session_row.project_root, session_row.project_slug, row["session_pk"]),
            )
            return int(row["session_pk"])
    if session_row.synthetic_session_key:
        row = db.execute(
            """
            SELECT session_pk FROM sessions
            WHERE vendor = ? AND client = ? AND synthetic_session_key = ?
            """,
            (session_row.vendor, session_row.client, session_row.synthetic_session_key),
        ).fetchone()
        if row is not None:
            return int(row["session_pk"])
    cursor = db.execute(
        """
        INSERT INTO sessions (vendor, client, vendor_session_id, synthetic_session_key, project_root, project_slug)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session_row.vendor,
            db_text(session_row.client),
            db_text(session_row.vendor_session_id),
            session_row.synthetic_session_key,
            db_text(session_row.project_root),
            db_text(session_row.project_slug),
        ),
    )
    return int(cursor.lastrowid)


def upsert_run(db: sqlite3.Connection, run_row, session_pk: int, source_id: int) -> None:
    db.execute(
        """
        INSERT INTO runs (
            run_id, session_pk, vendor, client, transport, protocol, provider_name, base_url, cwd,
            started_at, ended_at, status, model_requested, model_resolved, approval_mode, sandbox_mode,
            instruction_hash, config_hash, mcp_set_hash, git_head, primary_source_id, completeness, completeness_notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            session_pk = excluded.session_pk,
            transport = COALESCE(excluded.transport, runs.transport),
            protocol = COALESCE(excluded.protocol, runs.protocol),
            provider_name = COALESCE(excluded.provider_name, runs.provider_name),
            base_url = COALESCE(excluded.base_url, runs.base_url),
            cwd = COALESCE(excluded.cwd, runs.cwd),
            started_at = COALESCE(excluded.started_at, runs.started_at),
            ended_at = COALESCE(excluded.ended_at, runs.ended_at),
            status = COALESCE(excluded.status, runs.status),
            model_requested = COALESCE(excluded.model_requested, runs.model_requested),
            model_resolved = COALESCE(excluded.model_resolved, runs.model_resolved),
            approval_mode = COALESCE(excluded.approval_mode, runs.approval_mode),
            sandbox_mode = COALESCE(excluded.sandbox_mode, runs.sandbox_mode),
            instruction_hash = COALESCE(excluded.instruction_hash, runs.instruction_hash),
            config_hash = COALESCE(excluded.config_hash, runs.config_hash),
            mcp_set_hash = COALESCE(excluded.mcp_set_hash, runs.mcp_set_hash),
            git_head = COALESCE(excluded.git_head, runs.git_head),
            completeness = CASE
                WHEN runs.completeness = 'full' OR excluded.completeness = 'full' THEN 'full'
                ELSE COALESCE(excluded.completeness, runs.completeness)
            END,
            completeness_notes = CASE
                WHEN runs.completeness = 'full' OR excluded.completeness = 'full' THEN NULL
                ELSE COALESCE(excluded.completeness_notes, runs.completeness_notes)
            END,
            primary_source_id = COALESCE(runs.primary_source_id, excluded.primary_source_id)
        """,
        (
            run_row.run_id,
            session_pk,
            db_text(run_row.vendor),
            db_text(run_row.client),
            db_text(run_row.transport),
            db_text(run_row.protocol),
            db_text(run_row.provider_name),
            db_text(run_row.base_url),
            db_text(run_row.cwd),
            db_text(run_row.started_at),
            db_text(run_row.ended_at),
            db_text(run_row.status),
            db_text(run_row.model_requested),
            db_text(run_row.model_resolved),
            db_text(run_row.approval_mode),
            db_text(run_row.sandbox_mode),
            db_text(run_row.instruction_hash),
            db_text(run_row.config_hash),
            db_text(run_row.mcp_set_hash),
            db_text(run_row.git_head),
            source_id,
            db_text(run_row.completeness),
            db_text(run_row.completeness_notes),
        ),
    )


def upsert_run_config(db: sqlite3.Connection, row) -> None:
    db.execute(
        """
        INSERT INTO run_configs (run_id, instruction_ref, tools_json, mcp_servers_json, metadata_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            instruction_ref = COALESCE(excluded.instruction_ref, run_configs.instruction_ref),
            tools_json = COALESCE(excluded.tools_json, run_configs.tools_json),
            mcp_servers_json = COALESCE(excluded.mcp_servers_json, run_configs.mcp_servers_json),
            metadata_json = COALESCE(excluded.metadata_json, run_configs.metadata_json)
        """,
        (
            db_text(row.run_id),
            db_text(row.instruction_ref),
            db_text(json_dumps(row.tools)),
            db_text(json_dumps(row.mcp_servers)),
            db_text(json_dumps(row.metadata)),
        ),
    )


def upsert_event(db: sqlite3.Connection, row, record_ref_id: int | None) -> None:
    db.execute(
        """
        INSERT INTO events (
            event_id, run_id, seq, ts, kind, vendor_kind, vendor_event_id, role, text,
            payload_json, record_ref_id, parent_event_id, correlation_id, tool_call_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET
            seq = excluded.seq,
            ts = COALESCE(excluded.ts, events.ts),
            kind = excluded.kind,
            vendor_kind = COALESCE(excluded.vendor_kind, events.vendor_kind),
            vendor_event_id = COALESCE(excluded.vendor_event_id, events.vendor_event_id),
            role = COALESCE(excluded.role, events.role),
            text = COALESCE(excluded.text, events.text),
            payload_json = COALESCE(excluded.payload_json, events.payload_json),
            record_ref_id = COALESCE(excluded.record_ref_id, events.record_ref_id),
            parent_event_id = COALESCE(excluded.parent_event_id, events.parent_event_id),
            correlation_id = COALESCE(excluded.correlation_id, events.correlation_id),
            tool_call_id = COALESCE(excluded.tool_call_id, events.tool_call_id)
        """,
        (
            db_text(row.event_id),
            db_text(row.run_id),
            row.seq,
            db_text(row.ts),
            db_text(row.kind),
            db_text(row.vendor_kind),
            db_text(row.vendor_event_id),
            db_text(row.role),
            db_text(row.text),
            db_text(json_dumps(row.payload)),
            record_ref_id,
            db_text(row.parent_event_id),
            db_text(row.correlation_id),
            db_text(row.tool_call_id),
        ),
    )


def upsert_tool_call(db: sqlite3.Connection, row, start_ref_id: int | None, end_ref_id: int | None) -> None:
    db.execute(
        """
        INSERT INTO tool_calls (
            tool_call_id, run_id, tool_name, tool_source, mcp_server, ts_start, ts_end,
            args_json, result_json, status, exit_code, correlation_id, start_record_ref_id, end_record_ref_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tool_call_id) DO UPDATE SET
            run_id = excluded.run_id,
            tool_name = COALESCE(excluded.tool_name, tool_calls.tool_name),
            tool_source = COALESCE(excluded.tool_source, tool_calls.tool_source),
            mcp_server = COALESCE(excluded.mcp_server, tool_calls.mcp_server),
            ts_start = COALESCE(excluded.ts_start, tool_calls.ts_start),
            ts_end = COALESCE(excluded.ts_end, tool_calls.ts_end),
            args_json = COALESCE(excluded.args_json, tool_calls.args_json),
            result_json = COALESCE(excluded.result_json, tool_calls.result_json),
            status = COALESCE(excluded.status, tool_calls.status),
            exit_code = COALESCE(excluded.exit_code, tool_calls.exit_code),
            correlation_id = COALESCE(excluded.correlation_id, tool_calls.correlation_id),
            start_record_ref_id = COALESCE(excluded.start_record_ref_id, tool_calls.start_record_ref_id),
            end_record_ref_id = COALESCE(excluded.end_record_ref_id, tool_calls.end_record_ref_id)
        """,
        (
            db_text(row.tool_call_id),
            db_text(row.run_id),
            db_text(row.tool_name),
            db_text(row.tool_source),
            db_text(row.mcp_server),
            db_text(row.ts_start),
            db_text(row.ts_end),
            db_text(json_dumps(row.args)),
            db_text(json_dumps(row.result)),
            db_text(row.status),
            row.exit_code,
            db_text(row.correlation_id),
            start_ref_id,
            end_ref_id,
        ),
    )


def insert_file_touch(db: sqlite3.Connection, row, record_ref_id: int | None) -> None:
    db.execute(
        """
        INSERT OR IGNORE INTO file_touches (run_id, tool_call_id, path, op, record_ref_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (db_text(row.run_id), db_text(row.tool_call_id), db_text(row.path), db_text(row.op), record_ref_id),
    )


def upsert_run_edge(db: sqlite3.Connection, row) -> None:
    exists = db.execute("SELECT 1 FROM runs WHERE run_id = ?", (row.src_run_id,)).fetchone()
    exists2 = db.execute("SELECT 1 FROM runs WHERE run_id = ?", (row.dst_run_id,)).fetchone()
    if exists is None or exists2 is None:
        return
    db.execute(
        """
        INSERT INTO run_edges (src_run_id, dst_run_id, edge_type, inference_method, confidence)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(src_run_id, dst_run_id, edge_type) DO UPDATE SET
            inference_method = excluded.inference_method,
            confidence = excluded.confidence
        """,
        (
            db_text(row.src_run_id),
            db_text(row.dst_run_id),
            db_text(row.edge_type),
            db_text(row.inference_method),
            row.confidence,
        ),
    )


def command_init_db(args: argparse.Namespace) -> int:
    db = get_db(Path(args.db))
    db.close()
    print(Path(args.db))
    return 0


def command_import(args: argparse.Namespace) -> int:
    db = get_db(Path(args.db))
    vendors = args.vendor or list(ADAPTERS.keys())
    total_imported = 0
    total_skipped = 0
    total_failed = 0

    for vendor in vendors:
        adapter = ADAPTERS[vendor]
        parser_name, parser_version = adapter.parser_identity()
        if args.source:
            sources = [
                DiscoveredSource(vendor=vendor, source_kind=infer_source_kind(vendor, Path(path)), path=Path(path).expanduser())
                for path in args.source
            ]
        else:
            root = FIXTURE_ROOT / vendor if args.fixtures else None
            sources = adapter.discover_sources(root)
        if args.limit_sources:
            sources = sources[: args.limit_sources]

        for source in sources:
            if not source.path.exists():
                continue
            sha = sha256_file(source.path)
            source_id = upsert_source(db, source, sha)
            if not args.force and successful_import_exists(
                db,
                source_id=source_id,
                source_sha256=sha,
                parser_name=parser_name,
                parser_version=parser_version,
            ):
                total_skipped += 1
                continue

            try:
                parsed = adapter.parse_source(source)
            except Exception as exc:  # pragma: no cover - fail-open importer surface
                write_import_row(
                    db,
                    source_id=source_id,
                    source_sha256=sha,
                    parser_name=parser_name,
                    parser_version=parser_version,
                    success=False,
                    error={"error": type(exc).__name__, "message": str(exc), "path": str(source.path)},
                )
                db.commit()
                total_failed += 1
                continue

            try:
                db.execute("BEGIN")
                cleanup_source_data(db, source_id)
                import_id = write_import_row(
                    db,
                    source_id=source_id,
                    source_sha256=sha,
                    parser_name=parser_name,
                    parser_version=parser_version,
                    success=True,
                    error=None,
                )
                record_ref_ids: dict[str, int] = {}
                for record in parsed.records:
                    cursor = db.execute(
                        """
                        INSERT INTO record_refs (
                            source_id, import_id, raw_record_hash, raw_record_key, line_no, byte_start, byte_end, ts_raw
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_id,
                            import_id,
                            db_text(record.raw_record_hash),
                            db_text(record.raw_record_key),
                            record.line_no,
                            record.byte_start,
                            record.byte_end,
                            db_text(record.ts_raw),
                        ),
                    )
                    record_ref_ids[record.raw_record_key] = int(cursor.lastrowid)

                session_pks: dict[tuple[str, str, str], int] = {}
                for session in parsed.sessions:
                    session_pks[session.lookup_key] = ensure_session_pk(db, session)

                for run in parsed.runs:
                    session_pk = session_pks[run.session_lookup_key]
                    upsert_run(db, run, session_pk, source_id)

                for config in parsed.run_configs:
                    upsert_run_config(db, config)

                seq_offsets: dict[str, int] = {}
                for run in parsed.runs:
                    row = db.execute(
                        "SELECT COALESCE(MAX(seq), 0) AS max_seq FROM events WHERE run_id = ?",
                        (run.run_id,),
                    ).fetchone()
                    seq_offsets[run.run_id] = int(row["max_seq"])

                for event in parsed.events:
                    event.seq = seq_offsets.get(event.run_id, 0) + event.seq
                    upsert_event(db, event, record_ref_ids.get(event.record_key))

                for tool_call in parsed.tool_calls:
                    upsert_tool_call(
                        db,
                        tool_call,
                        record_ref_ids.get(tool_call.start_record_key),
                        record_ref_ids.get(tool_call.end_record_key),
                    )

                for touch in parsed.file_touches:
                    insert_file_touch(db, touch, record_ref_ids.get(touch.record_key))

                for edge in parsed.run_edges:
                    upsert_run_edge(db, edge)

                db.commit()
                total_imported += 1
            except Exception as exc:  # pragma: no cover - transaction failure path
                db.rollback()
                write_import_row(
                    db,
                    source_id=source_id,
                    source_sha256=sha,
                    parser_name=parser_name,
                    parser_version=parser_version,
                    success=False,
                    error={"error": type(exc).__name__, "message": str(exc), "path": str(source.path)},
                )
                db.commit()
                total_failed += 1

    print(json.dumps({"imported": total_imported, "skipped": total_skipped, "failed": total_failed}, sort_keys=True))
    return 0 if total_failed == 0 else 1


def command_stats(args: argparse.Namespace) -> int:
    db = get_db(Path(args.db))
    rows = db.execute(
        """
        SELECT vendor,
               COUNT(DISTINCT source_id) AS sources,
               COUNT(DISTINCT run_id) AS runs,
               COUNT(DISTINCT event_id) AS events,
               COUNT(DISTINCT tool_call_id) AS tool_calls,
               COUNT(DISTINCT touch_id) AS file_touches
        FROM (
            SELECT vendor, source_id, NULL AS run_id, NULL AS event_id, NULL AS tool_call_id, NULL AS touch_id FROM sources
            UNION ALL
            SELECT vendor, NULL, run_id, NULL, NULL, NULL FROM runs
            UNION ALL
            SELECT runs.vendor, NULL, NULL, event_id, NULL, NULL FROM events JOIN runs USING(run_id)
            UNION ALL
            SELECT runs.vendor, NULL, NULL, NULL, tool_call_id, NULL FROM tool_calls JOIN runs USING(run_id)
            UNION ALL
            SELECT runs.vendor, NULL, NULL, NULL, NULL, touch_id FROM file_touches JOIN runs USING(run_id)
        )
        GROUP BY vendor
        ORDER BY vendor
        """
    ).fetchall()
    _print_rows(rows)
    return 0


def command_query(args: argparse.Namespace) -> int:
    db = get_db(Path(args.db))

    # List available queries when no query specified
    if args.query is None:
        for sql_file in sorted(QUERY_DIR.glob("*.sql")):
            name = sql_file.stem
            # Extract params from SQL
            sql_text = sql_file.read_text()
            params = sorted(set(re.findall(r":([A-Za-z_][A-Za-z0-9_]*)", sql_text)))
            param_str = f"  params: {', '.join(params)}" if params else ""
            print(f"  {name}{param_str}")
        return 0

    sql = _load_query_sql(args.query)
    params = dict(_parse_param(item) for item in (args.param or []))
    params = _bind_missing_params(sql, params)
    rows = db.execute(sql, params).fetchall()
    if args.format == "json":
        print(json.dumps([dict(row) for row in rows], sort_keys=True, indent=2))
    else:
        _print_rows(rows)
    return 0


def command_recent(args: argparse.Namespace) -> int:
    """Show recent runs with key metadata."""
    db = get_db(Path(args.db))
    hours = args.hours or 24
    rows = db.execute(
        """
        SELECT r.run_id, r.vendor, r.model_resolved,
               SUBSTR(r.started_at, 1, 16) AS started,
               SUBSTR(r.ended_at, 1, 16) AS ended,
               r.status, r.cwd,
               COUNT(DISTINCT tc.tool_call_id) AS tools,
               COUNT(DISTINCT e.event_id) AS events
        FROM runs r
        LEFT JOIN tool_calls tc ON tc.run_id = r.run_id
        LEFT JOIN events e ON e.run_id = r.run_id
        WHERE r.started_at >= datetime('now', :offset)
          AND (:vendor IS NULL OR r.vendor = :vendor)
        GROUP BY r.run_id
        ORDER BY r.started_at DESC
        LIMIT :limit
        """,
        {
            "offset": f"-{hours} hours",
            "vendor": args.vendor,
            "limit": args.limit or 20,
        },
    ).fetchall()
    if args.format == "json":
        print(json.dumps([dict(row) for row in rows], sort_keys=True, indent=2))
    else:
        _print_rows(rows)
    return 0


def _load_query_sql(name_or_path: str) -> str:
    direct = Path(name_or_path)
    if direct.exists():
        return direct.read_text()
    query_path = QUERY_DIR / (name_or_path if name_or_path.endswith(".sql") else f"{name_or_path}.sql")
    if not query_path.exists():
        raise FileNotFoundError(f"query not found: {name_or_path}")
    return query_path.read_text()


def _parse_param(item: str) -> tuple[str, object]:
    key, raw_value = item.split("=", 1)
    value: object
    lower = raw_value.lower()
    if lower == "null":
        value = None
    elif lower in {"true", "false"}:
        value = lower == "true"
    else:
        try:
            value = int(raw_value)
        except ValueError:
            try:
                value = float(raw_value)
            except ValueError:
                value = raw_value
    return key, value


def _bind_missing_params(sql: str, params: dict[str, object]) -> dict[str, object]:
    bound = dict(params)
    for name in re.findall(r":([A-Za-z_][A-Za-z0-9_]*)", sql):
        bound.setdefault(name, None)
    return bound


def _print_rows(rows) -> None:
    if not rows:
        print("(no rows)")
        return
    columns = rows[0].keys()
    widths = {column: len(column) for column in columns}
    rendered = []
    for row in rows:
        rendered_row = {column: "" if row[column] is None else str(row[column]) for column in columns}
        rendered.append(rendered_row)
        for column, value in rendered_row.items():
            widths[column] = max(widths[column], len(value))
    header = "  ".join(column.ljust(widths[column]) for column in columns)
    print(header)
    print("  ".join("-" * widths[column] for column in columns))
    for row in rendered:
        print("  ".join(row[column].ljust(widths[column]) for column in columns))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Initialize the runlog database").set_defaults(func=command_init_db)

    p_import = sub.add_parser("import", help="Import run sources")
    p_import.add_argument("--vendor", action="append", choices=sorted(ADAPTERS.keys()), help="Vendor to import")
    p_import.add_argument("--fixtures", action="store_true", help="Import the scrubbed fixture corpus")
    p_import.add_argument("--source", action="append", help="Explicit source path(s) to import")
    p_import.add_argument("--force", action="store_true", help="Re-import even when source hash is unchanged")
    p_import.add_argument("--limit-sources", type=int, help="Limit number of discovered sources")
    p_import.set_defaults(func=command_import)

    sub.add_parser("stats", help="Show vendor-level runlog counts").set_defaults(func=command_stats)

    p_query = sub.add_parser("query", help="Run a named SQL query or SQL file")
    p_query.add_argument("query", nargs="?", default=None, help="Named query stem or .sql path (omit to list available)")
    p_query.add_argument("--param", action="append", help="Bind parameter in key=value form")
    p_query.add_argument("--format", choices=("table", "json"), default="table")
    p_query.set_defaults(func=command_query)

    p_recent = sub.add_parser("recent", help="Show recent runs (most common forensic query)")
    p_recent.add_argument("--hours", type=int, default=24, help="Lookback window (default: 24)")
    p_recent.add_argument("--vendor", help="Filter by vendor")
    p_recent.add_argument("--limit", type=int, default=20, help="Max rows (default: 20)")
    p_recent.add_argument("--format", choices=("table", "json"), default="table")
    p_recent.set_defaults(func=command_recent)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
