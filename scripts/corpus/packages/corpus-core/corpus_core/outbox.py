"""Cross-repo outbox primitive for the substrate-v2 cross-attestation pattern.

Per-repo mutation gateways INSERT annotation intent into a
`pending_corpus_attestations` table inside the same transaction as the
domain write. After the gateway releases its writer lock, the drainer
flushes intent rows to corpus filesystem via `corpus_core.annotate`. A
crash between commit and drain is recoverable by the audit job.

This module provides the THREE pieces that genuinely repeat across repos:

  1. `outbox_schema(natural_key)`     — parameterized CREATE TABLE DDL
  2. `ensure_lifecycle_columns(con)`  — idempotent ALTER ADD COLUMN helper
  3. `drain(con, *, ...)`             — generic read-emit-delete loop

Per-repo code still owns:

  - the natural key shape (verdict_id, cert_event_id, …)
  - the enqueue INSERT inside the gateway transaction
  - the domain → annotation kwargs mapping at enqueue time

The contract that's shared (and enforced by this module) is the OUTBOX
TABLE SHAPE: every per-repo outbox has the same columns past the natural
key. The drainer is fully generic because the column → annotate-kwarg
mapping is 1:1.

Why corpus_core owns this: `corpus_core.annotate` is already the sole
writer for annotations.jsonl across all repos. The outbox is "how you
wire your repo's writes into that sole writer." Co-locating eliminates
the n-th repo's copy-paste of the same drain loop.

See: decisions/2026-05-26-cross-attestation-substrate-v2.md;
plans/2026-05-27-substrate-v2-deferred-items.md Phase 2.5.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .annotate import AnnotationError, annotate as _annotate
from .schema_version import (
    SCHEMA_META_DDL,
    OUTBOX_SCHEMA_VERSION,
    OUTBOX_MIN_READER,
    bump_schema,
    seed_outbox_meta,
    verify_outbox_schema,
)
from .store import paper_path

if TYPE_CHECKING:
    import duckdb


OUTBOX_TABLE_NAME = "pending_corpus_attestations"

# Strict allowlists for SQL identifiers interpolated into DDL/DML. The
# drainer f-strings natural_key_cols into SELECT / DELETE / UPDATE clauses;
# validating up front prevents malformed config from causing parser errors
# OR injection-shaped bugs (close-review #12). Identifiers must be plain
# snake_case (the convention every per-repo outbox follows); SQL types are
# constrained to the small set that actually makes sense for an outbox PK
# column (string ids + integer schema_version).
_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_ALLOWED_SQL_TYPES = frozenset({"VARCHAR", "INTEGER", "BIGINT", "UUID", "TEXT"})


def _validate_identifier(name: str, *, role: str) -> None:
    if not _IDENTIFIER_RE.fullmatch(name):
        raise ValueError(
            f"invalid {role} {name!r}: must match {_IDENTIFIER_RE.pattern} "
            "(snake_case, starts with letter, ≤63 chars)"
        )


def _validate_sql_type(sql_type: str) -> None:
    if sql_type not in _ALLOWED_SQL_TYPES:
        raise ValueError(
            f"invalid SQL type {sql_type!r}; allowed: {sorted(_ALLOWED_SQL_TYPES)}"
        )


def outbox_schema(natural_key: tuple[tuple[str, str], ...]) -> str:
    """Return CREATE TABLE IF NOT EXISTS DDL for the outbox.

    Args:
        natural_key: tuple of (column_name, sql_type) pairs identifying the
            domain entity being attested. Examples:
                (("verdict_id", "VARCHAR"),)              # genomics
                (("cert_event_id", "VARCHAR"),)           # phenome
                (("contradiction_event_id", "VARCHAR"),)  # intel

    The natural key columns participate in a composite PRIMARY KEY with
    canonical_source_id. Structural idempotency: a (domain_id, source_id)
    pair can only have one outbox row regardless of insertion order.

    Lifecycle columns (annotation_status, supersedes_annotation_id) are
    declared inline for greenfield CREATE — for existing tables migrating
    onto the lifecycle pattern, call `ensure_lifecycle_columns(con)`.
    """
    if not natural_key:
        raise ValueError("natural_key must have at least one column")
    for name, sqltype in natural_key:
        _validate_identifier(name, role="natural_key column")
        _validate_sql_type(sqltype)
    nk_decl = ",\n    ".join(f"{name:<20s} {sqltype} NOT NULL" for name, sqltype in natural_key)
    nk_names = ", ".join(name for name, _ in natural_key)
    return f"""
{SCHEMA_META_DDL}

