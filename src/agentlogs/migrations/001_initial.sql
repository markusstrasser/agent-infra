-- agentlogs migration 001 — initial schema
-- Consolidates ~/.claude/sessions.db + ~/.claude/runlogs.db.
-- See .claude/plans/8799d138-unified-agent-logs.md

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- Provenance
-- -----------------------------------------------------------------------------

CREATE TABLE sources (
    source_id INTEGER PRIMARY KEY,
    vendor TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    file_mtime REAL,
    size_bytes INTEGER
);

CREATE TABLE imports (
    import_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    source_sha256 TEXT NOT NULL,
    parser_name TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    success INTEGER NOT NULL,
    error_json TEXT,
    UNIQUE(source_id, source_sha256, parser_name, parser_version, schema_version)
);

CREATE TABLE record_refs (
    record_ref_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    import_id INTEGER NOT NULL REFERENCES imports(import_id) ON DELETE CASCADE,
    raw_record_hash TEXT NOT NULL,
    raw_record_key TEXT NOT NULL,
    line_no INTEGER,
    byte_start INTEGER,
    byte_end INTEGER,
    ts_raw TEXT,
    UNIQUE(import_id, raw_record_key)
);

-- -----------------------------------------------------------------------------
-- Sessions (first-class, cross-vendor)
-- -----------------------------------------------------------------------------

CREATE TABLE sessions (
    session_pk INTEGER PRIMARY KEY,
    vendor TEXT NOT NULL,
    client TEXT NOT NULL,
    vendor_session_id TEXT,
    synthetic_session_key TEXT,
    session_uuid TEXT,                  -- canonical cross-vendor key (CLI/API surface)
    project_root TEXT,
    project_slug TEXT,

    -- Denormalized metadata (derived from runs+events at ingest; no transcript text)
    start_ts TEXT,
    end_ts TEXT,
    duration_min REAL,
    cost_usd REAL,
    context_pct INTEGER,
    model TEXT,
    first_message TEXT,                 -- ~200 char list-view denorm (not FTS)
    transcript_lines INTEGER,
    subagent_count INTEGER,
    lines_added INTEGER,
    lines_removed INTEGER,
    harness_hash TEXT,
    indexed_at TEXT
);

CREATE UNIQUE INDEX idx_sessions_vendor_session
    ON sessions(vendor, client, vendor_session_id)
    WHERE vendor_session_id IS NOT NULL;

CREATE UNIQUE INDEX idx_sessions_synthetic
    ON sessions(vendor, client, synthetic_session_key)
    WHERE synthetic_session_key IS NOT NULL;

CREATE UNIQUE INDEX idx_sessions_uuid
    ON sessions(session_uuid)
    WHERE session_uuid IS NOT NULL;

CREATE INDEX idx_sessions_project_start
    ON sessions(project_slug, start_ts);

-- -----------------------------------------------------------------------------
-- Runs (one per prompt+response cycle; many per session)
-- -----------------------------------------------------------------------------

CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    session_pk INTEGER NOT NULL REFERENCES sessions(session_pk) ON DELETE CASCADE,
    vendor TEXT NOT NULL,
    client TEXT NOT NULL,
    transport TEXT,
    protocol TEXT,
    provider_name TEXT,
    base_url TEXT,
    cwd TEXT,
    started_at TEXT,
    ended_at TEXT,
    status TEXT,
    model_requested TEXT,
    model_resolved TEXT,
    approval_mode TEXT,
    sandbox_mode TEXT,
    instruction_hash TEXT,
    config_hash TEXT,
    mcp_set_hash TEXT,
    git_head TEXT,
    primary_source_id INTEGER REFERENCES sources(source_id),
    completeness TEXT,
    completeness_notes TEXT,

    -- Structured token counts (promoted from payload_json per Phase 0 findings)
    input_tokens INTEGER,
    cached_tokens INTEGER,
    output_tokens INTEGER,
    reasoning_tokens INTEGER,
    total_tokens INTEGER
);

CREATE TABLE run_edges (
    src_run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    dst_run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL,
    inference_method TEXT NOT NULL,
    confidence REAL NOT NULL,
    PRIMARY KEY (src_run_id, dst_run_id, edge_type)
);

