"""Sticky event_id on (run_id, seq) re-import — agentlogs PK thrash fix.

Continuation-append re-imports used to reassign event_id via
ON CONFLICT(run_id, seq) DO UPDATE SET event_id = excluded.event_id.
When the re-parse mapped a different stable_id onto an existing seq that
already lived at another row, events.event_id PK violated → bulk
executemany failed → per-row fallback thrashed under launchd deadline.

Post-fix: (run_id, seq) conflict keeps the original event_id; mutable
fields still refresh; new seqs INSERT. Mapping-shift re-imports must not
raise IntegrityError.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import agentlogs
from agentlogs import index as ix


def _seed_run(db, run_id: str = "run-1") -> int:
    db.execute(
        "INSERT INTO sessions (session_uuid, vendor, client, vendor_session_id) "
        "VALUES ('codex:s1', 'codex', 'codex-cli', 's1')"
    )
    spk = db.execute("SELECT session_pk FROM sessions").fetchone()[0]
    db.execute(
        "INSERT INTO sources (vendor, source_kind, path, sha256, discovered_at) "
        "VALUES ('codex', 'transcript_jsonl', '/tmp/fake.jsonl', 'abc', '2026-01-01')"
    )
    sid = db.execute("SELECT source_id FROM sources").fetchone()[0]
    db.execute(
        "INSERT INTO runs (run_id, session_pk, vendor, client, started_at, primary_source_id) "
        "VALUES (?, ?, 'codex', 'codex-cli', '2026-01-01', ?)",
        (run_id, spk, sid),
    )
    db.execute(
        "INSERT INTO imports (source_id, source_sha256, parser_name, parser_version, "
        "schema_version, imported_at, success) "
        "VALUES (?, 'abc', 'codex', '1', '1', '2026-01-01', 1)",
        (sid,),
    )
    return int(db.execute("SELECT import_id FROM imports").fetchone()[0])


def test_sticky_event_id_survives_mapping_shift(tmp_path: Path) -> None:
    """Re-import with swapped seq↔event_id must keep original ids, not PK-crash."""
    db = agentlogs.connect(tmp_path / "sticky.db")
    # Ensure schema has UNIQUE(run_id, seq)
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq)"
    )
    iid = _seed_run(db)

    # Initial layout: seq1→id-A, seq2→id-B
    for seq, eid, text in ((1, "id-A", "first"), (2, "id-B", "second")):
        row = SimpleNamespace(
            event_id=eid,
            run_id="run-1",
            seq=seq,
            ts="2026-01-01T00:00:00Z",
            kind="message",
            vendor_kind=None,
            vendor_event_id=None,
            role="user",
            text=text,
            payload=None,
            parent_event_id=None,
            correlation_id=None,
            tool_call_id=None,
        )
        ix._upsert_event(db, row, None, iid)

    # Mapping shift: seq1→id-B, seq2→id-A (the thrash pattern) + new text
    for seq, eid, text in ((1, "id-B", "first-v2"), (2, "id-A", "second-v2")):
        row = SimpleNamespace(
            event_id=eid,
            run_id="run-1",
            seq=seq,
            ts="2026-01-01T00:01:00Z",
            kind="message",
            vendor_kind=None,
            vendor_event_id=None,
            role="user",
            text=text,
            payload=None,
            parent_event_id=None,
            correlation_id=None,
            tool_call_id=None,
        )
        ix._upsert_event(db, row, None, iid)  # must not raise

    rows = {
        r["seq"]: (r["event_id"], r["text"])
        for r in db.execute(
            "SELECT seq, event_id, text FROM events WHERE run_id='run-1' ORDER BY seq"
        )
    }
    # Sticky: original event_ids stay on their seqs
    assert rows[1][0] == "id-A"
    assert rows[2][0] == "id-B"
    # Mutable fields still refresh
    assert rows[1][1] == "first-v2"
    assert rows[2][1] == "second-v2"
    db.close()


def test_write_parsed_bulk_high_water_append_only(tmp_path: Path) -> None:
    """Continuation re-import writes only seq > max; no IntegrityError thrash."""
    db = agentlogs.connect(tmp_path / "bulk.db")
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq)"
    )
    iid1 = _seed_run(db)

    def _ev(eid, seq, text):
        return SimpleNamespace(
            event_id=eid,
            run_id="run-1",
            seq=seq,
            ts="2026-01-01T00:00:00Z",
            kind="message",
            vendor_kind=None,
            vendor_event_id=None,
            role="user",
            text=text,
            payload=None,
            parent_event_id=None,
            correlation_id=None,
            tool_call_id=None,
            record_key=None,
        )

    parsed1 = SimpleNamespace(
        records=[],
        sessions=[],
        runs=[],
        run_configs=[],
        events=[_ev("id-A", 1, "a"), _ev("id-B", 2, "b"), _ev("id-C", 3, "c")],
        tool_calls=[],
        file_touches=[],
        run_edges=[],
    )
    stats = ix.IndexerStats()
    ix._write_parsed(db, parsed1, source_id=1, import_id=iid1, stats=stats)
    assert stats.events_written == 3

    # Full re-parse with mapping shift on old seqs + true append — high-water
    # must skip seq≤3 and only write seq 4 (no bulk IntegrityError path).
    parsed2 = SimpleNamespace(
        records=[],
        sessions=[],
        runs=[],
        run_configs=[],
        events=[
            _ev("id-C", 1, "a2"),  # remapped — skipped by high-water
            _ev("id-A", 2, "b2"),
            _ev("id-B", 3, "c2"),
            _ev("id-D", 4, "d"),   # true append
        ],
        tool_calls=[],
        file_touches=[],
        run_edges=[],
    )
    stats2 = ix.IndexerStats()
    ix._write_parsed(db, parsed2, source_id=1, import_id=iid1, stats=stats2)
    assert stats2.events_written == 1  # only the append

    rows = list(
        db.execute(
            "SELECT seq, event_id, text FROM events WHERE run_id='run-1' ORDER BY seq"
        )
    )
    assert [(r[0], r[1], r[2]) for r in rows] == [
        (1, "id-A", "a"),   # untouched (high-water)
        (2, "id-B", "b"),
        (3, "id-C", "c"),
        (4, "id-D", "d"),   # new
    ]
    db.close()


def test_write_parsed_skips_recycled_event_id(tmp_path: Path) -> None:
    """New seq whose event_id already exists is skipped, not bulk-aborted."""
    db = agentlogs.connect(tmp_path / "recycle.db")
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq)"
    )
    iid = _seed_run(db)

    def _ev(eid, seq):
        return SimpleNamespace(
            event_id=eid,
            run_id="run-1",
            seq=seq,
            ts="2026-01-01T00:00:00Z",
            kind="message",
            vendor_kind=None,
            vendor_event_id=None,
            role="user",
            text="t",
            payload=None,
            parent_event_id=None,
            correlation_id=None,
            tool_call_id=None,
            record_key=None,
        )

    empty = dict(records=[], sessions=[], runs=[], run_configs=[],
                 tool_calls=[], file_touches=[], run_edges=[])
    stats = ix.IndexerStats()
    ix._write_parsed(
        db,
        SimpleNamespace(**empty, events=[_ev("id-A", 1)]),
        source_id=1, import_id=iid, stats=stats,
    )
    # New seq reuses id-A — must skip, not raise
    stats2 = ix.IndexerStats()
    ix._write_parsed(
        db,
        SimpleNamespace(**empty, events=[_ev("id-A", 2), _ev("id-B", 3)]),
        source_id=1, import_id=iid, stats=stats2,
    )
    assert stats2.events_written == 1  # only id-B
    seqs = [r[0] for r in db.execute(
        "SELECT seq FROM events WHERE run_id='run-1' ORDER BY seq"
    )]
    assert seqs == [1, 3]
    db.close()
