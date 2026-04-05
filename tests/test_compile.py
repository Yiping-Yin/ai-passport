from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.compile.service import KnowledgeCompileService
from app.domain import CompileJobStatus, NodeType, SourceType, WorkspaceType
from app.ingest.service import RawSourceStore, SourceImportRequest, SourceImportService
from app.storage.compile_jobs import CompileJobRepository
from app.storage.evidence import EvidenceFragmentRepository
from app.storage.knowledge_nodes import KnowledgeNodeRepository
from app.storage.migrate import migrate_up
from app.storage.node_evidence_links import NodeEvidenceLinkRepository
from app.storage.sources import SourceRepository
from app.storage.sqlite import connect
from app.storage.workspaces import WorkspaceRepository
from app.api.workspaces import WorkspaceService


NOW = datetime(2026, 4, 6, 20, 0, 0)
FIXTURE_CONTENT = """
## Topic: Python Typing
Summary: Types improve correctness.
Related: Method: Dataclass Serialization, Question: How should versions change?
Typed models help keep contracts stable.

## Project: AI Passport MVP
Summary: Build the passport compiler.
Related: Topic: Python Typing
The project focuses on local-first knowledge compilation.

## Method: Dataclass Serialization
Summary: Convert domain objects to transport-safe shapes.
Related: Topic: Python Typing
Serialize enums as strings and datetimes as ISO timestamps.

## Question: How should versions change?
Summary: Versions should increment only on meaningful node changes.
Related: Topic: Python Typing
Use snapshots for traceable revisions.
""".strip()


class CompileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "compile.sqlite3"
        self.raw_root = Path(self.tempdir.name) / "raw"
        migrate_up(self.db_path)
        self.connection = connect(self.db_path)
        self.workspace_repository = WorkspaceRepository(self.connection)
        self.source_repository = SourceRepository(self.connection)
        self.workspace_service = WorkspaceService(self.workspace_repository, self.source_repository)
        self.import_service = SourceImportService(
            workspace_repository=self.workspace_repository,
            source_repository=self.source_repository,
            raw_store=RawSourceStore(self.raw_root),
        )
        self.compile_jobs = CompileJobRepository(self.connection)
        self.nodes = KnowledgeNodeRepository(self.connection)
        self.evidence = EvidenceFragmentRepository(self.connection)
        self.node_evidence_links = NodeEvidenceLinkRepository(self.connection)
        self.compiler = KnowledgeCompileService(
            source_repository=self.source_repository,
            compile_job_repository=self.compile_jobs,
            knowledge_node_repository=self.nodes,
            evidence_repository=self.evidence,
            node_evidence_link_repository=self.node_evidence_links,
            raw_store=RawSourceStore(self.raw_root),
        )
        self.workspace = self.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="Compiler",
            now=NOW,
        )
        self.source = self.import_service.import_source(
            SourceImportRequest(
                workspace_id=self.workspace.id,
                source_type=SourceType.MARKDOWN,
                title="Compiler Fixture",
                origin="fixture.md",
                content=FIXTURE_CONTENT,
                imported_at=NOW + timedelta(minutes=1),
            )
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.tempdir.cleanup()

    def test_compile_emits_all_foundational_node_types(self) -> None:
        result = self.compiler.compile_source(self.source.id, requested_at=NOW + timedelta(minutes=2))
        node_types = {node.node_type for node in result.nodes}
        self.assertEqual(
            node_types,
            {NodeType.TOPIC, NodeType.PROJECT, NodeType.METHOD, NodeType.QUESTION},
        )
        self.assertEqual(result.job.status, CompileJobStatus.SUCCEEDED)

    def test_related_nodes_are_discoverable_from_both_sides(self) -> None:
        self.compiler.compile_source(self.source.id, requested_at=NOW + timedelta(minutes=2))
        nodes = {node.title: node for node in self.nodes.list_by_workspace(self.workspace.id)}
        topic = nodes["Python Typing"]
        method = nodes["Dataclass Serialization"]
        question = nodes["How should versions change?"]

        self.assertIn(method.id, topic.related_node_ids)
        self.assertIn(topic.id, method.related_node_ids)
        self.assertIn(question.id, topic.related_node_ids)
        self.assertIn(topic.id, question.related_node_ids)

    def test_changed_input_creates_new_revision_version(self) -> None:
        initial = self.compiler.compile_source(self.source.id, requested_at=NOW + timedelta(minutes=2))
        topic = next(node for node in initial.nodes if node.node_type is NodeType.TOPIC)
        raw_path = Path(self.source.raw_blob_ref)
        raw_path.write_text(FIXTURE_CONTENT.replace("Types improve correctness.", "Types improve correctness and maintainability."))

        updated = self.compiler.compile_source(self.source.id, requested_at=NOW + timedelta(minutes=3))
        updated_topic = next(node for node in updated.nodes if node.id == topic.id)
        revisions = self.nodes.list_revisions(topic.id)

        self.assertEqual(updated_topic.version, 2)
        self.assertEqual([revision.version for revision in revisions], [1, 2])

    def test_node_view_includes_evidence_and_source_jump(self) -> None:
        result = self.compiler.compile_source(self.source.id, requested_at=NOW + timedelta(minutes=2))
        topic = next(node for node in result.nodes if node.node_type is NodeType.TOPIC)

        view = self.compiler.read_node_with_evidence(topic.id)
        jump = self.compiler.source_jump_target(topic.id)

        self.assertEqual(view.node.id, topic.id)
        self.assertEqual(len(view.evidence_fragments), 1)
        self.assertEqual(view.evidence_fragments[0].source_id, self.source.id)
        self.assertTrue(jump.raw_blob_ref.endswith(".md"))
        self.assertTrue(jump.locator.startswith("line:"))


if __name__ == "__main__":
    unittest.main()
