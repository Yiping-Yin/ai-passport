BEGIN;

CREATE TABLE IF NOT EXISTS node_evidence_links (
    node_id TEXT NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    evidence_fragment_id TEXT NOT NULL REFERENCES evidence_fragments(id) ON DELETE CASCADE,
    PRIMARY KEY (node_id, evidence_fragment_id)
);

CREATE INDEX IF NOT EXISTS idx_node_evidence_links_evidence_id ON node_evidence_links(evidence_fragment_id, node_id);

COMMIT;
