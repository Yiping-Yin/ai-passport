from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.compile.review import KnowledgeNodeReviewService
from app.compile.service import KnowledgeCompileService
from app.domain import CandidateType, PermissionLevel, SourceType, WorkspaceType
from app.gateway.service import AuthorizationError, MountService
from app.ingest.service import RawSourceStore, SourceImportRequest, SourceImportService
from app.passport.service import PassportService, PostcardService
from app.passport.signals import CapabilitySignalService, FocusCardService
from app.review.service import ReviewService
from app.storage.audit_logs import AuditLogRepository
from app.storage.capability_signals import CapabilitySignalRepository
from app.storage.compile_jobs import CompileJobRepository
from app.storage.evidence import EvidenceFragmentRepository
from app.storage.focus_cards import FocusCardRepository
from app.storage.knowledge_nodes import KnowledgeNodeRepository
from app.storage.migrate import migrate_up
from app.storage.mistake_patterns import MistakePatternRepository
from app.storage.mount_sessions import MountSessionRepository
from app.storage.node_evidence_links import NodeEvidenceLinkRepository
from app.storage.node_overrides import KnowledgeNodeOverrideRepository
from app.storage.passports import PassportRepository
from app.storage.postcards import PostcardRepository
from app.storage.review_candidates import ReviewCandidateRepository
from app.storage.sources import SourceRepository
from app.storage.sqlite import connect
from app.storage.visas import VisaBundleRepository
from app.storage.workspaces import WorkspaceRepository
from app.api.workspaces import WorkspaceService
from app.utils.time import utc_now


NOW = datetime(2026, 4, 7, 9, 0, 0)
FIXTURE = """
## Topic: Python Typing
Summary: Types improve correctness.
Related: Method: Dataclass Serialization, Question: How should versions change?
Typed models help keep contracts stable.

## Method: Dataclass Serialization
Summary: Convert domain objects safely.
Related: Topic: Python Typing
Serialize enums as strings and timestamps as ISO values.

## Question: How should versions change?
Summary: Versions should only change on meaningful edits.
Related: Topic: Python Typing
Need a stable rule for version bumps.
""".strip()


class MountAndReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "mount.sqlite3"
        self.raw_root = Path(self.tempdir.name) / "raw"
        self.review_root = Path(self.tempdir.name) / "review"
        migrate_up(self.db_path)
        self.connection = connect(self.db_path)
        self.workspaces = WorkspaceRepository(self.connection)
        self.sources = SourceRepository(self.connection)
        self.workspace_service = WorkspaceService(self.workspaces, self.sources)
        self.import_service = SourceImportService(
            workspace_repository=self.workspaces,
            source_repository=self.sources,
            raw_store=RawSourceStore(self.raw_root),
        )
        self.compile_jobs = CompileJobRepository(self.connection)
        self.nodes = KnowledgeNodeRepository(self.connection)
        self.evidence = EvidenceFragmentRepository(self.connection)
        self.node_evidence = NodeEvidenceLinkRepository(self.connection)
        self.compiler = KnowledgeCompileService(
            source_repository=self.sources,
            compile_job_repository=self.compile_jobs,
            knowledge_node_repository=self.nodes,
            evidence_repository=self.evidence,
            node_evidence_link_repository=self.node_evidence,
            raw_store=RawSourceStore(self.raw_root),
        )
        self.signal_service = CapabilitySignalService(
            compiler=self.compiler,
            capability_signal_repository=CapabilitySignalRepository(self.connection),
            mistake_pattern_repository=MistakePatternRepository(self.connection),
        )
        self.focus_service = FocusCardService(FocusCardRepository(self.connection))
        self.postcard_service = PostcardService(
            compiler=self.compiler,
            capability_signals=CapabilitySignalRepository(self.connection),
            mistake_patterns=MistakePatternRepository(self.connection),
            postcard_repository=PostcardRepository(self.connection),
        )
        self.passport_service = PassportService(
            workspace_repository=self.workspaces,
            compiler=self.compiler,
            capability_signal_service=self.signal_service,
            capability_signal_repository=CapabilitySignalRepository(self.connection),
            mistake_pattern_repository=MistakePatternRepository(self.connection),
            focus_service=self.focus_service,
            postcard_service=self.postcard_service,
            postcard_repository=PostcardRepository(self.connection),
            passport_repository=PassportRepository(self.connection),
        )
        self.mount = MountService(
            visa_repository=VisaBundleRepository(self.connection),
            session_repository=MountSessionRepository(self.connection),
            audit_repository=AuditLogRepository(self.connection),
            passport_repository=PassportRepository(self.connection),
            passport_service=self.passport_service,
            postcard_repository=PostcardRepository(self.connection),
            postcard_service=self.postcard_service,
            knowledge_node_repository=self.nodes,
            focus_service=self.focus_service,
        )
        self.review = ReviewService(
            candidate_repository=ReviewCandidateRepository(self.connection),
            session_repository=MountSessionRepository(self.connection),
            audit_repository=AuditLogRepository(self.connection),
            knowledge_review_service=KnowledgeNodeReviewService(
                knowledge_node_repository=self.nodes,
                override_repository=KnowledgeNodeOverrideRepository(self.connection),
            ),
            postcard_repository=PostcardRepository(self.connection),
            focus_repository=FocusCardRepository(self.connection),
            mount_service=self.mount,
            storage_root=self.review_root,
        )

        workspace = self.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="Mount Workspace",
            now=NOW,
        )
        source = self.import_service.import_source(
            SourceImportRequest(
                workspace_id=workspace.id,
                source_type=SourceType.MARKDOWN,
                title="Mount Fixture",
                origin="mount.md",
                content=FIXTURE,
                imported_at=NOW + timedelta(minutes=1),
            )
        )
        self.focus_service.create_focus_card(
            workspace_id=workspace.id,
            title="Mount focus",
            goal="Validate passport-first reads",
            timeframe="today",
            priority=1,
            success_criteria=("Passport readable",),
            related_topics=("Python Typing",),
        )
        self.compiler.compile_source(source.id, requested_at=NOW + timedelta(minutes=2))
        self.passport = self.passport_service.generate_for_workspace(workspace.id, recorded_at=NOW + timedelta(minutes=3)).passport
        self.workspace_id = workspace.id
        self.topic = next(node for node in self.nodes.list_by_workspace(workspace.id) if node.title == "Python Typing")
        self.representative_postcard = self.postcard_service.representative_postcards(workspace.id)[0]

    def tearDown(self) -> None:
        self.connection.close()
        self.tempdir.cleanup()

    def test_passport_first_mount_and_permission_checks(self) -> None:
        passport_visa = self.mount.issue_default_passport_visa(
            self.workspace_id,
            expiry_at=NOW + timedelta(hours=1),
        )
        session = self.mount.start_session(passport_visa.id, client_type="gpt", started_at=NOW + timedelta(minutes=4))
        passport_payload = self.mount.read_passport_manifest(session.id)

        self.assertEqual(passport_payload.payload["workspace_id"], self.workspace_id)
        with self.assertRaises(AuthorizationError):
            self.mount.read_postcard(session.id, self.representative_postcard.id)
        with self.assertRaises(AuthorizationError):
            self.mount.assert_no_workspace_search()

    def test_topic_read_visa_allows_whitelisted_postcard_and_revocation_blocks_later_reads(self) -> None:
        visa = self.mount.issue_visa(
            workspace_id=self.workspace_id,
            included_postcards=(self.representative_postcard.id,),
            included_nodes=(self.topic.id,),
            permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.TOPIC_READ),
            expiry_at=NOW + timedelta(hours=1),
        )
        session = self.mount.start_session(visa.id, client_type="gpt", started_at=NOW + timedelta(minutes=4))
        postcard_payload = self.mount.read_postcard(session.id, self.representative_postcard.id)
        self.assertEqual(postcard_payload.payload["postcard"]["id"], self.representative_postcard.id)

        self.mount.revoke_visa(visa.id, actor="user")
        with self.assertRaises(AuthorizationError):
            self.mount.read_postcard(session.id, self.representative_postcard.id)

    def test_read_after_visa_expiry_is_rejected_even_for_existing_session(self) -> None:
        current = utc_now()
        visa = self.mount.issue_visa(
            workspace_id=self.workspace_id,
            included_postcards=(self.representative_postcard.id,),
            included_nodes=(self.topic.id,),
            permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.TOPIC_READ),
            expiry_at=current + timedelta(minutes=5),
        )
        session = self.mount.start_session(visa.id, client_type="gpt", started_at=current)
        self.mount.read_passport_manifest(session.id)
        expired = type(visa)(
            id=visa.id,
            scope=visa.scope,
            included_postcards=visa.included_postcards,
            included_nodes=visa.included_nodes,
            permission_levels=visa.permission_levels,
            expiry_at=current - timedelta(minutes=1),
            access_mode=visa.access_mode,
            writeback_policy=visa.writeback_policy,
            redaction_rules=visa.redaction_rules,
            status=visa.status,
            version=visa.version,
            workspace_id=visa.workspace_id,
        )
        self.mount.visas.update(expired)
        with self.assertRaises(AuthorizationError):
            self.mount.read_postcard(session.id, self.representative_postcard.id)

    def test_foreign_workspace_postcard_cannot_be_included_in_visa(self) -> None:
        other_workspace = self.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PROJECT,
            title="Other",
            now=NOW + timedelta(minutes=10),
        )
        other_source = self.import_service.import_source(
            SourceImportRequest(
                workspace_id=other_workspace.id,
                source_type=SourceType.MARKDOWN,
                title="Other Fixture",
                origin="other.md",
                content=FIXTURE,
                imported_at=NOW + timedelta(minutes=11),
            )
        )
        self.compiler.compile_source(other_source.id, requested_at=NOW + timedelta(minutes=12))
        self.passport_service.generate_for_workspace(other_workspace.id, recorded_at=NOW + timedelta(minutes=13))
        foreign_postcard = self.postcard_service.representative_postcards(other_workspace.id)[0]

        with self.assertRaises(AuthorizationError):
            self.mount.issue_visa(
                workspace_id=self.workspace_id,
                included_postcards=(foreign_postcard.id,),
                included_nodes=(),
                permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.TOPIC_READ),
                expiry_at=NOW + timedelta(hours=1),
            )

    def test_review_candidate_diff_and_acceptance_updates_node(self) -> None:
        visa = self.mount.issue_visa(
            workspace_id=self.workspace_id,
            included_postcards=(self.representative_postcard.id,),
            included_nodes=(self.topic.id,),
            permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.TOPIC_READ, PermissionLevel.WRITEBACK_CANDIDATE),
            expiry_at=NOW + timedelta(hours=1),
        )
        session = self.mount.start_session(visa.id, client_type="gpt", started_at=NOW + timedelta(minutes=4))

        candidate = self.review.create_candidate(
            session_id=session.id,
            candidate_type=CandidateType.SUMMARY,
            target_object=f"knowledge_node:{self.topic.id}",
            content={"summary": "Edited summary from review candidate."},
        )
        diff = self.review.read_diff(candidate.id)
        accepted = self.review.accept_candidate(candidate.id, actor="user")
        effective = self.review.knowledge.effective_view(self.topic.id)
        session_after = self.review.sessions.get(session.id)

        self.assertIn("Edited summary from review candidate.", diff.after["summary"])
        self.assertEqual(accepted.status.value, "accepted")
        self.assertEqual(effective.effective_node.summary, "Edited summary from review candidate.")
        self.assertIsNotNone(session_after)
        assert session_after is not None
        self.assertEqual(session_after.writeback_count, 1)

    def test_reject_candidate_preserves_canonical_state(self) -> None:
        visa = self.mount.issue_visa(
            workspace_id=self.workspace_id,
            included_postcards=(self.representative_postcard.id,),
            included_nodes=(self.topic.id,),
            permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.TOPIC_READ, PermissionLevel.WRITEBACK_CANDIDATE),
            expiry_at=NOW + timedelta(hours=1),
        )
        session = self.mount.start_session(visa.id, client_type="gpt", started_at=NOW + timedelta(minutes=4))
        candidate = self.review.create_candidate(
            session_id=session.id,
            candidate_type=CandidateType.SUMMARY,
            target_object=f"knowledge_node:{self.topic.id}",
            content={"summary": "Rejected summary."},
        )

        rejected = self.review.reject_candidate(candidate.id, actor="user")
        effective = self.review.knowledge.effective_view(self.topic.id)

        self.assertEqual(rejected.status.value, "rejected")
        self.assertNotEqual(effective.effective_node.summary, "Rejected summary.")

    def test_writeback_candidate_requires_permission(self) -> None:
        visa = self.mount.issue_visa(
            workspace_id=self.workspace_id,
            included_postcards=(self.representative_postcard.id,),
            included_nodes=(self.topic.id,),
            permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.TOPIC_READ),
            expiry_at=NOW + timedelta(hours=1),
        )
        session = self.mount.start_session(visa.id, client_type="gpt", started_at=NOW + timedelta(minutes=4))
        with self.assertRaises(AuthorizationError):
            self.review.create_candidate(
                session_id=session.id,
                candidate_type=CandidateType.SUMMARY,
                target_object=f"knowledge_node:{self.topic.id}",
                content={"summary": "Should be blocked"},
            )
