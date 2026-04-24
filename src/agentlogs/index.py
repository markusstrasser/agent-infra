"""Ingest session transcripts into agentlogs.db.

Replaces scripts/runlog.py command_import. Adapter contract unchanged; the
writer is rebuilt against the agentlogs schema:

  - No tool_calls.result_json write (column dropped — see Phase 0 findings)
  - Token counts (input/cached/output/reasoning/total) promoted from
    events.payload_json JSON into structured runs columns at ingest
  - events.payload_json trimmed: text/kind/role/tool_call_id already live in
    dedicated columns; payload carries only vendor-specific metadata that
    doesn't have a column home
  - events/tool_calls/file_touches tagged with import_id FK so re-imports under
    a new parser version can DELETE WHERE import_id IN (…)
  - session_uuid populated (canonical cross-vendor key)
  - indexer_runs row written per index invocation
"""

from __future__ import annotations

import hashlib
import sqlite3
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .adapters import ADAPTERS
from .adapters.common import DiscoveredSource, json_dumps

SCHEMA_VERSION = "agentlogs.v1"

# Keys from events.payload that carry token-usage metrics. Different vendors
# nest these differently; each adapter module is responsible for producing a
# payload dict that includes one of these keys when applicable.
_TOKEN_KEY_CANDIDATES = (
    "total_token_usage",    # Gemini
    "token_usage",          # Codex
    "usage",                # Claude
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _db_text(value: Any | None) -> str | None:
    if value is None:
        return None
    return str(value).encode("utf-8", "backslashreplace").decode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Token-count extraction from event payloads
# ---------------------------------------------------------------------------

_TOKEN_ATOM_KEYS = frozenset(
    k
    for aliases in (
        ("input", "input_tokens", "prompt_tokens"),
        ("cached", "cached_input_tokens", "cached_tokens"),
        ("output", "output_tokens", "completion_tokens"),
        ("thoughts", "reasoning_output_tokens", "reasoning_tokens"),
        ("total", "total_tokens"),
    )
    for k in aliases
)


def _is_token_dict(d: dict) -> bool:
    """A dict is a token dict if at least 2 of its keys are token atoms AND
    at least half of its values are numeric."""
    matching_keys = [k for k in d.keys() if k in _TOKEN_ATOM_KEYS]
    if len(matching_keys) < 2:
        return False
    numeric_matches = sum(
        1 for k in matching_keys if isinstance(d.get(k), (int, float))
    )
    return numeric_matches >= 2


def _find_token_dict(payload: Any) -> dict[str, Any] | None:
    """Recursively find a token-usage dict.

    Matches (a) nested under any _TOKEN_KEY_CANDIDATES, or
    (b) a dict where ≥2 keys are token atoms with numeric values (covers
    Gemini's token_usage payload which sits at top level without wrapper).
    """
    if isinstance(payload, dict):
        for key in _TOKEN_KEY_CANDIDATES:
            if key in payload and isinstance(payload[key], dict):
                return payload[key]
        if _is_token_dict(payload):
            return payload
        for value in payload.values():
            found = _find_token_dict(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_token_dict(item)
            if found:
                return found
    return None


_TOKEN_FIELD_MAP = {
    "input_tokens":     ("input", "input_tokens", "prompt_tokens"),
    "cached_tokens":    ("cached", "cached_input_tokens", "cached_tokens"),
    "output_tokens":    ("output", "output_tokens", "completion_tokens"),
    "reasoning_tokens": ("thoughts", "reasoning_output_tokens", "reasoning_tokens"),
    "total_tokens":     ("total", "total_tokens"),
}


def aggregate_tokens(events: Iterable) -> dict[str, int]:
    """Sum token counts across a run's events. Returns dict of column→total."""
    totals = {key: 0 for key in _TOKEN_FIELD_MAP}
    seen_any = False
    for event in events:
        token_dict = _find_token_dict(event.payload) if event.payload else None
        if not token_dict:
            continue
        for column, candidate_keys in _TOKEN_FIELD_MAP.items():
            for key in candidate_keys:
                if key in token_dict and isinstance(token_dict[key], (int, float)):
                    totals[column] += int(token_dict[key])
                    seen_any = True
                    break
    return totals if seen_any else {}


# ---------------------------------------------------------------------------
# Payload trimming
# ---------------------------------------------------------------------------

_REDUNDANT_PAYLOAD_KEYS = frozenset({
    "text", "content",        # already in events.text
    "role",                   # already in events.role
    "tool_call_id",           # already in events.tool_call_id
    "seq",                    # already in events.seq
    "ts", "timestamp",        # already in events.ts
})


def trim_payload(payload: Any) -> Any | None:
    """Drop keys from the top-level payload dict that are redundant with
    dedicated event columns. Return None if nothing structural remains.
    """
    if not isinstance(payload, dict):
        return payload
    kept = {k: v for k, v in payload.items() if k not in _REDUNDANT_PAYLOAD_KEYS}
    return kept if kept else None


# ---------------------------------------------------------------------------
# Upserts (writer functions — aligned with agentlogs schema)
# ---------------------------------------------------------------------------

def _upsert_source(db: sqlite3.Connection, source: DiscoveredSource, sha: str) -> int:
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
            _db_text(source.vendor),
            _db_text(source.source_kind),
            _db_text(str(source.path)),
            sha,
            _utc_now(),
            stat.st_mtime,
            stat.st_size,
        ),
    )
    row = db.execute("SELECT source_id FROM sources WHERE path = ?", (str(source.path),)).fetchone()
    return int(row[0])


