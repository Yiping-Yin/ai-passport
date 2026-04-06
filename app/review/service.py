"""Review queue, export, and restore services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import difflib
import json
from pathlib import Path
from uuid import uuid4

from app.compile.review import KnowledgeNodeReviewService
from app.domain import AuditLog, CandidateStatus, CandidateType, FocusStatus, ReviewCandidate, serialize_entity
from app.storage.audit_logs import AuditLogRepository
from app.storage.capability_signals import CapabilitySignalRepository
from app.storage.compile_jobs import CompileJobRepository
from app.storage.evidence import EvidenceFragmentRepository
from app.storage.focus_cards import FocusCardRepository
from app.storage.knowledge_nodes import KnowledgeNodeRepository
from app.storage.mistake_patterns import MistakePatternRepository
from app.storage.mount_sessions import MountSessionRepository
from app.storage.passports import PassportRepository
from app.storage.postcards import PostcardRepository
from app.storage.review_candidates import ReviewCandidateRepository
from app.storage.sources import SourceRepository
from app.storage.sqlite import insert_record
from app.storage.visas import VisaBundleRepository
from app.storage.workspaces import WorkspaceRepository
from app.gateway.service import MountService
from app.utils.time import utc_now


@dataclass(frozen=True, slots=True)
class CandidateDiff:
    target_object: str
    before: dict[str, object]
    after: dict[str, object]
    unified_diff: tuple[str, ...]


class ReviewService:
    def __init__(
        self,
        *,
        candidate_repository: ReviewCandidateRepository,
        session_repository: MountSessionRepository,
        audit_repository: AuditLogRepository,
        knowledge_review_service: KnowledgeNodeReviewService,
        postcard_repository: PostcardRepository,
        focus_repository: FocusCardRepository,
        mount_service: MountService | None = None,
        storage_root: Path,
    ) -> None:
        self.candidates = candidate_repository
        self.sessions = session_repository
        self.audit = audit_repository
        self.knowledge = knowledge_review_service
        self.postcards = postcard_repository
        self.focus = focus_repository
        self.mount = mount_service
        self.storage_root = storage_root

    def create_candidate(
        self,
        *,
        session_id: str,
        candidate_type: CandidateType,
        target_object: str,
        content: dict[str, object],
        evidence_ids: tuple[str, ...] = (),
    ) -> ReviewCandidate:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session: {session_id}")
        target_type, target_id = target_object.split(":", 1)
        target_workspace_id = self._target_workspace_id(target_type, target_id)
        if self.mount is not None:
            session = self.mount.authorize_writeback(
                session_id=session_id,
                target_workspace_id=target_workspace_id,
            )
        candidate_id = f"candidate-{uuid4().hex[:12]}"
        payload_path = self._write_json("candidates", candidate_id, content)
        diff = self._build_diff(target_object, content)
        diff_path = self._write_json("diffs", candidate_id, serialize_diff(diff))
        candidate = ReviewCandidate(
            id=candidate_id,
            session_id=session_id,
            candidate_type=candidate_type,
            content_ref=str(payload_path),
            target_object=target_object,
            diff_ref=str(diff_path),
            status=CandidateStatus.PENDING,
            version=1,
            evidence_ids=evidence_ids,
        )
        created = self.candidates.create(candidate)
        updated_session = type(session)(
            id=session.id,
            client_type=session.client_type,
            visa_id=session.visa_id,
            started_at=session.started_at,
            ended_at=session.ended_at,
            actions=(*session.actions, f"writeback_candidate:{candidate_id}"),
            writeback_count=session.writeback_count + 1,
            status=session.status,
        )
        self.sessions.update(updated_session)
        self._audit(session.client_type, "create_candidate", candidate_id, {"session_id": session_id})
        return created

    def read_diff(self, candidate_id: str) -> CandidateDiff:
        candidate = self._get_candidate(candidate_id)
        payload = json.loads(Path(candidate.diff_ref).read_text())
        return CandidateDiff(
            target_object=payload["target_object"],
            before=payload["before"],
            after=payload["after"],
            unified_diff=tuple(payload["unified_diff"]),
        )

    def accept_candidate(self, candidate_id: str, *, actor: str) -> ReviewCandidate:
        candidate = self._get_candidate(candidate_id)
        self._apply_candidate(candidate, override_payload=None)
        updated = ReviewCandidate(
            id=candidate.id,
            session_id=candidate.session_id,
            candidate_type=candidate.candidate_type,
            content_ref=candidate.content_ref,
            target_object=candidate.target_object,
            diff_ref=candidate.diff_ref,
            status=CandidateStatus.ACCEPTED,
            version=candidate.version,
            evidence_ids=candidate.evidence_ids,
        )
        stored = self.candidates.update(updated)
        self._audit(actor, "accept_candidate", candidate_id, {})
        return stored

    def edit_then_accept(self, candidate_id: str, *, actor: str, content_override: dict[str, object]) -> ReviewCandidate:
        candidate = self._get_candidate(candidate_id)
        self._apply_candidate(candidate, override_payload=content_override)
        updated = ReviewCandidate(
            id=candidate.id,
            session_id=candidate.session_id,
            candidate_type=candidate.candidate_type,
            content_ref=candidate.content_ref,
            target_object=candidate.target_object,
            diff_ref=candidate.diff_ref,
            status=CandidateStatus.ACCEPTED,
            version=candidate.version + 1,
            evidence_ids=candidate.evidence_ids,
        )
        stored = self.candidates.update(updated)
        self._audit(actor, "edit_accept_candidate", candidate_id, {})
        return stored

    def reject_candidate(self, candidate_id: str, *, actor: str) -> ReviewCandidate:
        candidate = self._get_candidate(candidate_id)
        updated = ReviewCandidate(
            id=candidate.id,
            session_id=candidate.session_id,
            candidate_type=candidate.candidate_type,
            content_ref=candidate.content_ref,
            target_object=candidate.target_object,
            diff_ref=candidate.diff_ref,
            status=CandidateStatus.REJECTED,
            version=candidate.version,
            evidence_ids=candidate.evidence_ids,
        )
        stored = self.candidates.update(updated)
        self._audit(actor, "reject_candidate", candidate_id, {})
        return stored

    def _apply_candidate(self, candidate: ReviewCandidate, *, override_payload: dict[str, object] | None) -> None:
        payload = json.loads(Path(candidate.content_ref).read_text())
        if override_payload:
            payload.update(override_payload)
        target_type, target_id = candidate.target_object.split(":", 1)
        if target_type == "knowledge_node":
            for field_name in ("title", "summary", "body", "related_node_ids"):
                if field_name in payload:
                    self.knowledge.set_field_override(
                        node_id=target_id,
                        field_name=field_name,
                        value=payload[field_name],
                        editor="review",
                        edited_at=utc_now(),
                    )
        elif target_type == "focus_card":
            current = self.focus.get(target_id)
            if current is None:
                raise KeyError(f"Unknown focus card: {target_id}")
            updated = type(current)(
                id=current.id,
                title=payload.get("title", current.title),
                goal=payload.get("goal", current.goal),
                timeframe=payload.get("timeframe", current.timeframe),
                priority=payload.get("priority", current.priority),
                success_criteria=tuple(payload.get("success_criteria", current.success_criteria)),
                related_topics=tuple(payload.get("related_topics", current.related_topics)),
                status=FocusStatus(payload.get("status", current.status.value)),
                workspace_id=current.workspace_id,
            )
            self.focus.update(updated)
        elif target_type == "postcard":
            postcard = self.postcards.get(target_id)
            if postcard is None:
                raise KeyError(f"Unknown postcard: {target_id}")
            updated = type(postcard)(
                id=postcard.id,
                card_type=postcard.card_type,
                title=payload.get("title", postcard.title),
                known_things=tuple(payload.get("known_things", postcard.known_things)),
                done_things=tuple(payload.get("done_things", postcard.done_things)),
                common_gaps=tuple(payload.get("common_gaps", postcard.common_gaps)),
                active_questions=tuple(payload.get("active_questions", postcard.active_questions)),
                suggested_next_step=payload.get("suggested_next_step", postcard.suggested_next_step),
                evidence_links=tuple(payload.get("evidence_links", postcard.evidence_links)),
                related_nodes=tuple(payload.get("related_nodes", postcard.related_nodes)),
                visibility=postcard.visibility,
                version=postcard.version + 1,
                workspace_id=postcard.workspace_id,
            )
            self.postcards.upsert(updated, recorded_at=utc_now())
        else:
            raise ValueError(f"Unsupported candidate target: {candidate.target_object}")

    def _build_diff(self, target_object: str, content: dict[str, object]) -> CandidateDiff:
        target_type, target_id = target_object.split(":", 1)
        if target_type == "knowledge_node":
            view = self.knowledge.effective_view(target_id)
            before = {
                "title": view.effective_node.title,
                "summary": view.effective_node.summary,
                "body": view.effective_node.body,
                "related_node_ids": list(view.effective_node.related_node_ids),
            }
        elif target_type == "postcard":
            postcard = self.postcards.get(target_id)
            if postcard is None:
                raise KeyError(f"Unknown postcard: {target_id}")
            before = {
                "title": postcard.title,
                "suggested_next_step": postcard.suggested_next_step,
                "common_gaps": list(postcard.common_gaps),
            }
        elif target_type == "focus_card":
            focus = self.focus.get(target_id)
            if focus is None:
                raise KeyError(f"Unknown focus card: {target_id}")
            before = {"title": focus.title, "goal": focus.goal, "timeframe": focus.timeframe}
        else:
            raise ValueError(f"Unsupported candidate target: {target_object}")
        after = {**before, **content}
        before_lines = json.dumps(before, indent=2, sort_keys=True).splitlines()
        after_lines = json.dumps(after, indent=2, sort_keys=True).splitlines()
        return CandidateDiff(
            target_object=target_object,
            before=before,
            after=after,
            unified_diff=tuple(
                difflib.unified_diff(before_lines, after_lines, fromfile="before", tofile="after", lineterm="")
            ),
        )

    def _write_json(self, directory_name: str, stem: str, payload: dict[str, object]) -> Path:
        directory = self.storage_root / directory_name
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{stem}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return path

    def _get_candidate(self, candidate_id: str) -> ReviewCandidate:
        candidate = self.candidates.get(candidate_id)
        if candidate is None:
            raise KeyError(f"Unknown review candidate: {candidate_id}")
        return candidate

    def _audit(self, actor: str, action: str, object_id: str, meta: dict[str, object]) -> None:
        event = AuditLog(
            id=f"audit-{uuid4().hex[:12]}",
            actor=actor,
            action=action,
            object_id=object_id,
            timestamp=utc_now(),
            result="success",
            meta=meta,
        )
        self.audit.append(event)

    def _target_workspace_id(self, target_type: str, target_id: str) -> str:
        if target_type == "knowledge_node":
            view = self.knowledge.effective_view(target_id)
            return view.effective_node.workspace_id
        if target_type == "postcard":
            postcard = self.postcards.get(target_id)
            if postcard is None:
                raise KeyError(f"Unknown postcard: {target_id}")
            return postcard.workspace_id
        if target_type == "focus_card":
            focus = self.focus.get(target_id)
            if focus is None:
                raise KeyError(f"Unknown focus card: {target_id}")
            return focus.workspace_id
        raise ValueError(f"Unsupported candidate target: {target_type}")


def serialize_diff(diff: CandidateDiff) -> dict[str, object]:
    return {
        "target_object": diff.target_object,
        "before": diff.before,
        "after": diff.after,
        "unified_diff": list(diff.unified_diff),
    }


class ExportRestoreService:
    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
        source_repository: SourceRepository,
        knowledge_node_repository: KnowledgeNodeRepository,
        evidence_repository: EvidenceFragmentRepository,
        capability_signal_repository: CapabilitySignalRepository,
        mistake_pattern_repository: MistakePatternRepository,
        focus_repository: FocusCardRepository,
        compile_job_repository: CompileJobRepository,
        passport_repository: PassportRepository,
        postcard_repository: PostcardRepository,
        visa_repository: VisaBundleRepository,
        session_repository: MountSessionRepository,
        candidate_repository: ReviewCandidateRepository,
        audit_repository: AuditLogRepository,
        export_root: Path,
        raw_root: Path,
    ) -> None:
        self.workspaces = workspace_repository
        self.sources = source_repository
        self.nodes = knowledge_node_repository
        self.evidence = evidence_repository
        self.signals = capability_signal_repository
        self.mistakes = mistake_pattern_repository
        self.focus = focus_repository
        self.compile_jobs = compile_job_repository
        self.passports = passport_repository
        self.postcards = postcard_repository
        self.visas = visa_repository
        self.sessions = session_repository
        self.candidates = candidate_repository
        self.audit = audit_repository
        self.export_root = export_root
        self.raw_root = raw_root

    def export_workspace(self, workspace_id: str, *, include_hidden: bool = False) -> Path:
        workspace = self.workspaces.get(workspace_id)
        if workspace is None:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        sources = self.sources.list_by_workspace(workspace_id)
        visible_postcards = self.postcards.list_by_workspace(workspace_id, include_hidden=include_hidden)
        passport = self.passports.get_by_workspace(workspace_id)
        if passport and not include_hidden:
            visible_ids = {card.id for card in visible_postcards}
            manifest = dict(passport.machine_manifest)
            manifest["representative_postcards"] = [
                item
                for item in manifest.get("representative_postcards", [])
                if item.get("id") in visible_ids
            ]
            passport_payload = serialize_entity(
                type(passport)(
                    id=passport.id,
                    owner_summary=passport.owner_summary,
                    theme_map=passport.theme_map,
                    capability_signal_ids=passport.capability_signal_ids,
                    focus_card_ids=passport.focus_card_ids,
                    representative_postcard_ids=tuple(
                        postcard_id for postcard_id in passport.representative_postcard_ids if postcard_id in visible_ids
                    ),
                    machine_manifest=manifest,
                    version=passport.version,
                    workspace_id=passport.workspace_id,
                )
            )
        else:
            passport_payload = serialize_entity(passport) if passport else None
        visas = self.visas.list_by_workspace(workspace_id)
        visa_ids = {visa.id for visa in visas}
        sessions = [session for visa_id in visa_ids for session in self.sessions.list_by_visa(visa_id)]
        session_ids = {session.id for session in sessions}
        raw_files = {
            source.id: {
                "relative_path": self._relative_raw_path(source.raw_blob_ref),
                "content": Path(source.raw_blob_ref).read_text(),
            }
            for source in sources
        }
        review_candidates = [
            serialize_entity(candidate)
            for candidate in self.candidates.list_all()
            if candidate.session_id in session_ids
        ]
        candidate_files = {
            candidate["id"]: {
                "content": json.loads(Path(candidate["content_ref"]).read_text()) if candidate.get("content_ref") else None,
                "diff": json.loads(Path(candidate["diff_ref"]).read_text()) if candidate.get("diff_ref") else None,
            }
            for candidate in review_candidates
        }
        export = {
            "workspace": serialize_entity(workspace),
            "sources": [serialize_entity(source) for source in sources],
            "knowledge_nodes": [serialize_entity(node) for node in self.nodes.list_by_workspace(workspace_id)],
            "evidence_fragments": [
                serialize_entity(fragment)
                for source in sources
                for fragment in self.evidence.list_for_source(source.id)
            ],
            "capability_signals": [
                serialize_entity(signal)
                for signal in self.signals.list_by_workspace(workspace_id)
                if include_hidden or signal.visibility.value != "restricted"
            ],
            "mistake_patterns": [
                serialize_entity(pattern)
                for pattern in self.mistakes.list_by_workspace(workspace_id)
                if (include_hidden or pattern.visibility.value != "restricted") and pattern.disposition.value != "dismissed"
            ],
            "focus_cards": [serialize_entity(card) for card in self.focus.list_by_workspace(workspace_id)],
            "compile_jobs": [serialize_entity(job) for job in self.compile_jobs.list_for_workspace(workspace_id)],
            "postcards": [serialize_entity(card) for card in visible_postcards],
            "passport": passport_payload,
            "visas": [serialize_entity(visa) for visa in visas],
            "mount_sessions": [serialize_entity(session) for session in sessions],
            "review_candidates": review_candidates,
            "candidate_files": candidate_files,
            "audit_logs": [
                serialize_entity(entry)
                for entry in self.audit.list_all()
                if entry.object_id.startswith(workspace_id) or entry.meta.get("workspace_id") == workspace_id
            ],
            "raw_files": raw_files,
        }
        self.export_root.mkdir(parents=True, exist_ok=True)
        path = self.export_root / f"{workspace_id}-export.json"
        path.write_text(json.dumps(export, indent=2, sort_keys=True) + "\n")
        self.audit.append(
            AuditLog(
                id=f"audit-{uuid4().hex[:12]}",
                actor="system",
                action="export_workspace",
                object_id=workspace_id,
                timestamp=utc_now(),
                result="success",
                meta={"path": str(path), "include_hidden": include_hidden, "workspace_id": workspace_id},
            )
        )
        return path

    def restore_workspace(self, path: Path) -> dict[str, object]:
        payload = json.loads(path.read_text())
        workspace = payload["workspace"]
        raw_files = payload.get("raw_files", {})
        candidate_files = payload.get("candidate_files", {})
        for source in payload.get("sources", []):
            raw_info = raw_files.get(source["id"])
            if raw_info:
                raw_path = self.raw_root / raw_info["relative_path"]
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(raw_info["content"])
                source["raw_blob_ref"] = str(raw_path)
        for candidate in payload.get("review_candidates", []):
            file_info = candidate_files.get(candidate["id"], {})
            if file_info.get("content") is not None:
                content_path = self._write_json("candidates", candidate["id"], file_info["content"])
                candidate["content_ref"] = str(content_path)
            if file_info.get("diff") is not None:
                diff_path = self._write_json("diffs", candidate["id"], file_info["diff"])
                candidate["diff_ref"] = str(diff_path)

        table_order = [
            ("workspaces", [workspace]),
            ("sources", payload.get("sources", [])),
            ("knowledge_nodes", payload.get("knowledge_nodes", [])),
            ("evidence_fragments", payload.get("evidence_fragments", [])),
            ("capability_signals", payload.get("capability_signals", [])),
            ("mistake_patterns", payload.get("mistake_patterns", [])),
            ("focus_cards", payload.get("focus_cards", [])),
            ("compile_jobs", payload.get("compile_jobs", [])),
            ("postcards", payload.get("postcards", [])),
            ("passports", [payload["passport"]] if payload.get("passport") else []),
            ("visa_bundles", payload.get("visas", [])),
            ("mount_sessions", payload.get("mount_sessions", [])),
            ("review_candidates", payload.get("review_candidates", [])),
            ("audit_logs", payload.get("audit_logs", [])),
        ]
        connection = self.workspaces.connection
        for table, records in table_order:
            for record in records:
                insert_record(connection, table, record)
        connection.commit()
        self.audit.append(
            AuditLog(
                id=f"audit-{uuid4().hex[:12]}",
                actor="system",
                action="restore_workspace",
                object_id=payload["workspace"]["id"],
                timestamp=utc_now(),
                result="success",
                meta={"path": str(path), "workspace_id": payload["workspace"]["id"]},
            )
        )
        return payload

    def _relative_raw_path(self, raw_blob_ref: str) -> str:
        path = Path(raw_blob_ref)
        try:
            return str(path.relative_to(self.raw_root))
        except ValueError:
            return path.name

    def _write_json(self, directory_name: str, stem: str, payload: dict[str, object]) -> Path:
        directory = self.export_root.parent / directory_name
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{stem}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return path
