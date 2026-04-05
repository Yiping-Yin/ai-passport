"""Canonical enums for the AI Knowledge Passport domain."""

from __future__ import annotations

from enum import StrEnum


class WorkspaceType(StrEnum):
    PERSONAL = "personal"
    WORK = "work"
    PROJECT = "project"


class SourceType(StrEnum):
    WEB_PAGE = "web_page"
    MARKDOWN = "markdown"
    PDF = "pdf"
    PLAIN_TEXT = "plain_text"
    PROJECT_DOCUMENT = "project_document"


class PrivacyLevel(StrEnum):
    PRIVATE = "private"
    RESTRICTED = "restricted"
    SHARED = "shared"


class PassportReadiness(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    READY = "ready"


class NodeType(StrEnum):
    TOPIC = "topic"
    PROJECT = "project"
    METHOD = "method"
    QUESTION = "question"


class CardType(StrEnum):
    KNOWLEDGE = "knowledge"
    CAPABILITY = "capability"
    MISTAKE = "mistake"
    EXPLORATION = "exploration"


class FocusStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"


class CandidateType(StrEnum):
    SUMMARY = "summary"
    OUTLINE = "outline"
    QUESTION_SET = "question_set"
    TEACHING_ARTIFACT = "teaching_artifact"


class CandidateStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"
    EXPIRED = "expired"
    REVOKED = "revoked"


class VisaStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PermissionLevel(StrEnum):
    PASSPORT_READ = "passport_read"
    TOPIC_READ = "topic_read"
    WRITEBACK_CANDIDATE = "writeback_candidate"


class AccessMode(StrEnum):
    READ_ONLY = "read_only"
    CANDIDATE_WRITEBACK = "candidate_writeback"


class WritebackPolicy(StrEnum):
    REVIEW_REQUIRED = "review_required"


class CompileJobStatus(StrEnum):
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class FieldProvenance(StrEnum):
    GENERATED = "generated"
    HUMAN_EDITED = "human_edited"
    MIXED = "mixed"


class OverrideMode(StrEnum):
    REPLACE = "replace"
    MERGE = "merge"


class InsightDisposition(StrEnum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
