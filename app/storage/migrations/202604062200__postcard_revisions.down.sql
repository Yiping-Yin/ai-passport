BEGIN;

DROP INDEX IF EXISTS idx_postcard_revisions_workspace_id;
DROP INDEX IF EXISTS idx_postcard_revisions_postcard_id;
DROP TABLE IF EXISTS postcard_revisions;

COMMIT;
