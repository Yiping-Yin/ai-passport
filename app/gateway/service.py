"""Passport-first mount, visa, and session services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from app.domain import (
    AccessMode,
    AuditLog,
    MountSession,
    PermissionLevel,
    SessionStatus,
    VisaBundle,
    VisaStatus,
    WritebackPolicy,
    serialize_entity,
)
from app.passport.service import PassportService, PostcardService
from app.passport.signals import FocusCardService
from app.storage.audit_logs import AuditLogRepository
from app.storage.mount_sessions import MountSessionRepository
from app.storage.passports import PassportRepository
from app.storage.postcards import PostcardRepository
from app.storage.visas import VisaBundleRepository


class AuthorizationError(PermissionError):
    """Raised when a visa or session is not authorized for a requested action."""


@dataclass(frozen=True, slots=True)
class SessionReadResult:
    session: MountSession
    payload: dict[str, object]


class MountService:
    def __init__(
        self,
        *,
        visa_repository: VisaBundleRepository,
        session_repository: MountSessionRepository,
        audit_repository: AuditLogRepository,
        passport_repository: PassportRepository,
        passport_service: PassportService,
        postcard_repository: PostcardRepository,
        postcard_service: PostcardService,
        focus_service: FocusCardService,
    ) -> None:
        self.visas = visa_repository
        self.sessions = session_repository
        self.audit = audit_repository
        self.passports = passport_repository
        self.passport_service = passport_service
        self.postcards = postcard_repository
        self.postcard_service = postcard_service
        self.focus_service = focus_service

    def issue_visa(
        self,
        *,
        workspace_id: str,
        included_postcards: tuple[str, ...],
        included_nodes: tuple[str, ...],
        permission_levels: tuple[PermissionLevel, ...],
        expiry_at: datetime | None,
        access_mode: AccessMode = AccessMode.READ_ONLY,
        writeback_policy: WritebackPolicy = WritebackPolicy.REVIEW_REQUIRED,
        redaction_rules: tuple[str, ...] = (),
        scope: tuple[str, ...] = ("passport",),
    ) -> VisaBundle:
        if PermissionLevel.WRITEBACK_CANDIDATE in permission_levels and access_mode is AccessMode.READ_ONLY:
            access_mode = AccessMode.CANDIDATE_WRITEBACK
        visa = VisaBundle(
            id=f"visa-{uuid4().hex[:12]}",
            scope=scope,
            included_postcards=included_postcards,
            included_nodes=included_nodes,
            permission_levels=permission_levels,
            expiry_at=expiry_at,
            access_mode=access_mode,
            writeback_policy=writeback_policy,
            redaction_rules=redaction_rules,
            status=VisaStatus.ACTIVE,
            version=1,
            workspace_id=workspace_id,
        )
        created = self.visas.create(visa)
        self._audit("system", "issue_visa", created.id, {"workspace_id": workspace_id})
        return created

    def revoke_visa(self, visa_id: str, *, actor: str) -> VisaBundle:
        visa = self._get_visa(visa_id)
        updated = VisaBundle(
            id=visa.id,
            scope=visa.scope,
            included_postcards=visa.included_postcards,
            included_nodes=visa.included_nodes,
            permission_levels=visa.permission_levels,
            expiry_at=visa.expiry_at,
            access_mode=visa.access_mode,
            writeback_policy=visa.writeback_policy,
            redaction_rules=visa.redaction_rules,
            status=VisaStatus.REVOKED,
            version=visa.version,
            workspace_id=visa.workspace_id,
        )
        stored = self.visas.update(updated)
        self._audit(actor, "revoke_visa", visa_id, {})
        return stored

    def start_session(self, visa_id: str, *, client_type: str, started_at: datetime) -> MountSession:
        visa = self._authorize_visa(visa_id, required=PermissionLevel.PASSPORT_READ, now=started_at)
        session = MountSession(
            id=f"session-{uuid4().hex[:12]}",
            client_type=client_type,
            visa_id=visa.id,
            started_at=started_at,
            ended_at=None,
            actions=(),
            writeback_count=0,
            status=SessionStatus.ACTIVE,
        )
        created = self.sessions.create(session)
        self._audit(client_type, "start_session", created.id, {"visa_id": visa.id})
        return created

    def end_session(self, session_id: str, *, ended_at: datetime) -> MountSession:
        session = self._get_session(session_id)
        updated = MountSession(
            id=session.id,
            client_type=session.client_type,
            visa_id=session.visa_id,
            started_at=session.started_at,
            ended_at=ended_at,
            actions=session.actions,
            writeback_count=session.writeback_count,
            status=SessionStatus.ENDED,
        )
        stored = self.sessions.update(updated)
        self._audit(session.client_type, "end_session", session_id, {})
        return stored

    def read_passport_manifest(self, session_id: str) -> SessionReadResult:
        session = self._get_session(session_id)
        visa = self._authorize_visa(session.visa_id, required=PermissionLevel.PASSPORT_READ, now=session.started_at)
        passport = self.passports.get_by_workspace(visa.workspace_id)
        if passport is None:
            raise KeyError(f"No passport for workspace {visa.workspace_id}")
        updated_session = self._record_action(session, "passport_read")
        payload = self.passport_service.read_machine_manifest(passport.id)
        self._audit(session.client_type, "read_passport", passport.id, {"session_id": session_id})
        return SessionReadResult(session=updated_session, payload=payload)

    def read_postcard(self, session_id: str, postcard_id: str) -> SessionReadResult:
        session = self._get_session(session_id)
        visa = self._authorize_visa(session.visa_id, required=PermissionLevel.TOPIC_READ, now=session.started_at)
        if postcard_id not in visa.included_postcards:
            raise AuthorizationError(f"Postcard {postcard_id} is not whitelisted in visa {visa.id}")
        postcard = self.postcards.get(postcard_id)
        if postcard is None:
            raise KeyError(f"Unknown postcard: {postcard_id}")
        updated_session = self._record_action(session, f"postcard_read:{postcard_id}")
        self._audit(session.client_type, "read_postcard", postcard_id, {"session_id": session_id})
        return SessionReadResult(session=updated_session, payload={"postcard": serialize_entity(postcard)})

    def issue_default_passport_visa(self, workspace_id: str, *, expiry_at: datetime | None) -> VisaBundle:
        passport = self.passports.get_by_workspace(workspace_id)
        if passport is None:
            raise KeyError(f"No passport for workspace {workspace_id}")
        return self.issue_visa(
            workspace_id=workspace_id,
            included_postcards=passport.representative_postcard_ids,
            included_nodes=(),
            permission_levels=(PermissionLevel.PASSPORT_READ,),
            expiry_at=expiry_at,
            scope=("passport",),
        )

    def assert_no_workspace_search(self) -> None:
        raise AuthorizationError("Whole-workspace search is not available; read only explicit whitelisted objects.")

    def _record_action(self, session: MountSession, action: str) -> MountSession:
        updated = MountSession(
            id=session.id,
            client_type=session.client_type,
            visa_id=session.visa_id,
            started_at=session.started_at,
            ended_at=session.ended_at,
            actions=(*session.actions, action),
            writeback_count=session.writeback_count,
            status=session.status,
        )
        return self.sessions.update(updated)

    def _authorize_visa(self, visa_id: str, *, required: PermissionLevel, now: datetime) -> VisaBundle:
        visa = self._get_visa(visa_id)
        if visa.status is not VisaStatus.ACTIVE:
            raise AuthorizationError(f"Visa {visa_id} is not active")
        if visa.expiry_at is not None and visa.expiry_at < now:
            raise AuthorizationError(f"Visa {visa_id} is expired")
        if required not in visa.permission_levels:
            raise AuthorizationError(f"Visa {visa_id} lacks permission {required.value}")
        return visa

    def _get_visa(self, visa_id: str) -> VisaBundle:
        visa = self.visas.get(visa_id)
        if visa is None:
            raise KeyError(f"Unknown visa: {visa_id}")
        return visa

    def _get_session(self, session_id: str) -> MountSession:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session: {session_id}")
        return session

    def _audit(self, actor: str, action: str, object_id: str, meta: dict[str, object]) -> None:
        event = AuditLog(
            id=f"audit-{uuid4().hex[:12]}",
            actor=actor,
            action=action,
            object_id=object_id,
            timestamp=datetime.utcnow(),
            result="success",
            meta=meta,
        )
        self.audit.append(event)
