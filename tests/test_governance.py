from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.api.server import build_context
from app.domain import CandidateType, PermissionLevel, PrivacyLevel, SourceType, WorkspaceType
from app.ingest.service import SourceImportRequest


NOW = datetime(2026, 4, 7, 11, 0, 0)
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


class GovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.context = build_context(
            db_path=self.root / "source.sqlite3",
            raw_root=self.root / "raw",
            export_root=self.root / "exports",
            review_root=self.root / "review",
        )
        workspace = self.context.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="Governance",
            now=NOW,
        )
        source = self.context.source_import_service.import_source(
            SourceImportRequest(
                workspace_id=workspace.id,
                source_type=SourceType.MARKDOWN,
                title="Governance Fixture",
                origin="governance.md",
                content=FIXTURE,
                imported_at=NOW + timedelta(minutes=1),
            )
        )
        self.context.focus_service.create_focus_card(
            workspace_id=workspace.id,
            title="Governance focus",
            goal="Validate export and restore",
            timeframe="today",
            priority=1,
            success_criteria=("export works", "restore works"),
            related_topics=("Python Typing",),
        )
        self.context.compile_service.compile_source(source.id, requested_at=NOW + timedelta(minutes=2))
        self.context.passport_service.generate_for_workspace(workspace.id, recorded_at=NOW + timedelta(minutes=3))
        visa = self.context.mount_service.issue_visa(
            workspace_id=workspace.id,
            included_postcards=tuple(card.id for card in self.context.postcard_service.representative_postcards(workspace.id)),
            included_nodes=tuple(node.id for node in self.context.compile_service.nodes.list_by_workspace(workspace.id)),
            permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.TOPIC_READ, PermissionLevel.WRITEBACK_CANDIDATE),
            expiry_at=NOW + timedelta(hours=1),
        )
        session = self.context.mount_service.start_session(visa.id, client_type="gpt", started_at=NOW + timedelta(minutes=4))
        self.context.review_service.create_candidate(
            session_id=session.id,
            candidate_type=CandidateType.SUMMARY,
            target_object=f"knowledge_node:{self.context.compile_service.nodes.list_by_workspace(workspace.id)[0].id}",
            content={"summary": "Candidate for export"},
        )
        first_card = self.context.postcard_service.representative_postcards(workspace.id)[0]
        self.context.postcard_service.set_visibility(first_card.id, PrivacyLevel.RESTRICTED)
        self.workspace_id = workspace.id

    def tearDown(self) -> None:
        self.context.connection.close()
        self.tempdir.cleanup()

    def test_export_filters_hidden_cards_and_restore_rehydrates_workspace(self) -> None:
        export_path = self.context.export_restore_service.export_workspace(self.workspace_id, include_hidden=False)
        self.assertTrue(export_path.exists())

        restored_context = build_context(
            db_path=self.root / "restore.sqlite3",
            raw_root=self.root / "restored_raw",
            export_root=self.root / "restored_exports",
            review_root=self.root / "restored_review",
        )
        try:
            payload = restored_context.export_restore_service.restore_workspace(export_path)
            workspace = restored_context.workspace_service.get_workspace(self.workspace_id)
            passport = restored_context.passport_service.passports.get_by_workspace(self.workspace_id)
            cards = restored_context.postcard_service.postcards.list_by_workspace(self.workspace_id)
            sources = restored_context.inbox_service.sources.list_by_workspace(self.workspace_id)

            self.assertEqual(payload["workspace"]["id"], self.workspace_id)
            self.assertEqual(workspace.id, self.workspace_id)
            self.assertIsNotNone(passport)
            self.assertTrue(any(Path(source.raw_blob_ref).exists() for source in sources))
            self.assertTrue(all(card.visibility.value != "restricted" for card in cards))
        finally:
            restored_context.connection.close()
