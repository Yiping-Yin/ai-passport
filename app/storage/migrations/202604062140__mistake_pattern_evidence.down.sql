BEGIN;

ALTER TABLE mistake_patterns RENAME TO mistake_patterns_old2;
CREATE TABLE mistake_patterns (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    description TEXT NOT NULL,
    examples TEXT NOT NULL DEFAULT '[]',
    fix_suggestions TEXT NOT NULL DEFAULT '[]',
    recurrence_count INTEGER NOT NULL CHECK (recurrence_count >= 0),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    visibility TEXT NOT NULL CHECK (visibility IN ('private', 'restricted', 'shared')),
    version INTEGER NOT NULL DEFAULT 1,
    disposition TEXT NOT NULL DEFAULT 'suggested' CHECK (disposition IN ('suggested', 'confirmed', 'dismissed'))
);
INSERT INTO mistake_patterns (id, topic, description, examples, fix_suggestions, recurrence_count, workspace_id, visibility, version, disposition)
SELECT id, topic, description, examples, fix_suggestions, recurrence_count, workspace_id, visibility, version, disposition
FROM mistake_patterns_old2;
DROP TABLE mistake_patterns_old2;

COMMIT;
