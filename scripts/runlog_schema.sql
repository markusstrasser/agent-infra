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

-- Git commits with session attribution (evolution-forensics)
CREATE TABLE IF NOT EXISTS git_commits (
    hash TEXT NOT NULL,
    project TEXT NOT NULL,
    authored_at TEXT NOT NULL,
    author TEXT,
    subject TEXT NOT NULL,
    scope TEXT,           -- extracted from [scope] prefix
    commit_type TEXT,     -- fix, fix-of-fix, revert, feature, rule, research, chore
    session_id TEXT,      -- from Session-ID trailer
    body TEXT,
    files_changed INTEGER,
    insertions INTEGER,
    deletions INTEGER,
    PRIMARY KEY (hash, project)
);

CREATE INDEX IF NOT EXISTS idx_git_commits_session ON git_commits(session_id)
WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_git_commits_project_date ON git_commits(project, authored_at);
CREATE INDEX IF NOT EXISTS idx_git_commits_type ON git_commits(commit_type);

-- Files changed per commit
CREATE TABLE IF NOT EXISTS git_commit_files (
    hash TEXT NOT NULL,
    project TEXT NOT NULL,
    path TEXT NOT NULL,
    insertions INTEGER,
    deletions INTEGER,
    PRIMARY KEY (hash, project, path),
    FOREIGN KEY (hash, project) REFERENCES git_commits(hash, project) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_git_commit_files_path ON git_commit_files(path);

-- Churn hotspots: files with most commits in window
CREATE VIEW IF NOT EXISTS v_churn_hotspots AS
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

-- Build-then-retire: files that appear in both feature and revert commits
CREATE VIEW IF NOT EXISTS v_build_then_retire AS
SELECT
    built.project,
    built.path,
    built.hash AS built_hash,
    built.authored_at AS built_date,
    built.subject AS built_subject,
    retired.hash AS retired_hash,
    retired.authored_at AS retired_date,
    retired.subject AS retired_subject,
    ROUND(julianday(SUBSTR(retired.authored_at, 1, 19)) - julianday(SUBSTR(built.authored_at, 1, 19)), 1) AS lifespan_days
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

-- Session → commit → outcome join
CREATE VIEW IF NOT EXISTS v_session_commits AS
SELECT
    s.vendor_session_id,
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

-- Fix-of-fix chains: files fixed then fixed again within 3 days
-- Note: authored_at has timezone offsets (-0500), so we strip to first 19 chars for julianday
CREATE VIEW IF NOT EXISTS v_fix_chains AS
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
    ROUND(julianday(SUBSTR(f2.authored_at, 1, 19)) - julianday(SUBSTR(f1.authored_at, 1, 19)), 1) AS gap_days
FROM git_commits f1
JOIN git_commit_files gcf1 ON f1.hash = gcf1.hash AND f1.project = gcf1.project
JOIN git_commit_files gcf2 ON gcf1.path = gcf2.path AND gcf1.project = gcf2.project
JOIN git_commits f2 ON gcf2.hash = f2.hash AND gcf2.project = f2.project
WHERE f1.commit_type IN ('fix', 'revert')
  AND f2.commit_type IN ('fix', 'fix-of-fix', 'revert')
  AND f2.authored_at > f1.authored_at
  AND julianday(SUBSTR(f2.authored_at, 1, 19)) - julianday(SUBSTR(f1.authored_at, 1, 19)) <= 3.0
  AND f1.hash != f2.hash
ORDER BY f1.project, gcf1.path, f1.authored_at;

-- Session durability: which sessions produce code that needs subsequent fixes?
CREATE VIEW IF NOT EXISTS v_session_durability AS
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
