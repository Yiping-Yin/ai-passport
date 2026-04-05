BEGIN;

CREATE TABLE IF NOT EXISTS knowledge_node_revisions (
    id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK (version >= 1),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    source_ids TEXT NOT NULL,
    related_node_ids TEXT NOT NULL DEFAULT '[]',
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_node_revisions_node_id ON knowledge_node_revisions(node_id, version ASC);
CREATE INDEX IF NOT EXISTS idx_knowledge_node_revisions_workspace_id ON knowledge_node_revisions(workspace_id, recorded_at DESC);

COMMIT;
