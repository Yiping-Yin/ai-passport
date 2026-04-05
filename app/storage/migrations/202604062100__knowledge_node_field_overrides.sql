BEGIN;

CREATE TABLE IF NOT EXISTS knowledge_node_field_overrides (
    node_id TEXT NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL CHECK (field_name IN ('title', 'summary', 'body', 'related_node_ids')),
    override_mode TEXT NOT NULL CHECK (override_mode IN ('replace', 'merge')),
    value_json TEXT NOT NULL,
    edited_at TEXT NOT NULL,
    editor TEXT NOT NULL,
    PRIMARY KEY (node_id, field_name)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_node_field_overrides_editor ON knowledge_node_field_overrides(editor, edited_at DESC);

COMMIT;
