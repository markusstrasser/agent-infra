-- Knowledge substrate schema v1
-- One DB per project, shared schema across intel/selve/genomics.
-- Domain-specific fields go in payload (JSON).

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Core objects --

CREATE TABLE IF NOT EXISTS assertions (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,      -- domain-specific: thesis, claim, variant_classification, ...
    status      TEXT NOT NULL DEFAULT 'active',  -- active, stale, invalidated, superseded, ...
    title       TEXT,               -- human-readable short description
    source_file TEXT,               -- markdown file this assertion appears in (if any)
    payload     TEXT DEFAULT '{}',  -- JSON: domain-specific fields (confidence, acmg_criteria, ...)
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE IF NOT EXISTS evidence (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,      -- paper, database, observation, computation, expert, ...
    status      TEXT NOT NULL DEFAULT 'active',  -- active, stale, retracted, superseded
    source      TEXT NOT NULL,      -- doi:..., clinvar:..., url:..., file:...
    title       TEXT,
    source_grade TEXT,              -- NATO Admiralty: A1, B2, C3, etc. (optional)
    payload     TEXT DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE IF NOT EXISTS artifacts (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,      -- memo, report, pipeline_output, dataset, ...
    status      TEXT NOT NULL DEFAULT 'active',  -- active, stale, outdated, superseded
    path        TEXT,               -- file path relative to project root
    title       TEXT,
    payload     TEXT DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

-- Derivations: multi-input processes that produce outputs --
-- A derivation links N inputs to M outputs through a named process.

CREATE TABLE IF NOT EXISTS derivations (
    id          TEXT PRIMARY KEY,
    process     TEXT NOT NULL,      -- what produced this: "literature_review", "pipeline_run", "synthesis", ...
    description TEXT,
    payload     TEXT DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE IF NOT EXISTS derivation_inputs (
    derivation_id TEXT NOT NULL REFERENCES derivations(id) ON DELETE CASCADE,
    input_id      TEXT NOT NULL,
    input_type    TEXT NOT NULL CHECK (input_type IN ('assertion', 'evidence', 'artifact')),
    PRIMARY KEY (derivation_id, input_id, input_type)
);

CREATE TABLE IF NOT EXISTS derivation_outputs (
    derivation_id TEXT NOT NULL REFERENCES derivations(id) ON DELETE CASCADE,
    output_id     TEXT NOT NULL,
    output_type   TEXT NOT NULL CHECK (output_type IN ('assertion', 'artifact')),
    PRIMARY KEY (derivation_id, output_id, output_type)
);

-- Typed relations between any two objects --

CREATE TABLE IF NOT EXISTS relations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('assertion', 'evidence', 'artifact')),
    target_id   TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK (target_type IN ('assertion', 'evidence', 'artifact')),
    relation    TEXT NOT NULL,      -- supported_by, contradicted_by, supersedes, depends_on, derived_from, ...
    payload     TEXT DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    UNIQUE (source_id, source_type, target_id, target_type, relation)
);

-- Append-only change log --

CREATE TABLE IF NOT EXISTS changelog (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id   TEXT NOT NULL,
    object_type TEXT NOT NULL,
    action      TEXT NOT NULL,      -- created, updated, status_changed, stale_propagated, ...
    old_value   TEXT,               -- JSON: previous state (for status changes)
    new_value   TEXT,               -- JSON: new state
    reason      TEXT,               -- why this change happened
    timestamp   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

-- Cross-project references (stored as data, not FK constraints) --

CREATE TABLE IF NOT EXISTS cross_project_refs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    local_id    TEXT NOT NULL,
    local_type  TEXT NOT NULL,
    remote_project TEXT NOT NULL,   -- "intel", "selve", "genomics"
    remote_id   TEXT NOT NULL,
    remote_type TEXT NOT NULL,
    relation    TEXT NOT NULL,      -- depends_on, derived_from, consumes, ...
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    UNIQUE (local_id, local_type, remote_project, remote_id, remote_type, relation)
);

-- Indexes for common queries --

CREATE INDEX IF NOT EXISTS idx_assertions_status ON assertions(status);
CREATE INDEX IF NOT EXISTS idx_assertions_type ON assertions(type);
CREATE INDEX IF NOT EXISTS idx_assertions_source_file ON assertions(source_file);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence(type);
CREATE INDEX IF NOT EXISTS idx_evidence_status ON evidence(status);
CREATE INDEX IF NOT EXISTS idx_artifacts_status ON artifacts(status);
CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id, source_type);
CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id, target_type);
CREATE INDEX IF NOT EXISTS idx_changelog_object ON changelog(object_id, object_type);
CREATE INDEX IF NOT EXISTS idx_changelog_timestamp ON changelog(timestamp);
CREATE INDEX IF NOT EXISTS idx_cross_project_remote ON cross_project_refs(remote_project, remote_id);
CREATE INDEX IF NOT EXISTS idx_derivation_inputs_input ON derivation_inputs(input_id, input_type);
CREATE INDEX IF NOT EXISTS idx_derivation_outputs_output ON derivation_outputs(output_id, output_type);
