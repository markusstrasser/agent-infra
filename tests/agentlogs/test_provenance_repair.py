"""v9 -> v10 provenance repair preserves pointers and drops amplification."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import agentlogs
from agentlogs.migrations import (
    ExplicitProvenanceRepairRequired,
    _migration_files,
    _read_migration,
    _split_sql,
)
from agentlogs.provenance_repair import apply_repair, open_unmigrated, plan_repair


def _legacy_fixture(path: Path) -> None:
    # Build from the v10 schema, not the head: later migrations must run on reopen.
    db = sqlite3.connect(str(path), isolation_level=None)
    for version, filename in _migration_files():
        if version <= 10:
            for stmt in _split_sql(_read_migration(filename)):
                db.execute(stmt)
    db.execute("PRAGMA foreign_keys=OFF")
    for name in (
        "idx_tool_calls_start_record_ref",
        "idx_tool_calls_end_record_ref",
        "idx_file_touches_record_ref",
    ):
        db.execute(f"DROP INDEX {name}")
    db.execute(
        "CREATE TABLE record_refs_v9 ("
        "record_ref_id INTEGER PRIMARY KEY, "
        "source_id INTEGER NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE, "
        "import_id INTEGER NOT NULL REFERENCES imports(import_id) ON DELETE CASCADE, "
        "raw_record_hash TEXT NOT NULL, raw_record_key TEXT NOT NULL, "
        "line_no INTEGER, byte_start INTEGER, byte_end INTEGER, ts_raw TEXT, "
        "UNIQUE(import_id, raw_record_key))"
    )
    db.execute("DROP TABLE record_refs")
    db.execute("ALTER TABLE record_refs_v9 RENAME TO record_refs")
    db.execute("PRAGMA user_version=9")

    db.execute(
        "INSERT INTO sources (source_id, vendor, source_kind, path, sha256, discovered_at) "
        "VALUES (1, 'codex', 'transcript_jsonl', '/tmp/x.jsonl', 'sha', '2026-01-01')"
    )
    for iid, sha in ((1, "sha1"), (2, "sha2")):
        db.execute(
            "INSERT INTO imports (import_id, source_id, source_sha256, parser_name, "
            "parser_version, schema_version, imported_at, success) "
            "VALUES (?, 1, ?, 'codex', '1', 'agentlogs.v1', '2026-01-01', 1)",
            (iid, sha),
        )
    db.executemany(
        "INSERT INTO record_refs (record_ref_id, source_id, import_id, raw_record_hash, "
        "raw_record_key, line_no) VALUES (?, 1, ?, ?, ?, ?)",
        (
            (1, 1, "h1", "same", 1),
            (2, 2, "h1-new", "same", 1),
            (3, 2, "h2", "other", 2),
            (4, 2, "junk", "unreferenced", 3),
        ),
    )
    db.execute(
        "INSERT INTO sessions (session_pk, vendor, client, vendor_session_id, session_uuid) "
        "VALUES (1, 'codex', 'codex-cli', 's1', 'codex:s1')"
    )
    db.execute(
        "INSERT INTO runs (run_id, session_pk, vendor, client) "
        "VALUES ('r1', 1, 'codex', 'codex-cli')"
    )
    db.execute(
        "INSERT INTO events (event_id, run_id, import_id, seq, kind, record_ref_id) "
        "VALUES ('e1', 'r1', 2, 1, 'user_message', 2)"
    )
    db.execute(
        "INSERT INTO tool_calls (tool_call_id, run_id, import_id, tool_name, "
        "start_record_ref_id, end_record_ref_id) "
        "VALUES ('t1', 'r1', 2, 'exec', 1, 3)"
    )
    db.execute(
        "INSERT INTO file_touches (run_id, tool_call_id, import_id, path, op, record_ref_id) "
        "VALUES ('r1', 't1', 2, '/tmp/a', 'write', 2)"
    )
    db.close()


def test_populated_v9_connect_fails_loud_instead_of_rewriting(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    _legacy_fixture(path)
    with pytest.raises(ExplicitProvenanceRepairRequired, match="repair-provenance"):
        agentlogs.connect(path)


def test_repair_canonicalizes_and_remaps_every_pointer(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    _legacy_fixture(path)
    db = open_unmigrated(path)
    plan = plan_repair(db)
    assert (plan.record_refs, plan.pointer_upper_bound) == (4, 4)

    result = apply_repair(db, vacuum=False, log=lambda _message: None)
    assert (result.record_refs_before, result.record_refs_after) == (4, 2)
    assert db.execute("PRAGMA user_version").fetchone()[0] == 10
    assert "import_id" not in {r[1] for r in db.execute("PRAGMA table_info(record_refs)")}
    assert [tuple(r) for r in db.execute(
        "SELECT record_ref_id, raw_record_key FROM record_refs ORDER BY record_ref_id"
    )] == [(1, "same"), (3, "other")]
    assert db.execute(
        "SELECT raw_record_hash FROM record_refs WHERE record_ref_id=1"
    ).fetchone()[0] == "h1-new"
    assert db.execute("SELECT record_ref_id FROM events").fetchone()[0] == 1
    assert tuple(db.execute(
        "SELECT start_record_ref_id, end_record_ref_id FROM tool_calls"
    ).fetchone()) == (1, 3)
    assert db.execute("SELECT record_ref_id FROM file_touches").fetchone()[0] == 1
    assert list(db.execute("PRAGMA foreign_key_check")) == []
    db.close()

    # Normal migrated connections work after the explicit repair.
    reopened = agentlogs.connect(path)
    assert agentlogs.current_version(reopened) == 11
    reopened.close()


def test_repair_refuses_an_already_canonical_database(tmp_path: Path) -> None:
    path = tmp_path / "current.db"
    agentlogs.connect(path).close()
    db = open_unmigrated(path)
    with pytest.raises(RuntimeError, match="requires schema v9"):
        apply_repair(db, vacuum=False, log=lambda _message: None)
    db.close()