CREATE INDEX idx_runs_vendor_started ON runs(vendor, started_at);
CREATE INDEX idx_runs_model_route ON runs(provider_name, model_requested, model_resolved, transport);
CREATE INDEX idx_runs_hashes ON runs(instruction_hash, config_hash, mcp_set_hash);
CREATE INDEX idx_runs_session ON runs(session_pk);

-- -----------------------------------------------------------------------------
-- Events, tool calls, file touches (per-run detail)
-- All carry import_id FK so re-imports can DELETE WHERE import_id IN (...)
-- -----------------------------------------------------------------------------

CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    import_id INTEGER REFERENCES imports(import_id),
    seq INTEGER NOT NULL,
    ts TEXT,
    kind TEXT NOT NULL,
    vendor_kind TEXT,
    vendor_event_id TEXT,
    role TEXT,
    text TEXT,
    payload_json TEXT,                  -- metadata only; verbose content lives in text
    record_ref_id INTEGER REFERENCES record_refs(record_ref_id),
    parent_event_id TEXT REFERENCES events(event_id),
    correlation_id TEXT,
    tool_call_id TEXT
);

CREATE UNIQUE INDEX idx_events_run_seq ON events(run_id, seq);
CREATE INDEX idx_events_kind ON events(kind);
CREATE INDEX idx_events_tool_call_id ON events(tool_call_id);
CREATE INDEX idx_events_record_ref ON events(record_ref_id);
CREATE INDEX idx_events_import ON events(import_id);

CREATE TABLE tool_calls (
    tool_call_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    import_id INTEGER REFERENCES imports(import_id),
    tool_name TEXT NOT NULL,
    tool_source TEXT,
    mcp_server TEXT,
    ts_start TEXT,
    ts_end TEXT,
    args_json TEXT,                     -- tool input args (analytics-valuable)
    -- result_json intentionally NOT stored — duplicates the tool_result event's text.
    status TEXT,
    exit_code INTEGER,
    correlation_id TEXT,
    start_record_ref_id INTEGER REFERENCES record_refs(record_ref_id),
    end_record_ref_id INTEGER REFERENCES record_refs(record_ref_id)
);

CREATE INDEX idx_tool_calls_run ON tool_calls(run_id);
CREATE INDEX idx_tool_calls_name ON tool_calls(tool_name);
CREATE INDEX idx_tool_calls_status ON tool_calls(status);
CREATE INDEX idx_tool_calls_import ON tool_calls(import_id);

CREATE TABLE file_touches (
    touch_id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    tool_call_id TEXT REFERENCES tool_calls(tool_call_id) ON DELETE CASCADE,
    import_id INTEGER REFERENCES imports(import_id),
    path TEXT NOT NULL,
    op TEXT NOT NULL,
    record_ref_id INTEGER REFERENCES record_refs(record_ref_id)
);

CREATE INDEX idx_file_touches_path ON file_touches(path);
CREATE INDEX idx_file_touches_run ON file_touches(run_id);
CREATE INDEX idx_file_touches_import ON file_touches(import_id);
CREATE UNIQUE INDEX idx_file_touches_unique ON file_touches(run_id, tool_call_id, path, op);

CREATE TABLE run_configs (
    run_id TEXT PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
    instruction_ref TEXT,
    tools_json TEXT,
    mcp_servers_json TEXT,
    metadata_json TEXT
);

-- -----------------------------------------------------------------------------
-- Session quality (ported from sessions.db)
-- -----------------------------------------------------------------------------

CREATE TABLE session_quality (
    session_pk INTEGER PRIMARY KEY REFERENCES sessions(session_pk) ON DELETE CASCADE,
    quality_score REAL,
    quality_notes TEXT,
    scored_at TEXT,
    scorer TEXT
);

-- Trace index for improvement-log failure patterns
CREATE TABLE trace_index (
    trace_id INTEGER PRIMARY KEY,
    pattern TEXT NOT NULL,
    session_pk INTEGER REFERENCES sessions(session_pk) ON DELETE CASCADE,
    session_uuid TEXT,
    date_seen TEXT,
    source_line INTEGER,
    severity TEXT,
    notes TEXT
);

