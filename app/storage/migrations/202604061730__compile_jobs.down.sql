BEGIN;

DROP INDEX IF EXISTS idx_compile_jobs_workspace_id;
DROP INDEX IF EXISTS idx_compile_jobs_source_id;
DROP TABLE IF EXISTS compile_jobs;

COMMIT;
