"""Metrics, release gates, and pilot-readiness helpers."""

from __future__ import annotations

from dataclasses import dataclass

from app.passport.service import PassportService, PostcardService
from app.storage.audit_logs import AuditLogRepository
from app.storage.mount_sessions import MountSessionRepository
from app.storage.review_candidates import ReviewCandidateRepository
from app.storage.sources import SourceRepository
from app.storage.visas import VisaBundleRepository
from app.storage.workspaces import WorkspaceRepository


@dataclass(frozen=True, slots=True)
class ReleaseGate:
    key: str
    passed: bool
    details: str


class OperationsService:
    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
        source_repository: SourceRepository,
        passport_service: PassportService,
        postcard_service: PostcardService,
        visa_repository: VisaBundleRepository,
        session_repository: MountSessionRepository,
        candidate_repository: ReviewCandidateRepository,
        audit_repository: AuditLogRepository,
    ) -> None:
        self.workspaces = workspace_repository
        self.sources = source_repository
        self.passport_service = passport_service
        self.postcard_service = postcard_service
        self.visas = visa_repository
        self.sessions = session_repository
        self.candidates = candidate_repository
        self.audit = audit_repository

    def metrics(self, workspace_id: str) -> dict[str, object]:
        workspaces = [workspace for workspace in self.workspaces.list() if workspace.id == workspace_id]
        if not workspaces:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        sessions = self._workspace_sessions(workspace_id)
        candidates = [candidate for candidate in self.candidates.list_all() if candidate.session_id in {session.id for session in sessions}]
        accepted = [candidate for candidate in candidates if candidate.status.value == "accepted"]
        representative = self.postcard_service.representative_postcards(workspace_id)
        readiness = self.passport_service.compute_readiness(workspace_id)
        return {
            "workspace_id": workspace_id,
            "passport_readiness": readiness.value,
            "representative_postcard_count": len(representative),
            "session_count": len(sessions),
            "review_candidate_count": len(candidates),
            "review_candidate_acceptance_rate": len(accepted) / len(candidates) if candidates else 0.0,
            "topic_level_visa_usage_rate": len(sessions) / len(self.sources.list_by_workspace(workspace_id)) if self.sources.list_by_workspace(workspace_id) else 0.0,
            "audit_event_count": len([event for event in self.audit.list_all() if event.meta.get("workspace_id") == workspace_id or event.object_id.startswith(workspace_id)]),
        }

    def release_gates(self, workspace_id: str) -> tuple[ReleaseGate, ...]:
        passport = self.passport_service.passports.get_by_workspace(workspace_id)
        representative = self.postcard_service.representative_postcards(workspace_id)
        sessions = self._workspace_sessions(workspace_id)
        candidates = [candidate for candidate in self.candidates.list_all() if candidate.session_id in {session.id for session in sessions}]
        export_restore_events = [
            event
            for event in self.audit.list_all()
            if event.action == "restore_workspace" and event.meta.get("workspace_id") == workspace_id
        ]
        return (
            ReleaseGate("end_to_end_flow", passport is not None and len(representative) >= 3, "Workspace can reach an initial Passport with representative postcards."),
            ReleaseGate("passport_plus_focus", passport is not None and bool(passport.focus_card_ids), "Passport manifest includes active focus and postcards."),
            ReleaseGate("visa_control", bool(sessions), "At least one mount session exists via a Visa Bundle."),
            ReleaseGate("review_queue", bool(candidates), "Writeback candidates flow into review rather than canonical state."),
            ReleaseGate("evidence_trace", self.evidence_trace_coverage(workspace_id) == 1.0, "High-level cards and Passport expose evidence links."),
            ReleaseGate("session_trace", all(candidate.session_id for candidate in candidates), "Every candidate references a mount session."),
            ReleaseGate("export_restore", bool(export_restore_events), "An export and restore cycle has been recorded."),
            ReleaseGate("pilot_feedback", False, "Awaiting real-user feedback collection."),
        )

    def evidence_trace_coverage(self, workspace_id: str) -> float:
        postcards = self.postcard_service.postcards.list_by_workspace(workspace_id)
        if not postcards:
            return 0.0
        with_evidence = [card for card in postcards if card.evidence_links]
        return len(with_evidence) / len(postcards)

    def _workspace_sessions(self, workspace_id: str):
        visas = self.visas.list_by_workspace(workspace_id)
        return [session for visa in visas for session in self.sessions.list_by_visa(visa.id)]
