from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.compile.service import KnowledgeCompileService
from app.domain import PassportReadiness, PrivacyLevel, SourceType, WorkspaceType
from app.ingest.service import RawSourceStore, SourceImportRequest, SourceImportService
from app.passport.service import PassportService, PostcardService
from app.passport.signals import CapabilitySignalService, FocusCardService
from app.storage.capability_signals import CapabilitySignalRepository
from app.storage.compile_jobs import CompileJobRepository
from app.storage.evidence import EvidenceFragmentRepository
from app.storage.focus_cards import FocusCardRepository
from app.storage.knowledge_nodes import KnowledgeNodeRepository
from app.storage.migrate import migrate_up
from app.storage.mistake_patterns import MistakePatternRepository
from app.storage.node_evidence_links import NodeEvidenceLinkRepository
from app.storage.passports import PassportRepository
from app.storage.postcards import PostcardRepository
from app.storage.sources import SourceRepository
from app.storage.sqlite import connect
from app.storage.workspaces import WorkspaceRepository
from app.api.workspaces import WorkspaceService


NOW = datetime(2026, 4, 6, 23, 0, 0)
FIXTURE = """
## Topic: Python Typing
Summary: Types improve correctness.
Related: Method: Dataclass Serialization, Question: How should versions change?
Typed models help keep contracts stable.

## Project: AI Passport MVP
Summary: Build the passport compiler.
Related: Topic: Python Typing
The project focuses on local-first knowledge compilation.

## Method: Dataclass Serialization
Summary: Convert domain objects safely.
Related: Topic: Python Typing
Serialize enums as strings and timestamps as ISO values.

## Question: How should versions change?
Summary: Versions should only change on meaningful edits.
Related: Topic: Python Typing
Need a stable rule for version bumps.
""".strip()


class PassportGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "passport.sqlite3"
        self.raw_root = Path(self.tempdir.name) / "raw"
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
        self.compiler = KnowledgeCompileService(
            source_repository=self.sources,
            compile_job_repository=CompileJobRepository(self.connection),
            knowledge_node_repository=KnowledgeNodeRepository(self.connection),
            evidence_repository=EvidenceFragmentRepository(self.connection),
            node_evidence_link_repository=NodeEvidenceLinkRepository(self.connection),
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
        workspace = self.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="Passport Workspace",
            now=NOW,
        )
        source = self.import_service.import_source(
            SourceImportRequest(
                workspace_id=workspace.id,
                source_type=SourceType.MARKDOWN,
                title="Passport Fixture",
                origin="passport.md",
                content=FIXTURE,
                imported_at=NOW + timedelta(minutes=1),
            )
        )
        self.compiler.compile_source(source.id, requested_at=NOW + timedelta(minutes=2))
        self.focus_service.create_focus_card(
            workspace_id=workspace.id,
            title="Ship Passport",
            goal="Generate the first passport",
            timeframe="this week",
            priority=1,
            success_criteria=("Passport generated",),
            related_topics=("Python Typing",),
        )
        self.workspace_id = workspace.id

    def tearDown(self) -> None:
        self.connection.close()
        self.tempdir.cleanup()

    def test_postcard_generation_produces_four_classes_and_representatives(self) -> None:
        self.signal_service.generate_for_workspace(self.workspace_id)
        cards = self.postcard_service.generate_for_workspace(self.workspace_id, recorded_at=NOW + timedelta(minutes=3))
        classes = {card.card_type.value for card in cards}
        reps = self.postcard_service.representative_postcards(self.workspace_id)

        self.assertEqual(classes, {"knowledge", "capability", "mistake", "exploration"})
        self.assertGreaterEqual(len(reps), 3)
        self.assertLessEqual(len(reps), 5)

    def test_postcard_visibility_controls_and_versioning(self) -> None:
        self.signal_service.generate_for_workspace(self.workspace_id)
        cards = self.postcard_service.generate_for_workspace(self.workspace_id, recorded_at=NOW + timedelta(minutes=3))
        first = next(card for card in cards if card.card_type.value == "knowledge" and card.title == "Python Typing")
        hidden = self.postcard_service.set_visibility(first.id, PrivacyLevel.RESTRICTED)
        self.assertEqual(hidden.visibility, PrivacyLevel.RESTRICTED)

        raw_file = next(Path(self.raw_root).rglob("*.md"))
        raw_file.write_text(FIXTURE.replace("Types improve correctness.", "Types improve correctness and confidence."))
        source = self.sources.list_by_workspace(self.workspace_id)[0]
        self.compiler.compile_source(source.id, requested_at=NOW + timedelta(minutes=4))
        updated_cards = self.postcard_service.generate_for_workspace(self.workspace_id, recorded_at=NOW + timedelta(minutes=5))
        updated = next(card for card in updated_cards if card.id == first.id)
        self.assertGreaterEqual(updated.version, 2)

    def test_passport_machine_and_human_views_stay_aligned_and_ready(self) -> None:
        view = self.passport_service.generate_for_workspace(self.workspace_id, recorded_at=NOW + timedelta(minutes=3))
        machine = self.passport_service.read_machine_manifest(view.passport.id)
        human = self.passport_service.read_human_view(view.passport.id)
        readiness = self.passport_service.compute_readiness(self.workspace_id)

        self.assertEqual(machine["owner_summary"], view.passport.owner_summary)
        self.assertIn(view.passport.owner_summary, human)
        self.assertEqual(readiness, PassportReadiness.READY)

    def test_owner_summary_rewrite_updates_passport_immediately(self) -> None:
        view = self.passport_service.generate_for_workspace(self.workspace_id, recorded_at=NOW + timedelta(minutes=3))
        rewritten = self.passport_service.rewrite_owner_summary(view.passport.id, "Custom summary")
        human = self.passport_service.read_human_view(view.passport.id)

        self.assertEqual(rewritten.owner_summary, "Custom summary")
        self.assertIn("Custom summary", human)