INSERT INTO corpus_schema_meta
    (artifact, schema_version, min_reader_version, min_writer_version, notes)
VALUES ('outbox', '{OUTBOX_SCHEMA_VERSION}', '{OUTBOX_MIN_READER}',
        '{OUTBOX_MIN_READER}', 'composite-PK + lifecycle columns')
ON CONFLICT (artifact) DO NOTHING;

CREATE TABLE IF NOT EXISTS {OUTBOX_TABLE_NAME} (
    {nk_decl},
    canonical_source_id     VARCHAR NOT NULL,
    actor_type              VARCHAR NOT NULL,
    actor_id                VARCHAR NOT NULL,
    output_uri              VARCHAR NOT NULL,
    output_hash             VARCHAR,
    prompt_template_hash    VARCHAR,
    asserted_at             TIMESTAMP NOT NULL,
    queued_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    retry_count             INTEGER NOT NULL DEFAULT 0,
    last_error              VARCHAR,
    status                  VARCHAR NOT NULL DEFAULT 'pending',
    annotation_status       VARCHAR NOT NULL DEFAULT 'active',
    supersedes_annotation_id VARCHAR,
    valid_from              TIMESTAMP,
    PRIMARY KEY ({nk_names}, canonical_source_id)
);

CREATE INDEX IF NOT EXISTS idx_pending_corpus_status
    ON {OUTBOX_TABLE_NAME}(status);
