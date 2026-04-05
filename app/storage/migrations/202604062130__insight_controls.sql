BEGIN;

ALTER TABLE capability_signals ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE capability_signals ADD COLUMN disposition TEXT NOT NULL DEFAULT 'suggested' CHECK (disposition IN ('suggested', 'confirmed', 'dismissed'));

ALTER TABLE mistake_patterns ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE mistake_patterns ADD COLUMN disposition TEXT NOT NULL DEFAULT 'suggested' CHECK (disposition IN ('suggested', 'confirmed', 'dismissed'));

COMMIT;
