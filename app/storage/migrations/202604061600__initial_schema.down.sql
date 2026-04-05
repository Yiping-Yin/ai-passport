BEGIN;

DROP INDEX IF EXISTS idx_audit_logs_object_id;
DROP INDEX IF EXISTS idx_review_candidates_session_id;
DROP INDEX IF EXISTS idx_mount_sessions_visa_id;
DROP INDEX IF EXISTS idx_visa_bundles_workspace_id;
DROP INDEX IF EXISTS idx_passports_workspace_id;
DROP INDEX IF EXISTS idx_postcards_workspace_id;
DROP INDEX IF EXISTS idx_focus_cards_workspace_id;
DROP INDEX IF EXISTS idx_mistake_patterns_workspace_id;
DROP INDEX IF EXISTS idx_capability_signals_workspace_id;
DROP INDEX IF EXISTS idx_evidence_fragments_source_id;
DROP INDEX IF EXISTS idx_knowledge_nodes_workspace_id;
DROP INDEX IF EXISTS idx_sources_workspace_id;

DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS review_candidates;
DROP TABLE IF EXISTS mount_sessions;
DROP TABLE IF EXISTS visa_bundles;
DROP TABLE IF EXISTS passports;
DROP TABLE IF EXISTS postcards;
DROP TABLE IF EXISTS focus_cards;
DROP TABLE IF EXISTS mistake_patterns;
DROP TABLE IF EXISTS capability_signals;
DROP TABLE IF EXISTS evidence_fragments;
DROP TABLE IF EXISTS knowledge_nodes;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS workspaces;

COMMIT;