def _successful_import_exists(db, *, source_id, sha, parser_name, parser_version):
    row = db.execute(
        """
        SELECT 1 FROM imports
        WHERE source_id = ? AND source_sha256 = ?
          AND parser_name = ? AND parser_version = ?
          AND schema_version = ? AND success = 1
        """,
        (source_id, sha, parser_name, parser_version, SCHEMA_VERSION),
    ).fetchone()
    return row is not None


def _write_import(db, *, source_id, sha, parser_name, parser_version, success, error) -> int:
    """Record an import attempt. UPSERT on the UNIQUE 5-tuple — re-imports
    (force=True or repeat-failure) overwrite the prior row.

    Without UPSERT, --force re-import or repeat parse-failure trips the
    UNIQUE(source_id, source_sha256, parser_name, parser_version,
    schema_version) constraint defined in 001_initial.sql.
    """
    db.execute(
        """
        INSERT INTO imports (source_id, source_sha256, parser_name, parser_version,
                             schema_version, imported_at, success, error_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id, source_sha256, parser_name, parser_version, schema_version)
        DO UPDATE SET
            imported_at = excluded.imported_at,
            success = excluded.success,
            error_json = excluded.error_json
        """,
        (source_id, sha, parser_name, parser_version, SCHEMA_VERSION,
         _utc_now(), 1 if success else 0, json_dumps(error) if error else None),
    )
    row = db.execute(
        """
        SELECT import_id FROM imports
        WHERE source_id = ? AND source_sha256 = ?
          AND parser_name = ? AND parser_version = ? AND schema_version = ?
        """,
        (source_id, sha, parser_name, parser_version, SCHEMA_VERSION),
    ).fetchone()
    return int(row[0])


def _cleanup_source_data(
    db: sqlite3.Connection,
    source_id: int,
    *,
    parser_name: str,
    parser_version: str,
    force: bool,
) -> None:
    """Delete prior-import rows that should be replaced.

    Three cases:
      - Parser version differs from prior import → wipe prior version's rows
        (schema may have changed; old rows are stale).
      - force=True → wipe ALL prior rows for this source (user-requested clean
        re-import).
      - Same parser version, no force (the WatchPaths case: source SHA changed
        because the JSONL got appended-to) → DO NOT wipe. UPSERT on
        events.event_id / tool_calls.tool_call_id / file_touches unique-index
        handles append cleanly without O(N) churn per fire.
    """
    if force:
        import_ids = [row[0] for row in db.execute(
            "SELECT import_id FROM imports WHERE source_id = ?", (source_id,)
        )]
    else:
        import_ids = [row[0] for row in db.execute(
            """
            SELECT import_id FROM imports
            WHERE source_id = ?
              AND NOT (parser_name = ? AND parser_version = ? AND schema_version = ?)
            """,
            (source_id, parser_name, parser_version, SCHEMA_VERSION),
        )]
    if not import_ids:
        return
    placeholders = ", ".join("?" for _ in import_ids)
    db.execute(f"DELETE FROM file_touches WHERE import_id IN ({placeholders})", import_ids)
    db.execute(f"DELETE FROM tool_calls WHERE import_id IN ({placeholders})", import_ids)
    db.execute(f"DELETE FROM events WHERE import_id IN ({placeholders})", import_ids)
    db.execute(
        f"DELETE FROM record_refs WHERE import_id IN ({placeholders})", import_ids,
    )