""".strip()


def ensure_lifecycle_columns(con: "duckdb.DuckDBPyConnection") -> None:
    """Idempotently add annotation_status + supersedes_annotation_id to an
    existing outbox.

    Greenfield outboxes created via `outbox_schema(...)` already have these
    columns inline. This helper is only needed for repos that pre-date the
    lifecycle extension (genomics, where the original 2026-05-26 schema
    lacked the columns).

    DuckDB rejects ALTER TABLE ADD COLUMN with NOT NULL constraint (parser
    limitation as of 1.4); the added columns are nullable at the DB level
    and the caller is expected to supply explicit values. The drainer
    COALESCEs missing annotation_status to 'active' for safety.
    """
    import duckdb

    try:
        rows = con.execute(f"PRAGMA table_info('{OUTBOX_TABLE_NAME}')").fetchall()
    except (duckdb.CatalogException, duckdb.BinderException):
        return  # outbox table doesn't exist yet
    if not rows:
        return
    cols = {row[1] for row in rows}
    if "annotation_status" not in cols:
        con.execute(
            f"ALTER TABLE {OUTBOX_TABLE_NAME} "
            "ADD COLUMN annotation_status VARCHAR DEFAULT 'active'"
        )
        con.execute(
            f"UPDATE {OUTBOX_TABLE_NAME} "
            "SET annotation_status = 'active' WHERE annotation_status IS NULL"
        )
    if "supersedes_annotation_id" not in cols:
        con.execute(
            f"ALTER TABLE {OUTBOX_TABLE_NAME} "
            "ADD COLUMN supersedes_annotation_id VARCHAR"
        )
    # Phase A: bitemporal valid_from passthrough column. NULL-default;
    # callers pass it through to corpus_core.annotate via the drainer.
    if "valid_from" not in cols:
        con.execute(
            f"ALTER TABLE {OUTBOX_TABLE_NAME} "
            "ADD COLUMN valid_from TIMESTAMP"
        )
    # Phase G0: legacy outboxes that pre-date schema_meta need the row
    # seeded so preflight can compare against. seed first (DO NOTHING),
    # then bump to current version (DO UPDATE) — this advances 1.2.0 →
    # 1.3.0 cleanly after the ALTERs above.
    seed_outbox_meta(con)
    bump_schema(
        con,
        artifact="outbox",
        new_version=OUTBOX_SCHEMA_VERSION,
        min_reader=OUTBOX_MIN_READER,
        min_writer=OUTBOX_MIN_READER,
        notes="composite-PK + lifecycle + valid_from",
    )


@dataclass(frozen=True)
class DrainStats:
    """What a single drain() invocation accomplished."""
    flushed: int = 0       # emitted to corpus + DELETEd from outbox
    retried: int = 0       # emit failed, retry_count bumped, row stays pending
    abandoned: int = 0     # retry_count crossed 3, row flipped to status='abandoned'


def drain(
    db_path: Path | str,
    *,
    repo: str,
    scope: str,
    natural_key_cols: tuple[str, ...],
    batch_size: int = 1000,
) -> DrainStats:
    """Lock-friendly drain. Open RO to fetch pending rows, release the
    connection, perform filesystem IO without holding any DuckDB lock,
    then briefly open RW only to record DELETE/UPDATE results. This
    prevents the drainer from blocking a concurrent writer (mutation
    gateway) during corpus FS IO.

    On operational failure (OSError / AnnotationError / duckdb.IOException),
    bump retry_count; ≥3 retries flips status to 'abandoned' for human
    triage. The 3-phase pattern is the same shape audit_corpus_sync used
    bespoke before this module existed (the prior single-conn pattern held
    the writer lock for the full O(N) corpus IO loop — measured regression).

    Args:
        db_path: path to the DuckDB file containing the outbox.
        repo: corpus_core.uri scheme for this writer (e.g. 'genomics').
        scope: corpus annotation scope (e.g. 'verdict', 'cert_event').
        natural_key_cols: column names that form the natural key, in the
            same order as outbox_schema() was called.
        batch_size: cap on rows read per invocation (back-pressure).

    Returns:
        DrainStats summarizing flushed / retried / abandoned counts.

    Skip behaviour: if the DB file is missing, or the outbox table is
    absent, returns DrainStats() (zero counts) silently — these are
    expected steady-states for new or untouched repos. If the writer lock
    is contended at either phase, returns whatever was completed so far.

    Failure-mode contract: operational errors are caught + recorded; the
    drain advances row-by-row. Programmer errors (ImportError, TypeError,
    NameError) bubble loudly — those indicate contract drift between the
    gateway and the drainer that should not be swallowed.
    """
    import duckdb

    if not natural_key_cols:
        raise ValueError("natural_key_cols must have at least one column")
    for col in natural_key_cols:
        _validate_identifier(col, role="natural_key column")

    db_path = Path(db_path)
    if not db_path.exists():
        return DrainStats()

    # Phase G0 preflight: fail loud on schema skew BEFORE doing any FS IO.
    # Greenfield (no meta row, missing table) is handled by the verify
    # function — only raises when the DB exists and skew is real.
    verify_outbox_schema(db_path)

    nk_select = ", ".join(natural_key_cols)
    nk_where = " AND ".join(f"{col} = ?" for col in natural_key_cols)
    n_nk = len(natural_key_cols)

    # ---- Phase 1: RO fetch, no lock held during FS IO ----------------
    try:
        con_ro = duckdb.connect(str(db_path), read_only=True)
    except duckdb.IOException:
        return DrainStats()
    try:
        try:
            rows = con_ro.execute(
                f"""
                SELECT {nk_select},
                       canonical_source_id, actor_type, actor_id, output_uri,
                       output_hash, prompt_template_hash, asserted_at, retry_count,
                       annotation_status, supersedes_annotation_id, valid_from
                FROM {OUTBOX_TABLE_NAME}
                WHERE status = 'pending'
                LIMIT ?
                """,
                [batch_size],
            ).fetchall()
        except (duckdb.BinderException, duckdb.CatalogException):
            return DrainStats()
    finally:
        con_ro.close()

    if not rows:
        return DrainStats()

    # ---- Phase 2: FS IO with NO DuckDB lock held --------------------
    successes: list[tuple[tuple, str]] = []  # (nk_values, canon)
    failures: list[tuple[tuple, str, int, str]] = []  # (nk, canon, new_retry, err)
    for row in rows:
        nk_values = row[:n_nk]
        (
            canon, actor_type, actor_id, output_uri, output_hash,
            prompt_template_hash, asserted_at, retry_count,
            annotation_status, supersedes_annotation_id, valid_from,
        ) = row[n_nk:]
        try:
            paper_path(canon).mkdir(parents=True, exist_ok=True)
            _annotate(
                canon,
                repo=repo,
                actor_type=actor_type,
                actor_id=actor_id,
                scope=scope,
                output_uri=output_uri,
                output_hash=output_hash,
                prompt_template_hash=prompt_template_hash,
                asserted_at=asserted_at,
                status=annotation_status or "active",
                supersedes_annotation_id=supersedes_annotation_id,
                valid_from=valid_from,
            )
            successes.append((nk_values, canon))
        except (OSError, AnnotationError, duckdb.IOException) as exc:
            failures.append((nk_values, canon, retry_count + 1, str(exc)[:500]))

    # ---- Phase 3: short RW write to record DELETE/UPDATE ------------
    try:
        con_rw = duckdb.connect(str(db_path), read_only=False)
    except duckdb.IOException:
        # We did the FS IO but can't record it. Next drain re-fetches
        # the same rows — annotate is idempotent on stable_tuple so re-
        # emit is a no-op. The DB stays as-is; rows stay 'pending'.
        return DrainStats()
    flushed = retried = abandoned = 0
    try:
        for nk_values, canon in successes:
            con_rw.execute(
                f"DELETE FROM {OUTBOX_TABLE_NAME} "
                f"WHERE {nk_where} AND canonical_source_id = ?",
                [*nk_values, canon],
            )
            flushed += 1
        for nk_values, canon, new_retry, err in failures:
            new_status = "abandoned" if new_retry >= 3 else "pending"
            con_rw.execute(
                f"UPDATE {OUTBOX_TABLE_NAME} "
                f"SET retry_count = ?, last_error = ?, status = ? "
                f"WHERE {nk_where} AND canonical_source_id = ?",
                [new_retry, err, new_status, *nk_values, canon],
            )
            if new_status == "abandoned":
                abandoned += 1
            else:
                retried += 1
    finally:
        con_rw.close()
    return DrainStats(flushed=flushed, retried=retried, abandoned=abandoned)


def abandoned_count(db_path: Path | str) -> int:
    """How many rows are stuck in status='abandoned' (need human triage).
    Returns 0 when the DB file or outbox table doesn't exist, or when
    the DB is contended. RO connection — never blocks a writer."""
    import duckdb

    db_path = Path(db_path)
    if not db_path.exists():
        return 0
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except duckdb.IOException:
        return 0
    try:
        try:
            row = con.execute(
                f"SELECT COUNT(*) FROM {OUTBOX_TABLE_NAME} WHERE status = 'abandoned'"
            ).fetchone()
            return int(row[0]) if row else 0
        except (duckdb.BinderException, duckdb.CatalogException):
            return 0
    finally:
        con.close()


__all__ = [
    "OUTBOX_TABLE_NAME",
    "DrainStats",
    "abandoned_count",
    "drain",
    "ensure_lifecycle_columns",
    "outbox_schema",
]
