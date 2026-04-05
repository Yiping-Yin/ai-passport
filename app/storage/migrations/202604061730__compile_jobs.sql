BEGIN;

CREATE TABLE IF NOT EXISTS compile_jobs (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    requested_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    last_error TEXT,
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1)
);

CREATE INDEX IF NOT EXISTS idx_compile_jobs_source_id ON compile_jobs(source_id, requested_at DESC, attempt_number DESC);
CREATE INDEX IF NOT EXISTS idx_compile_jobs_workspace_id ON compile_jobs(workspace_id, status, requested_at DESC);

COMMIT;
