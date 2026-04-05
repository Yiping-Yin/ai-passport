BEGIN;

CREATE TABLE IF NOT EXISTS postcard_revisions (
    id TEXT PRIMARY KEY,
    postcard_id TEXT NOT NULL REFERENCES postcards(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK (version >= 1),
    card_type TEXT NOT NULL,
    title TEXT NOT NULL,
    known_things TEXT NOT NULL DEFAULT '[]',
    done_things TEXT NOT NULL DEFAULT '[]',
    common_gaps TEXT NOT NULL DEFAULT '[]',
    active_questions TEXT NOT NULL DEFAULT '[]',
    suggested_next_step TEXT NOT NULL,
    evidence_links TEXT NOT NULL DEFAULT '[]',
    related_nodes TEXT NOT NULL DEFAULT '[]',
    visibility TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_postcard_revisions_postcard_id ON postcard_revisions(postcard_id, version ASC);
CREATE INDEX IF NOT EXISTS idx_postcard_revisions_workspace_id ON postcard_revisions(workspace_id, recorded_at DESC);

COMMIT;
