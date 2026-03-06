PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    source_id INTEGER PRIMARY KEY,
    vendor TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    file_mtime REAL,
    size_bytes INTEGER
);

CREATE TABLE IF NOT EXISTS imports (
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

CREATE TABLE IF NOT EXISTS record_refs (
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

CREATE TABLE IF NOT EXISTS sessions (
    session_pk INTEGER PRIMARY KEY,
    vendor TEXT NOT NULL,
    client TEXT NOT NULL,
    vendor_session_id TEXT,
    synthetic_session_key TEXT,
    project_root TEXT,
    project_slug TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_vendor_session
ON sessions(vendor, client, vendor_session_id)
WHERE vendor_session_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_synthetic
ON sessions(vendor, client, synthetic_session_key)
WHERE synthetic_session_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS runs (
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
    completeness_notes TEXT
);

CREATE TABLE IF NOT EXISTS run_edges (
    src_run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    dst_run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL,
    inference_method TEXT NOT NULL,
    confidence REAL NOT NULL,
    PRIMARY KEY (src_run_id, dst_run_id, edge_type)
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    ts TEXT,
    kind TEXT NOT NULL,
    vendor_kind TEXT,
    vendor_event_id TEXT,
    role TEXT,
    text TEXT,
    payload_json TEXT,
    record_ref_id INTEGER REFERENCES record_refs(record_ref_id),
    parent_event_id TEXT REFERENCES events(event_id),
    correlation_id TEXT,
    tool_call_id TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
CREATE INDEX IF NOT EXISTS idx_events_tool_call_id ON events(tool_call_id);
CREATE INDEX IF NOT EXISTS idx_events_record_ref ON events(record_ref_id);

CREATE TABLE IF NOT EXISTS tool_calls (
    tool_call_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_source TEXT,
    mcp_server TEXT,
    ts_start TEXT,
    ts_end TEXT,
    args_json TEXT,
    result_json TEXT,
    status TEXT,
    exit_code INTEGER,
    correlation_id TEXT,
    start_record_ref_id INTEGER REFERENCES record_refs(record_ref_id),
    end_record_ref_id INTEGER REFERENCES record_refs(record_ref_id)
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_run ON tool_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_name ON tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_calls_status ON tool_calls(status);

CREATE TABLE IF NOT EXISTS file_touches (
    touch_id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    tool_call_id TEXT REFERENCES tool_calls(tool_call_id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    op TEXT NOT NULL,
    record_ref_id INTEGER REFERENCES record_refs(record_ref_id)
);

CREATE INDEX IF NOT EXISTS idx_file_touches_path ON file_touches(path);
CREATE INDEX IF NOT EXISTS idx_file_touches_run ON file_touches(run_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_file_touches_unique ON file_touches(run_id, tool_call_id, path, op);

CREATE TABLE IF NOT EXISTS run_configs (
    run_id TEXT PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
    instruction_ref TEXT,
    tools_json TEXT,
    mcp_servers_json TEXT,
    metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_vendor_started ON runs(vendor, started_at);
CREATE INDEX IF NOT EXISTS idx_runs_model_route ON runs(provider_name, model_requested, model_resolved, transport);
CREATE INDEX IF NOT EXISTS idx_runs_hashes ON runs(instruction_hash, config_hash, mcp_set_hash);
