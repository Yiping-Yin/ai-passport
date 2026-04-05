BEGIN;

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    workspace_type TEXT NOT NULL CHECK (workspace_type IN ('personal', 'work', 'project')),
    title TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    privacy_default TEXT NOT NULL CHECK (privacy_default IN ('private', 'restricted', 'shared')),
    passport_readiness TEXT NOT NULL CHECK (passport_readiness IN ('not_started', 'in_progress', 'ready')),
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL CHECK (source_type IN ('web_page', 'markdown', 'pdf', 'plain_text', 'project_document')),
    title TEXT NOT NULL,
    origin TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    privacy_level TEXT NOT NULL CHECK (privacy_level IN ('private', 'restricted', 'shared')),
    raw_blob_ref TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL CHECK (node_type IN ('topic', 'project', 'method', 'question')),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    source_ids TEXT NOT NULL,
    related_node_ids TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK (version >= 1)
);

CREATE TABLE IF NOT EXISTS evidence_fragments (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    locator TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

CREATE TABLE IF NOT EXISTS capability_signals (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    evidence_ids TEXT NOT NULL,
    observed_practice TEXT NOT NULL,
    current_gaps TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    visibility TEXT NOT NULL CHECK (visibility IN ('private', 'restricted', 'shared'))
);

CREATE TABLE IF NOT EXISTS mistake_patterns (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    description TEXT NOT NULL,
    examples TEXT NOT NULL DEFAULT '[]',
    fix_suggestions TEXT NOT NULL DEFAULT '[]',
    recurrence_count INTEGER NOT NULL CHECK (recurrence_count >= 0),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    visibility TEXT NOT NULL CHECK (visibility IN ('private', 'restricted', 'shared'))
);

CREATE TABLE IF NOT EXISTS focus_cards (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    goal TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    priority INTEGER NOT NULL CHECK (priority >= 0),
    success_criteria TEXT NOT NULL,
    related_topics TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK (status IN ('active', 'archived', 'closed')),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS postcards (
    id TEXT PRIMARY KEY,
    card_type TEXT NOT NULL CHECK (card_type IN ('knowledge', 'capability', 'mistake', 'exploration')),
    title TEXT NOT NULL,
    known_things TEXT NOT NULL DEFAULT '[]',
    done_things TEXT NOT NULL DEFAULT '[]',
    common_gaps TEXT NOT NULL DEFAULT '[]',
    active_questions TEXT NOT NULL DEFAULT '[]',
    suggested_next_step TEXT NOT NULL,
    evidence_links TEXT NOT NULL DEFAULT '[]',
    related_nodes TEXT NOT NULL DEFAULT '[]',
    visibility TEXT NOT NULL CHECK (visibility IN ('private', 'restricted', 'shared')),
    version INTEGER NOT NULL CHECK (version >= 1),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS passports (
    id TEXT PRIMARY KEY,
    owner_summary TEXT NOT NULL,
    theme_map TEXT NOT NULL DEFAULT '[]',
    capability_signal_ids TEXT NOT NULL DEFAULT '[]',
    focus_card_ids TEXT NOT NULL DEFAULT '[]',
    representative_postcard_ids TEXT NOT NULL DEFAULT '[]',
    machine_manifest TEXT NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL CHECK (version >= 1),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS visa_bundles (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL DEFAULT '[]',
    included_postcards TEXT NOT NULL DEFAULT '[]',
    included_nodes TEXT NOT NULL DEFAULT '[]',
    permission_levels TEXT NOT NULL DEFAULT '[]',
    expiry_at TEXT,
    access_mode TEXT NOT NULL CHECK (access_mode IN ('read_only', 'candidate_writeback')),
    writeback_policy TEXT NOT NULL CHECK (writeback_policy IN ('review_required')),
    redaction_rules TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK (status IN ('active', 'expired', 'revoked')),
    version INTEGER NOT NULL CHECK (version >= 1),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mount_sessions (
    id TEXT PRIMARY KEY,
    client_type TEXT NOT NULL,
    visa_id TEXT NOT NULL REFERENCES visa_bundles(id) ON DELETE CASCADE,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    actions TEXT NOT NULL DEFAULT '[]',
    writeback_count INTEGER NOT NULL CHECK (writeback_count >= 0),
    status TEXT NOT NULL CHECK (status IN ('active', 'ended', 'expired', 'revoked'))
);

CREATE TABLE IF NOT EXISTS review_candidates (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES mount_sessions(id) ON DELETE CASCADE,
    candidate_type TEXT NOT NULL CHECK (candidate_type IN ('summary', 'outline', 'question_set', 'teaching_artifact')),
    content_ref TEXT NOT NULL,
    target_object TEXT NOT NULL,
    diff_ref TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'rejected')),
    version INTEGER NOT NULL CHECK (version >= 1),
    evidence_ids TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    object_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    result TEXT NOT NULL,
    meta TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_sources_workspace_id ON sources(workspace_id, imported_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_workspace_id ON knowledge_nodes(workspace_id, node_type);
CREATE INDEX IF NOT EXISTS idx_evidence_fragments_source_id ON evidence_fragments(source_id);
CREATE INDEX IF NOT EXISTS idx_capability_signals_workspace_id ON capability_signals(workspace_id, topic);
CREATE INDEX IF NOT EXISTS idx_mistake_patterns_workspace_id ON mistake_patterns(workspace_id, topic);
CREATE INDEX IF NOT EXISTS idx_focus_cards_workspace_id ON focus_cards(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_postcards_workspace_id ON postcards(workspace_id, card_type);
CREATE INDEX IF NOT EXISTS idx_passports_workspace_id ON passports(workspace_id);
CREATE INDEX IF NOT EXISTS idx_visa_bundles_workspace_id ON visa_bundles(workspace_id, status, expiry_at);
CREATE INDEX IF NOT EXISTS idx_mount_sessions_visa_id ON mount_sessions(visa_id, status);
CREATE INDEX IF NOT EXISTS idx_review_candidates_session_id ON review_candidates(session_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_object_id ON audit_logs(object_id, timestamp);

COMMIT;
