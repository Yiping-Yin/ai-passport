BEGIN;

ALTER TABLE mistake_patterns ADD COLUMN evidence_ids TEXT NOT NULL DEFAULT '[]';

COMMIT;
