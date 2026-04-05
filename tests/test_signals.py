from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.compile.service import KnowledgeCompileService
from app.domain import FocusStatus, InsightDisposition, NodeType, SourceType, WorkspaceType
from app.ingest.service import RawSourceStore, SourceImportRequest, SourceImportService
from app.passport.signals import CapabilitySignalService, FocusCardService
from app.storage.capability_signals import CapabilitySignalRepository
from app.storage.compile_jobs import CompileJobRepository
from app.storage.evidence import EvidenceFragmentRepository
from app.storage.focus_cards import FocusCardRepository
from app.storage.knowledge_nodes import KnowledgeNodeRepository
from app.storage.migrate import migrate_up
from app.storage.mistake_patterns import MistakePatternRepository
from app.storage.node_evidence_links import NodeEvidenceLinkRepository
from app.storage.sources import SourceRepository
from app.storage.sqlite import connect
from app.storage.workspaces import WorkspaceRepository
from app.api.workspaces import WorkspaceService


NOW = datetime(2026, 4, 6, 22, 0, 0)
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


class SignalAndFocusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "signals.sqlite3"
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
        workspace = self.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="Signals",
            now=NOW,
        )
        source = self.import_service.import_source(
            SourceImportRequest(
                workspace_id=workspace.id,
                source_type=SourceType.MARKDOWN,
                title="Signals Fixture",
                origin="signals.md",
                content=FIXTURE,
                imported_at=NOW + timedelta(minutes=1),
            )
        )
        self.compiler.compile_source(source.id, requested_at=NOW + timedelta(minutes=2))
        self.workspace_id = workspace.id

    def tearDown(self) -> None:
        self.connection.close()
        self.tempdir.cleanup()

    def test_signal_generation_produces_descriptive_non_numeric_signals(self) -> None:
        bundle = self.signal_service.generate_for_workspace(self.workspace_id)
        topics = {signal.topic for signal in bundle.capability_signals}
        self.assertIn("Python Typing", topics)
        signal = next(item for item in bundle.capability_signals if item.topic == "Python Typing")
        self.assertGreater(len(signal.observed_practice), 0)
        self.assertNotIn("score", signal.observed_practice.lower())
        self.assertGreaterEqual(signal.version, 1)

    def test_mistake_pattern_generation_and_controls(self) -> None:
        bundle = self.signal_service.generate_for_workspace(self.workspace_id)
        pattern = bundle.mistake_patterns[0]
        self.assertEqual(pattern.version, 1)

        confirmed = self.signal_service.confirm_pattern(pattern.id)
        dismissed = self.signal_service.dismiss_pattern(pattern.id)

        self.assertEqual(confirmed.disposition, InsightDisposition.CONFIRMED)
        self.assertEqual(dismissed.disposition, InsightDisposition.DISMISSED)

    def test_focus_service_keeps_one_active_card(self) -> None:
        first = self.focus_service.create_focus_card(
            workspace_id=self.workspace_id,
            title="First focus",
            goal="Ship signals",
            timeframe="this week",
            priority=1,
            success_criteria=("Signals generated",),
            related_topics=("Python Typing",),
            status=FocusStatus.ACTIVE,
        )
        second = self.focus_service.create_focus_card(
            workspace_id=self.workspace_id,
            title="Second focus",
            goal="Ship postcards",
            timeframe="next week",
            priority=2,
            success_criteria=("Postcards generated",),
            related_topics=("Python Typing",),
            status=FocusStatus.ACTIVE,
        )
        first_after = next(card for card in self.focus_service.list_focus_cards(self.workspace_id) if card.id == first.id)
        active = self.focus_service.active_focus(self.workspace_id)

        self.assertEqual(first_after.status, FocusStatus.ARCHIVED)
        self.assertIsNotNone(active)
        assert active is not None
        self.assertEqual(active.id, second.id)
