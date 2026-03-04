-- Orchestrator task queue schema.
-- Location: ~/.claude/orchestrator.db (created by orchestrator.py init-db)

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    pipeline TEXT,
    step TEXT,
    project TEXT NOT NULL,
    prompt TEXT NOT NULL,
    engine TEXT DEFAULT 'claude',
    status TEXT DEFAULT 'pending',
    depends_on INTEGER REFERENCES tasks(id),
    priority INTEGER DEFAULT 5,
    max_turns INTEGER DEFAULT 15,
    max_budget_usd REAL DEFAULT 5.0,
    model TEXT,
    agent TEXT,
    allowed_tools TEXT,
    effort TEXT,
    cwd TEXT,
    requires_approval INTEGER DEFAULT 0,
    approved_at TEXT,
    blocked_reason TEXT,
    output_file TEXT,
    result_summary TEXT,
    cost_usd REAL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    subagents TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    started_at TEXT,
    finished_at TEXT,
    error TEXT,
    step_options TEXT
);

CREATE TABLE IF NOT EXISTS pipelines (
    name TEXT PRIMARY KEY,
    template TEXT NOT NULL,
    project TEXT NOT NULL,
    schedule TEXT,
    pause_before TEXT,
    last_run TEXT,
    enabled INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_tasks_claimable
    ON tasks(status, priority, created_at)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_tasks_finished
    ON tasks(finished_at)
    WHERE finished_at IS NOT NULL;
