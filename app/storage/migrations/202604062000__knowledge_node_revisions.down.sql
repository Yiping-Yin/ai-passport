BEGIN;

DROP INDEX IF EXISTS idx_knowledge_node_revisions_workspace_id;
DROP INDEX IF EXISTS idx_knowledge_node_revisions_node_id;
DROP TABLE IF EXISTS knowledge_node_revisions;

COMMIT;
