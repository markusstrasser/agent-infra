-- agentlogs migration 010 — source-record provenance has source-stable identity.
--
-- Existing non-empty v9 databases are deliberately blocked by apply_migrations:
-- use `agentlogs repair-provenance --yes` on a clone, verify it, then swap.
-- This SQL therefore handles fresh/empty databases only. The explicit repair
-- path performs the equivalent rewrite while preserving and remapping pointers.

CREATE TABLE record_refs_v10 (
    record_ref_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    raw_record_hash TEXT NOT NULL,
    raw_record_key TEXT NOT NULL,
    line_no INTEGER,
    byte_start INTEGER,
    byte_end INTEGER,
    ts_raw TEXT,
    UNIQUE(source_id, raw_record_key)
);

DROP TABLE record_refs;
ALTER TABLE record_refs_v10 RENAME TO record_refs;

CREATE INDEX idx_tool_calls_start_record_ref ON tool_calls(start_record_ref_id);
CREATE INDEX idx_tool_calls_end_record_ref ON tool_calls(end_record_ref_id);
CREATE INDEX idx_file_touches_record_ref ON file_touches(record_ref_id);

PRAGMA user_version = 10;