CREATE INDEX idx_trace_index_pattern ON trace_index(pattern);
CREATE INDEX idx_trace_index_session ON trace_index(session_pk);

-- -----------------------------------------------------------------------------
-- Git commits + attribution
-- -----------------------------------------------------------------------------

CREATE TABLE git_commits (
    hash TEXT NOT NULL,
    project TEXT NOT NULL,
    authored_at TEXT NOT NULL,
    author TEXT,
    subject TEXT NOT NULL,
    scope TEXT,
    commit_type TEXT,
    session_id TEXT,
    body TEXT,
    files_changed INTEGER,
    insertions INTEGER,
    deletions INTEGER,
    PRIMARY KEY (hash, project)
);

CREATE INDEX idx_git_commits_session ON git_commits(session_id)
    WHERE session_id IS NOT NULL;
CREATE INDEX idx_git_commits_project_date ON git_commits(project, authored_at);
CREATE INDEX idx_git_commits_type ON git_commits(commit_type);

CREATE TABLE git_commit_files (
    hash TEXT NOT NULL,
    project TEXT NOT NULL,
    path TEXT NOT NULL,
    insertions INTEGER,
    deletions INTEGER,
    PRIMARY KEY (hash, project, path),
    FOREIGN KEY (hash, project) REFERENCES git_commits(hash, project) ON DELETE CASCADE
);

CREATE INDEX idx_git_commit_files_path ON git_commit_files(path);

-- -----------------------------------------------------------------------------
-- Indexer observability
-- -----------------------------------------------------------------------------

CREATE TABLE indexer_runs (
    run_id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    vendor TEXT,                -- 'all' or specific vendor
    sources_discovered INTEGER DEFAULT 0,
    sources_imported INTEGER DEFAULT 0,
    sources_skipped INTEGER DEFAULT 0,
    sources_failed INTEGER DEFAULT 0,
    events_written INTEGER DEFAULT 0,
    status TEXT NOT NULL,       -- 'running' | 'success' | 'error'
    error_class TEXT,
    error_message TEXT
);

CREATE INDEX idx_indexer_runs_status ON indexer_runs(status, started_at);

-- -----------------------------------------------------------------------------
-- FTS5 — external-content over events.text, trigger-maintained
-- -----------------------------------------------------------------------------

CREATE VIRTUAL TABLE events_fts USING fts5(
    text,
    content='events',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

CREATE TRIGGER events_ai AFTER INSERT ON events BEGIN
    INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text);
END;

CREATE TRIGGER events_ad AFTER DELETE ON events BEGIN
    INSERT INTO events_fts(events_fts, rowid, text) VALUES('delete', old.rowid, old.text);
END;

CREATE TRIGGER events_au AFTER UPDATE ON events BEGIN
    INSERT INTO events_fts(events_fts, rowid, text) VALUES('delete', old.rowid, old.text);
    INSERT INTO events_fts(rowid, text) VALUES (new.rowid, new.text);
END;

-- -----------------------------------------------------------------------------
-- Views
-- -----------------------------------------------------------------------------

CREATE VIEW v_churn_hotspots AS
SELECT
    gc.project,
    gcf.path,
    COUNT(DISTINCT gc.hash) AS commits,
    SUM(CASE WHEN gc.commit_type IN ('fix', 'fix-of-fix') THEN 1 ELSE 0 END) AS fix_commits,
    SUM(CASE WHEN gc.commit_type = 'revert' THEN 1 ELSE 0 END) AS reverts,
    GROUP_CONCAT(DISTINCT gc.commit_type) AS types
FROM git_commit_files gcf
JOIN git_commits gc ON gc.hash = gcf.hash AND gc.project = gcf.project
GROUP BY gc.project, gcf.path
HAVING commits >= 5
ORDER BY commits DESC;

CREATE VIEW v_build_then_retire AS
SELECT
    built.project,
    built.path,
    built.hash AS built_hash,
    built.authored_at AS built_date,
    built.subject AS built_subject,
    retired.hash AS retired_hash,
    retired.authored_at AS retired_date,
    retired.subject AS retired_subject,
    ROUND(julianday(retired.authored_at) - julianday(built.authored_at), 1) AS lifespan_days
