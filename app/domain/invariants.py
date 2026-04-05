"""Validation helpers for domain invariants."""

from __future__ import annotations

from datetime import datetime

from app.domain.enums import AccessMode, PermissionLevel, SessionStatus, WritebackPolicy


class DomainValidationError(ValueError):
    """Raised when a domain object violates a product invariant."""


def ensure_non_empty(name: str, value: str) -> None:
    if not value.strip():
        raise DomainValidationError(f"{name} must be non-empty")


def ensure_version(name: str, value: int) -> None:
    if value < 1:
        raise DomainValidationError(f"{name} must be >= 1")


def ensure_confidence(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise DomainValidationError(f"{name} must be between 0.0 and 1.0")


def ensure_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise DomainValidationError(f"{name} must be >= 0")


def ensure_no_wildcards(name: str, values: tuple[str, ...]) -> None:
    if any(value == "*" for value in values):
        raise DomainValidationError(f"{name} must not contain wildcard access")


def validate_visa_bundle(
    *,
    scope: tuple[str, ...],
    included_postcards: tuple[str, ...],
    included_nodes: tuple[str, ...],
    permission_levels: tuple[PermissionLevel, ...],
    access_mode: AccessMode,
    writeback_policy: WritebackPolicy,
) -> None:
    ensure_no_wildcards("scope", scope)
    ensure_no_wildcards("included_postcards", included_postcards)
    ensure_no_wildcards("included_nodes", included_nodes)

    if PermissionLevel.PASSPORT_READ not in permission_levels:
        raise DomainValidationError("visa bundles must always include passport_read")

    if PermissionLevel.TOPIC_READ in permission_levels and not (included_postcards or included_nodes):
        raise DomainValidationError("topic_read requires an explicit whitelist of postcards or nodes")

    if PermissionLevel.WRITEBACK_CANDIDATE in permission_levels:
        if access_mode is not AccessMode.CANDIDATE_WRITEBACK:
            raise DomainValidationError("writeback_candidate permission requires candidate_writeback mode")
        if writeback_policy is not WritebackPolicy.REVIEW_REQUIRED:
            raise DomainValidationError("writeback_candidate must remain review_required")
    elif access_mode is not AccessMode.READ_ONLY:
        raise DomainValidationError("read-only-first access forbids writeback mode without explicit permission")


def validate_mount_session(status: SessionStatus, ended_at: datetime | None, writeback_count: int) -> None:
    ensure_non_negative("writeback_count", writeback_count)
    if status is SessionStatus.ACTIVE and ended_at is not None:
        raise DomainValidationError("active mount sessions cannot have ended_at set")
    if status is not SessionStatus.ACTIVE and ended_at is None:
        raise DomainValidationError("closed mount sessions must set ended_at")
