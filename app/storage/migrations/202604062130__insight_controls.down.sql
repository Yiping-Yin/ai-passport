BEGIN;

ALTER TABLE capability_signals RENAME TO capability_signals_old;
CREATE TABLE capability_signals (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    evidence_ids TEXT NOT NULL,
    observed_practice TEXT NOT NULL,
    current_gaps TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    visibility TEXT NOT NULL CHECK (visibility IN ('private', 'restricted', 'shared'))
);
INSERT INTO capability_signals (id, topic, evidence_ids, observed_practice, current_gaps, confidence, workspace_id, visibility)
SELECT id, topic, evidence_ids, observed_practice, current_gaps, confidence, workspace_id, visibility
FROM capability_signals_old;
DROP TABLE capability_signals_old;

ALTER TABLE mistake_patterns RENAME TO mistake_patterns_old;
CREATE TABLE mistake_patterns (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    description TEXT NOT NULL,
    examples TEXT NOT NULL DEFAULT '[]',
    fix_suggestions TEXT NOT NULL DEFAULT '[]',
    recurrence_count INTEGER NOT NULL CHECK (recurrence_count >= 0),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    visibility TEXT NOT NULL CHECK (visibility IN ('private', 'restricted', 'shared'))
);
INSERT INTO mistake_patterns (id, topic, description, examples, fix_suggestions, recurrence_count, workspace_id, visibility)
SELECT id, topic, description, examples, fix_suggestions, recurrence_count, workspace_id, visibility
FROM mistake_patterns_old;
DROP TABLE mistake_patterns_old;

COMMIT;