FROM (
    SELECT gc.project, gcf.path, gc.hash, gc.authored_at, gc.subject
    FROM git_commits gc
    JOIN git_commit_files gcf ON gc.hash = gcf.hash AND gc.project = gcf.project
    WHERE gc.commit_type = 'feature'
) built
JOIN (
    SELECT gc.project, gcf.path, gc.hash, gc.authored_at, gc.subject
    FROM git_commits gc
    JOIN git_commit_files gcf ON gc.hash = gcf.hash AND gc.project = gcf.project
    WHERE gc.commit_type = 'revert'
) retired ON built.project = retired.project
    AND built.path = retired.path
    AND retired.authored_at > built.authored_at
ORDER BY lifespan_days ASC;

CREATE VIEW v_session_commits AS
SELECT
    s.vendor_session_id,
    s.session_uuid,
    s.project_slug,
    gc.hash,
    gc.project,
    gc.authored_at,
    gc.subject,
    gc.scope,
    gc.commit_type,
    gc.files_changed,
    gc.insertions,
    gc.deletions
FROM git_commits gc
JOIN sessions s ON gc.session_id = s.vendor_session_id
ORDER BY gc.authored_at;

CREATE VIEW v_fix_chains AS
SELECT
    f1.project,
    gcf1.path,
    f1.hash AS fix1_hash,
    f1.authored_at AS fix1_date,
    f1.subject AS fix1_subject,
    f1.session_id AS fix1_session,
    f2.hash AS fix2_hash,
    f2.authored_at AS fix2_date,
    f2.subject AS fix2_subject,
    f2.session_id AS fix2_session,
    ROUND(julianday(f2.authored_at) - julianday(f1.authored_at), 1) AS gap_days
FROM git_commits f1
JOIN git_commit_files gcf1 ON f1.hash = gcf1.hash AND f1.project = gcf1.project
JOIN git_commit_files gcf2 ON gcf1.path = gcf2.path AND gcf1.project = gcf2.project
JOIN git_commits f2 ON gcf2.hash = f2.hash AND gcf2.project = f2.project
WHERE f1.commit_type IN ('fix', 'revert')
  AND f2.commit_type IN ('fix', 'fix-of-fix', 'revert')
  AND f2.authored_at > f1.authored_at
  AND julianday(f2.authored_at) - julianday(f1.authored_at) <= 3.0
  AND f1.hash != f2.hash
ORDER BY f1.project, gcf1.path, f1.authored_at;

CREATE VIEW v_session_durability AS
SELECT
    gc.session_id,
    gc.project,
    COUNT(DISTINCT gc.hash) AS commits_produced,
    COUNT(DISTINCT CASE WHEN fc.fix2_hash IS NOT NULL THEN gc.hash END) AS commits_later_fixed,
    ROUND(
        COUNT(DISTINCT CASE WHEN fc.fix2_hash IS NOT NULL THEN gc.hash END) * 100.0
        / MAX(COUNT(DISTINCT gc.hash), 1),
    1) AS fragility_pct
FROM git_commits gc
LEFT JOIN v_fix_chains fc ON gc.hash = fc.fix1_hash AND gc.project = fc.project
WHERE gc.session_id IS NOT NULL
GROUP BY gc.session_id, gc.project
ORDER BY fragility_pct DESC;

-- Latest indexer health per vendor (for `agentlogs stats`)
CREATE VIEW v_indexer_health AS
SELECT
    vendor,
    MAX(started_at) FILTER (WHERE status='success') AS last_success_at,
    MAX(started_at) FILTER (WHERE status='error')   AS last_error_at,
    COUNT(*) FILTER (WHERE status='success')        AS success_count_total,
    COUNT(*) FILTER (WHERE status='error')          AS error_count_total,
    COUNT(*) FILTER (WHERE status='success'
                     AND started_at > datetime('now', '-7 days')) AS success_7d,
    COUNT(*) FILTER (WHERE status='error'
                     AND started_at > datetime('now', '-7 days')) AS error_7d
FROM indexer_runs
WHERE vendor IS NOT NULL
GROUP BY vendor;

PRAGMA user_version = 1;
