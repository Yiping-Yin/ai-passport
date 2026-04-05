"""Typed domain entities for the AI Knowledge Passport MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.enums import (
    AccessMode,
    CandidateStatus,
    CandidateType,
    CardType,
    CompileJobStatus,
    FocusStatus,
    NodeType,
    PassportReadiness,
    PermissionLevel,
    PrivacyLevel,
    SessionStatus,
    SourceType,
    VisaStatus,
    WorkspaceType,
    WritebackPolicy,
)
from app.domain.invariants import (
    ensure_confidence,
    ensure_no_wildcards,
    ensure_non_empty,
    ensure_non_negative,
    ensure_version,
    validate_mount_session,
    validate_visa_bundle,
)


StringList = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Workspace:
    id: str
    workspace_type: WorkspaceType
    title: str
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    tags: StringList = ()
    privacy_default: PrivacyLevel = PrivacyLevel.PRIVATE
    passport_readiness: PassportReadiness = PassportReadiness.NOT_STARTED
    archived_at: datetime | None = None

    def __post_init__(self) -> None:
        ensure_non_empty("workspace.id", self.id)
        ensure_non_empty("workspace.title", self.title)


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    source_type: SourceType
    title: str
    origin: str
    imported_at: datetime
    workspace_id: str
    privacy_level: PrivacyLevel
    raw_blob_ref: str
    tags: StringList = ()

    def __post_init__(self) -> None:
        ensure_non_empty("source.id", self.id)
        ensure_non_empty("source.title", self.title)
        ensure_non_empty("source.origin", self.origin)
        ensure_non_empty("source.workspace_id", self.workspace_id)
        ensure_non_empty("source.raw_blob_ref", self.raw_blob_ref)


@dataclass(frozen=True, slots=True)
class KnowledgeNode:
    id: str
    node_type: NodeType
    title: str
    summary: str
    body: str
    source_ids: StringList
    related_node_ids: StringList
    updated_at: datetime
    workspace_id: str
    version: int = 1

    def __post_init__(self) -> None:
        ensure_non_empty("knowledge_node.id", self.id)
        ensure_non_empty("knowledge_node.title", self.title)
        ensure_non_empty("knowledge_node.workspace_id", self.workspace_id)
        ensure_version("knowledge_node.version", self.version)
        if not self.source_ids:
            raise ValueError("knowledge_node.source_ids must not be empty")


@dataclass(frozen=True, slots=True)
class EvidenceFragment:
    id: str
    source_id: str
    locator: str
    excerpt: str
    confidence: float

    def __post_init__(self) -> None:
        ensure_non_empty("evidence_fragment.id", self.id)
        ensure_non_empty("evidence_fragment.source_id", self.source_id)
        ensure_non_empty("evidence_fragment.locator", self.locator)
        ensure_non_empty("evidence_fragment.excerpt", self.excerpt)
        ensure_confidence("evidence_fragment.confidence", self.confidence)


@dataclass(frozen=True, slots=True)
class CapabilitySignal:
    id: str
    topic: str
    evidence_ids: StringList
    observed_practice: str
    current_gaps: StringList
    confidence: float
    workspace_id: str
    visibility: PrivacyLevel = PrivacyLevel.PRIVATE

    def __post_init__(self) -> None:
        ensure_non_empty("capability_signal.id", self.id)
        ensure_non_empty("capability_signal.topic", self.topic)
        ensure_non_empty("capability_signal.observed_practice", self.observed_practice)
        ensure_non_empty("capability_signal.workspace_id", self.workspace_id)
        ensure_confidence("capability_signal.confidence", self.confidence)
        if not self.evidence_ids:
            raise ValueError("capability_signal.evidence_ids must not be empty")


@dataclass(frozen=True, slots=True)
class MistakePattern:
    id: str
    topic: str
    description: str
    examples: StringList
    fix_suggestions: StringList
    recurrence_count: int
    workspace_id: str
    visibility: PrivacyLevel = PrivacyLevel.PRIVATE

    def __post_init__(self) -> None:
        ensure_non_empty("mistake_pattern.id", self.id)
        ensure_non_empty("mistake_pattern.topic", self.topic)
        ensure_non_empty("mistake_pattern.description", self.description)
        ensure_non_empty("mistake_pattern.workspace_id", self.workspace_id)
        ensure_non_negative("mistake_pattern.recurrence_count", self.recurrence_count)


@dataclass(frozen=True, slots=True)
class FocusCard:
    id: str
    title: str
    goal: str
    timeframe: str
    priority: int
    success_criteria: StringList
    related_topics: StringList
    status: FocusStatus
    workspace_id: str

    def __post_init__(self) -> None:
        ensure_non_empty("focus_card.id", self.id)
        ensure_non_empty("focus_card.title", self.title)
        ensure_non_empty("focus_card.goal", self.goal)
        ensure_non_empty("focus_card.timeframe", self.timeframe)
        ensure_non_empty("focus_card.workspace_id", self.workspace_id)
        ensure_non_negative("focus_card.priority", self.priority)
        if not self.success_criteria:
            raise ValueError("focus_card.success_criteria must not be empty")


@dataclass(frozen=True, slots=True)
class Postcard:
    id: str
    card_type: CardType
    title: str
    known_things: StringList
    done_things: StringList
    common_gaps: StringList
    active_questions: StringList
    suggested_next_step: str
    evidence_links: StringList
    related_nodes: StringList
    visibility: PrivacyLevel
    version: int
    workspace_id: str

    def __post_init__(self) -> None:
        ensure_non_empty("postcard.id", self.id)
        ensure_non_empty("postcard.title", self.title)
        ensure_non_empty("postcard.suggested_next_step", self.suggested_next_step)
        ensure_non_empty("postcard.workspace_id", self.workspace_id)
        ensure_version("postcard.version", self.version)
        if not self.evidence_links:
            raise ValueError("postcard.evidence_links must not be empty")


@dataclass(frozen=True, slots=True)
class Passport:
    id: str
    owner_summary: str
    theme_map: StringList
    capability_signal_ids: StringList
    focus_card_ids: StringList
    representative_postcard_ids: StringList
    machine_manifest: dict[str, Any]
    version: int
    workspace_id: str

    def __post_init__(self) -> None:
        ensure_non_empty("passport.id", self.id)
        ensure_non_empty("passport.owner_summary", self.owner_summary)
        ensure_non_empty("passport.workspace_id", self.workspace_id)
        ensure_version("passport.version", self.version)


@dataclass(frozen=True, slots=True)
class VisaBundle:
    id: str
    scope: StringList
    included_postcards: StringList
    included_nodes: StringList
    permission_levels: tuple[PermissionLevel, ...]
    expiry_at: datetime | None
    access_mode: AccessMode
    writeback_policy: WritebackPolicy
    redaction_rules: StringList
    status: VisaStatus
    version: int
    workspace_id: str

    def __post_init__(self) -> None:
        ensure_non_empty("visa_bundle.id", self.id)
        ensure_non_empty("visa_bundle.workspace_id", self.workspace_id)
        ensure_version("visa_bundle.version", self.version)
        ensure_no_wildcards("visa_bundle.redaction_rules", self.redaction_rules)
        validate_visa_bundle(
            scope=self.scope,
            included_postcards=self.included_postcards,
            included_nodes=self.included_nodes,
            permission_levels=self.permission_levels,
            access_mode=self.access_mode,
            writeback_policy=self.writeback_policy,
        )


@dataclass(frozen=True, slots=True)
class MountSession:
    id: str
    client_type: str
    visa_id: str
    started_at: datetime
    ended_at: datetime | None
    actions: StringList
    writeback_count: int
    status: SessionStatus

    def __post_init__(self) -> None:
        ensure_non_empty("mount_session.id", self.id)
        ensure_non_empty("mount_session.client_type", self.client_type)
        ensure_non_empty("mount_session.visa_id", self.visa_id)
        validate_mount_session(self.status, self.ended_at, self.writeback_count)


@dataclass(frozen=True, slots=True)
class ReviewCandidate:
    id: str
    session_id: str
    candidate_type: CandidateType
    content_ref: str
    target_object: str
    diff_ref: str | None
    status: CandidateStatus
    version: int
    evidence_ids: StringList = ()

    def __post_init__(self) -> None:
        ensure_non_empty("review_candidate.id", self.id)
        ensure_non_empty("review_candidate.session_id", self.session_id)
        ensure_non_empty("review_candidate.content_ref", self.content_ref)
        ensure_non_empty("review_candidate.target_object", self.target_object)
        ensure_version("review_candidate.version", self.version)


@dataclass(frozen=True, slots=True)
class AuditLog:
    id: str
    actor: str
    action: str
    object_id: str
    timestamp: datetime
    result: str
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        ensure_non_empty("audit_log.id", self.id)
        ensure_non_empty("audit_log.actor", self.actor)
        ensure_non_empty("audit_log.action", self.action)
        ensure_non_empty("audit_log.object_id", self.object_id)
        ensure_non_empty("audit_log.result", self.result)


@dataclass(frozen=True, slots=True)
class CompileJob:
    id: str
    source_id: str
    workspace_id: str
    status: CompileJobStatus
    requested_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    last_error: str | None = None
    attempt_number: int = 1

    def __post_init__(self) -> None:
        ensure_non_empty("compile_job.id", self.id)
        ensure_non_empty("compile_job.source_id", self.source_id)
        ensure_non_empty("compile_job.workspace_id", self.workspace_id)
        ensure_version("compile_job.attempt_number", self.attempt_number)
