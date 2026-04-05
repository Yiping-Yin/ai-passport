from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.compile.review import KnowledgeNodeReviewService
from app.compile.service import KnowledgeCompileService
from app.domain import FieldProvenance, OverrideMode, SourceType, WorkspaceType
from app.ingest.service import RawSourceStore, SourceImportRequest, SourceImportService
from app.storage.compile_jobs import CompileJobRepository
from app.storage.evidence import EvidenceFragmentRepository
from app.storage.knowledge_nodes import KnowledgeNodeRepository
from app.storage.migrate import migrate_up
from app.storage.node_evidence_links import NodeEvidenceLinkRepository
from app.storage.node_overrides import KnowledgeNodeOverrideRepository
from app.storage.sources import SourceRepository
from app.storage.sqlite import connect
from app.storage.workspaces import WorkspaceRepository
from app.api.workspaces import WorkspaceService


NOW = datetime(2026, 4, 6, 21, 0, 0)
FIXTURE_CONTENT = """
## Topic: Python Typing
Summary: Types improve correctness.
Related: Method: Dataclass Serialization
Typed models help keep contracts stable.

## Method: Dataclass Serialization
Summary: Convert domain objects to transport-safe shapes.
Related: Topic: Python Typing
Serialize enums as strings and datetimes as ISO timestamps.
""".strip()


class CompileReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "review.sqlite3"
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
        self.compiler = KnowledgeCompileService(
            source_repository=self.source_repository,
            compile_job_repository=CompileJobRepository(self.connection),
            knowledge_node_repository=KnowledgeNodeRepository(self.connection),
            evidence_repository=EvidenceFragmentRepository(self.connection),
            node_evidence_link_repository=NodeEvidenceLinkRepository(self.connection),
            raw_store=RawSourceStore(self.raw_root),
        )
        self.review = KnowledgeNodeReviewService(
            knowledge_node_repository=KnowledgeNodeRepository(self.connection),
            override_repository=KnowledgeNodeOverrideRepository(self.connection),
        )
        workspace = self.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="Review",
            now=NOW,
        )
        source = self.import_service.import_source(
            SourceImportRequest(
                workspace_id=workspace.id,
                source_type=SourceType.MARKDOWN,
                title="Review Fixture",
                origin="review.md",
                content=FIXTURE_CONTENT,
                imported_at=NOW + timedelta(minutes=1),
            )
        )
        result = self.compiler.compile_source(source.id, requested_at=NOW + timedelta(minutes=2))
        self.topic = next(node for node in result.nodes if node.title == "Python Typing")
        self.method = next(node for node in result.nodes if node.title == "Dataclass Serialization")
        self.raw_path = Path(source.raw_blob_ref)

    def tearDown(self) -> None:
        self.connection.close()
        self.tempdir.cleanup()

    def test_manual_field_override_persists_and_marks_provenance(self) -> None:
        self.review.set_field_override(
            node_id=self.topic.id,
            field_name="title",
            value="Python Typing (Edited)",
            editor="user",
            edited_at=NOW + timedelta(minutes=3),
        )
        view = self.review.effective_view(self.topic.id)
        self.assertEqual(view.effective_node.title, "Python Typing (Edited)")
        self.assertEqual(view.field_provenance["title"], FieldProvenance.HUMAN_EDITED)

    def test_relation_merge_marks_mixed_provenance(self) -> None:
        self.review.set_field_override(
            node_id=self.topic.id,
            field_name="related_node_ids",
            value=["node-extra-manual"],
            editor="user",
            edited_at=NOW + timedelta(minutes=3),
            override_mode=OverrideMode.MERGE,
        )
        view = self.review.effective_view(self.topic.id)
        self.assertIn(self.method.id, view.effective_node.related_node_ids)
        self.assertIn("node-extra-manual", view.effective_node.related_node_ids)
        self.assertEqual(view.field_provenance["related_node_ids"], FieldProvenance.MIXED)

    def test_compile_diff_shows_revision_changes(self) -> None:
        self.raw_path.write_text(FIXTURE_CONTENT.replace("Types improve correctness.", "Types improve correctness and maintainability."))
        self.compiler.compile_source(self.topic.source_ids[0], requested_at=NOW + timedelta(minutes=4))

        diff = self.review.diff_latest(self.topic.id)
        self.assertIsNotNone(diff)
        assert diff is not None
        changed_fields = {field.field_name for field in diff.fields}
        self.assertIn("summary", changed_fields)
        self.assertEqual((diff.from_version, diff.to_version), (1, 2))


if __name__ == "__main__":
    unittest.main()
