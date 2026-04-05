BEGIN;

DROP INDEX IF EXISTS idx_node_evidence_links_evidence_id;
DROP TABLE IF EXISTS node_evidence_links;

COMMIT;