def _ensure_session_pk(db: sqlite3.Connection, sr) -> int:
    if sr.vendor_session_id:
        row = db.execute(
            "SELECT session_pk FROM sessions WHERE vendor=? AND client=? AND vendor_session_id=?",
            (sr.vendor, sr.client, sr.vendor_session_id),
        ).fetchone()
        if row:
            db.execute(
                "UPDATE sessions SET project_root=COALESCE(?, project_root), "
                "project_slug=COALESCE(?, project_slug), session_uuid=COALESCE(session_uuid, ?) "
                "WHERE session_pk=?",
                (sr.project_root, sr.project_slug, sr.vendor_session_id, row[0]),
            )
            return int(row[0])
    if sr.synthetic_session_key:
        row = db.execute(
            "SELECT session_pk FROM sessions WHERE vendor=? AND client=? AND synthetic_session_key=?",
            (sr.vendor, sr.client, sr.synthetic_session_key),
        ).fetchone()
        if row:
            return int(row[0])

    # Namespace by vendor so cross-vendor ID collisions can't trip the
    # UNIQUE(session_uuid) constraint. UUID-shaped IDs are 128-bit and
    # collisions are astronomical, but Gemini's path-derived synthetic keys
    # could theoretically collide with another vendor's vendor_session_id.
    raw_id = sr.vendor_session_id or sr.synthetic_session_key
    session_uuid = f"{sr.vendor}:{raw_id}" if raw_id else None
    cursor = db.execute(
        """
        INSERT INTO sessions (vendor, client, vendor_session_id, synthetic_session_key,
                              session_uuid, project_root, project_slug)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (sr.vendor, _db_text(sr.client), _db_text(sr.vendor_session_id),
         sr.synthetic_session_key, _db_text(session_uuid),
         _db_text(sr.project_root), _db_text(sr.project_slug)),
    )
    return int(cursor.lastrowid)  # type: ignore[arg-type]


def _upsert_run(db, run_row, session_pk: int, source_id: int, token_totals: dict) -> None:
    db.execute(
        """
        INSERT INTO runs (
            run_id, session_pk, vendor, client, transport, protocol, provider_name, base_url, cwd,
            started_at, ended_at, status, model_requested, model_resolved, approval_mode, sandbox_mode,
            instruction_hash, config_hash, mcp_set_hash, git_head, primary_source_id,
            completeness, completeness_notes,
            input_tokens, cached_tokens, output_tokens, reasoning_tokens, total_tokens
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            primary_source_id = COALESCE(runs.primary_source_id, excluded.primary_source_id),
            input_tokens     = COALESCE(excluded.input_tokens,     runs.input_tokens),
            cached_tokens    = COALESCE(excluded.cached_tokens,    runs.cached_tokens),
            output_tokens    = COALESCE(excluded.output_tokens,    runs.output_tokens),
            reasoning_tokens = COALESCE(excluded.reasoning_tokens, runs.reasoning_tokens),
            total_tokens     = COALESCE(excluded.total_tokens,     runs.total_tokens)
        """,
        (
            run_row.run_id, session_pk, _db_text(run_row.vendor), _db_text(run_row.client),
            _db_text(run_row.transport), _db_text(run_row.protocol), _db_text(run_row.provider_name),
            _db_text(run_row.base_url), _db_text(run_row.cwd),
            _db_text(run_row.started_at), _db_text(run_row.ended_at), _db_text(run_row.status),
            _db_text(run_row.model_requested), _db_text(run_row.model_resolved),
            _db_text(run_row.approval_mode), _db_text(run_row.sandbox_mode),
            _db_text(run_row.instruction_hash), _db_text(run_row.config_hash),
            _db_text(run_row.mcp_set_hash), _db_text(run_row.git_head),
            source_id, _db_text(run_row.completeness), _db_text(run_row.completeness_notes),
            token_totals.get("input_tokens"), token_totals.get("cached_tokens"),
            token_totals.get("output_tokens"), token_totals.get("reasoning_tokens"),
            token_totals.get("total_tokens"),
        ),
    )


def _upsert_event(db, row, record_ref_id, import_id):
    # (run_id, seq) is the stable identity within a run — event_id is derived
    # from stable_id(raw_key, ...) which can shift between re-parses (e.g., if a
    # line_no-based raw_key changes). Conflict target is the composite index, not
    # the PK, so re-indexing updates the event_id in place instead of failing the
    # whole vendor's transaction.
    trimmed = trim_payload(row.payload)
    db.execute(
        """
        INSERT INTO events (
            event_id, run_id, import_id, seq, ts, kind, vendor_kind, vendor_event_id,
            role, text, payload_json, record_ref_id, parent_event_id, correlation_id, tool_call_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id, seq) DO UPDATE SET
            event_id = excluded.event_id,
            import_id = excluded.import_id,
            ts = COALESCE(excluded.ts, events.ts),
            kind = excluded.kind,
            vendor_kind = COALESCE(excluded.vendor_kind, events.vendor_kind),
            vendor_event_id = COALESCE(excluded.vendor_event_id, events.vendor_event_id),
            role = COALESCE(excluded.role, events.role),
            text = COALESCE(excluded.text, events.text),
            payload_json = excluded.payload_json,
            record_ref_id = COALESCE(excluded.record_ref_id, events.record_ref_id),
            parent_event_id = COALESCE(excluded.parent_event_id, events.parent_event_id),
            correlation_id = COALESCE(excluded.correlation_id, events.correlation_id),
            tool_call_id = COALESCE(excluded.tool_call_id, events.tool_call_id)
        """,
        (
            _db_text(row.event_id), _db_text(row.run_id), import_id, row.seq,
            _db_text(row.ts), _db_text(row.kind),
            _db_text(row.vendor_kind), _db_text(row.vendor_event_id),
            _db_text(row.role), _db_text(row.text),
            _db_text(json_dumps(trimmed)) if trimmed is not None else None,
            record_ref_id,
            _db_text(row.parent_event_id), _db_text(row.correlation_id),
            _db_text(row.tool_call_id),
        ),
    )


def _upsert_tool_call(db, row, start_ref_id, end_ref_id, import_id):
    # Note: result_json intentionally not stored (column dropped — duplicated by tool_result event)
    db.execute(
        """
        INSERT INTO tool_calls (
            tool_call_id, run_id, import_id, tool_name, tool_source, mcp_server,
            ts_start, ts_end, args_json, status, exit_code, correlation_id,
            start_record_ref_id, end_record_ref_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tool_call_id) DO UPDATE SET
            run_id = excluded.run_id,
            import_id = excluded.import_id,
            tool_name = COALESCE(excluded.tool_name, tool_calls.tool_name),
            tool_source = COALESCE(excluded.tool_source, tool_calls.tool_source),
            mcp_server = COALESCE(excluded.mcp_server, tool_calls.mcp_server),
            ts_start = COALESCE(excluded.ts_start, tool_calls.ts_start),
            ts_end = COALESCE(excluded.ts_end, tool_calls.ts_end),
            args_json = COALESCE(excluded.args_json, tool_calls.args_json),
            status = COALESCE(excluded.status, tool_calls.status),
            exit_code = COALESCE(excluded.exit_code, tool_calls.exit_code),
            correlation_id = COALESCE(excluded.correlation_id, tool_calls.correlation_id),
            start_record_ref_id = COALESCE(excluded.start_record_ref_id, tool_calls.start_record_ref_id),
            end_record_ref_id = COALESCE(excluded.end_record_ref_id, tool_calls.end_record_ref_id)
        """,
        (
            _db_text(row.tool_call_id), _db_text(row.run_id), import_id,
            _db_text(row.tool_name), _db_text(row.tool_source), _db_text(row.mcp_server),
            _db_text(row.ts_start), _db_text(row.ts_end),
            _db_text(json_dumps(row.args)),
            _db_text(row.status), row.exit_code, _db_text(row.correlation_id),
            start_ref_id, end_ref_id,
        ),
    )


def _insert_file_touch(db, row, record_ref_id, import_id):
    db.execute(
        """
        INSERT OR IGNORE INTO file_touches (run_id, tool_call_id, import_id, path, op, record_ref_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (_db_text(row.run_id), _db_text(row.tool_call_id), import_id,
         _db_text(row.path), _db_text(row.op), record_ref_id),
    )


def _upsert_run_config(db, row):
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
        (_db_text(row.run_id), _db_text(row.instruction_ref),
         _db_text(json_dumps(row.tools)), _db_text(json_dumps(row.mcp_servers)),
         _db_text(json_dumps(row.metadata))),
    )


def _upsert_run_edge(db, row):
    a = db.execute("SELECT 1 FROM runs WHERE run_id=?", (row.src_run_id,)).fetchone()
    b = db.execute("SELECT 1 FROM runs WHERE run_id=?", (row.dst_run_id,)).fetchone()
    if a is None or b is None:
        return
    db.execute(
        """
        INSERT INTO run_edges (src_run_id, dst_run_id, edge_type, inference_method, confidence)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(src_run_id, dst_run_id, edge_type) DO UPDATE SET
            inference_method = excluded.inference_method,
            confidence = excluded.confidence
        """,
        (_db_text(row.src_run_id), _db_text(row.dst_run_id), _db_text(row.edge_type),
         _db_text(row.inference_method), row.confidence),
    )


# ---------------------------------------------------------------------------
# indexer_runs lifecycle
# ---------------------------------------------------------------------------

@dataclass
class IndexerStats:
    sources_discovered: int = 0
    sources_imported: int = 0
    sources_skipped: int = 0
    sources_failed: int = 0
    events_written: int = 0


def _start_indexer_run(db: sqlite3.Connection, vendor: str) -> int:
    cursor = db.execute(
        "INSERT INTO indexer_runs (started_at, vendor, status) VALUES (?, ?, 'running')",
        (_utc_now(), vendor),
    )
    return int(cursor.lastrowid)  # type: ignore[arg-type]


def _finish_indexer_run(db, run_id: int, stats: IndexerStats, error: Exception | None) -> None:
    db.execute(
        """
        UPDATE indexer_runs SET
            ended_at = ?,
            sources_discovered = ?,
            sources_imported = ?,
            sources_skipped = ?,
            sources_failed = ?,
            events_written = ?,
            status = ?,
            error_class = ?,
            error_message = ?
        WHERE run_id = ?
        """,
        (_utc_now(), stats.sources_discovered, stats.sources_imported,
         stats.sources_skipped, stats.sources_failed, stats.events_written,
         "error" if error else "success",
         type(error).__name__ if error else None,
         str(error)[:2000] if error else None,
         run_id),
    )


# ---------------------------------------------------------------------------
# Top-level ingest
# ---------------------------------------------------------------------------

def index_vendor(
    db: sqlite3.Connection,
    vendor: str,
    *,
    limit_sources: int | None = None,
    source_paths: list[Path] | None = None,
    force: bool = False,
) -> IndexerStats:
    """Ingest one vendor's sources into the given DB connection.

    Returns stats including sources_imported / sources_skipped / events_written.
    Writes an indexer_runs row (success or error).
    """
    adapter = ADAPTERS[vendor]
    parser_name, parser_version = adapter.parser_identity()
    stats = IndexerStats()
    run_row_id = _start_indexer_run(db, vendor)
    error: Exception | None = None
    try:
        if source_paths is not None:
            sources = [
                DiscoveredSource(
                    vendor=vendor,
                    source_kind="transcript_jsonl",
                    path=Path(p).expanduser(),
                )
                for p in source_paths
            ]
        else:
            sources = adapter.discover_sources()
        if limit_sources:
            sources = sources[:limit_sources]
        stats.sources_discovered = len(sources)

        for source in sources:
            if not source.path.exists():
                continue
            sha = _sha256_file(source.path)
            source_id = _upsert_source(db, source, sha)

            if not force and _successful_import_exists(
                db, source_id=source_id, sha=sha,
                parser_name=parser_name, parser_version=parser_version,
            ):
                stats.sources_skipped += 1
                continue

            try:
                parsed = adapter.parse_source(source)
            except Exception as exc:
                _write_import(
                    db, source_id=source_id, sha=sha,
                    parser_name=parser_name, parser_version=parser_version,
                    success=False,
                    error={"error": type(exc).__name__, "message": str(exc), "path": str(source.path)},
                )
                stats.sources_failed += 1
                continue

            db.execute("BEGIN IMMEDIATE")
            try:
                _cleanup_source_data(
                    db, source_id,
                    parser_name=parser_name, parser_version=parser_version,
                    force=force,
                )
                import_id = _write_import(
                    db, source_id=source_id, sha=sha,
                    parser_name=parser_name, parser_version=parser_version,
                    success=True, error=None,
                )
                _write_parsed(db, parsed, source_id, import_id, stats)
                db.execute("COMMIT")
                stats.sources_imported += 1
            except Exception:
                db.execute("ROLLBACK")
                raise
    except Exception as exc:
        error = exc
        traceback.print_exc()
    finally:
        _finish_indexer_run(db, run_row_id, stats, error)
    return stats


def _write_parsed(db, parsed, source_id: int, import_id: int, stats: IndexerStats) -> None:
    """Write a ParsedSource bundle under a single import_id."""
    # Record refs first — events reference them
    ref_map: dict[str, int] = {}
    for record in parsed.records:
        cursor = db.execute(
            """
            INSERT INTO record_refs (source_id, import_id, raw_record_hash, raw_record_key,
                                     line_no, byte_start, byte_end, ts_raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, import_id, record.raw_record_hash, record.raw_record_key,
             record.line_no, record.byte_start, record.byte_end, _db_text(record.ts_raw)),
        )
        ref_map[record.raw_record_key] = int(cursor.lastrowid)  # type: ignore[arg-type]

    # Sessions
    session_pks: dict[tuple[str, str, str], int] = {}
    for sr in parsed.sessions:
        session_pks[sr.lookup_key] = _ensure_session_pk(db, sr)

    # Group events by run for token aggregation
    events_by_run: dict[str, list] = {}
    for ev in parsed.events:
        events_by_run.setdefault(ev.run_id, []).append(ev)

    # Runs (with token aggregation)
    for run in parsed.runs:
        session_pk = session_pks.get(run.session_lookup_key)
        if session_pk is None:
            continue
        tokens = aggregate_tokens(events_by_run.get(run.run_id, []))
        _upsert_run(db, run, session_pk, source_id, tokens)

    # Run configs
    for rc in parsed.run_configs:
        _upsert_run_config(db, rc)

    # Events
    for ev in parsed.events:
        record_ref_id = ref_map.get(ev.record_key) if ev.record_key else None
        _upsert_event(db, ev, record_ref_id, import_id)
        stats.events_written += 1

    # Tool calls
    for tc in parsed.tool_calls:
        start_ref = ref_map.get(tc.start_record_key) if tc.start_record_key else None
        end_ref = ref_map.get(tc.end_record_key) if tc.end_record_key else None
        _upsert_tool_call(db, tc, start_ref, end_ref, import_id)

    # File touches
    for ft in parsed.file_touches:
        record_ref_id = ref_map.get(ft.record_key) if ft.record_key else None
        _insert_file_touch(db, ft, record_ref_id, import_id)

    # Run edges
    for re in parsed.run_edges:
        _upsert_run_edge(db, re)

    # Session denorm refresh — populate list-view / filter fields
    _refresh_session_denorm(db, [pk for pk in session_pks.values()])


def _refresh_session_denorm(db: sqlite3.Connection, session_pks: list[int]) -> None:
    """Recompute sessions.start_ts / end_ts / duration / model / first_message
    etc. from the runs/events we just wrote. Idempotent per-session."""
    if not session_pks:
        return
    placeholders = ", ".join("?" for _ in session_pks)
    db.execute(
        f"""
        UPDATE sessions AS s SET
            start_ts = (
                SELECT MIN(r.started_at) FROM runs r WHERE r.session_pk = s.session_pk
            ),
            end_ts = (
                SELECT MAX(r.ended_at) FROM runs r WHERE r.session_pk = s.session_pk
            ),
            duration_min = (
                SELECT ROUND(
                    (julianday(MAX(r.ended_at)) - julianday(MIN(r.started_at))) * 24 * 60, 1
                ) FROM runs r WHERE r.session_pk = s.session_pk
            ),
            model = (
                SELECT r.model_resolved FROM runs r
                WHERE r.session_pk = s.session_pk AND r.model_resolved IS NOT NULL
                ORDER BY r.started_at LIMIT 1
            ),
            first_message = (
                SELECT substr(e.text, 1, 200) FROM events e
                JOIN runs r ON r.run_id = e.run_id
                WHERE r.session_pk = s.session_pk AND e.kind = 'user_message'
                ORDER BY r.started_at, e.seq LIMIT 1
            ),
            transcript_lines = (
                SELECT COUNT(*) FROM events e
                JOIN runs r ON r.run_id = e.run_id
                WHERE r.session_pk = s.session_pk
            ),
            -- subagent_count: events emitted by a subagent are marked with
            -- kind 'subagent_*' or role 'subagent' by the adapters (Claude's
            -- Agent tool produces these). Cheap to derive here.
            subagent_count = (
                SELECT COUNT(DISTINCT tc.tool_call_id) FROM tool_calls tc
                JOIN runs r ON r.run_id = tc.run_id
                WHERE r.session_pk = s.session_pk
                  AND tc.tool_name IN ('Agent', 'Task', 'spawn_agent')
            ),
            indexed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        WHERE s.session_pk IN ({placeholders})
        """,
        session_pks,
    )
