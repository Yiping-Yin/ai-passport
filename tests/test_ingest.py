from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.domain import PrivacyLevel, SourceType, WorkspaceType
from app.ingest.service import RawSourceStore, SourceImportRequest, SourceImportService
from app.storage.migrate import migrate_up
from app.storage.sources import SourceRepository
from app.storage.sqlite import connect
from app.storage.workspaces import WorkspaceRepository
from app.api.workspaces import WorkspaceService


NOW = datetime(2026, 4, 6, 16, 0, 0)


class SourceIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "ingest.sqlite3"
        self.raw_root = Path(self.tempdir.name) / "raw"
        migrate_up(self.db_path)
        self.connection = connect(self.db_path)
        self.workspace_repository = WorkspaceRepository(self.connection)
        self.source_repository = SourceRepository(self.connection)
        self.workspace_service = WorkspaceService(self.workspace_repository, self.source_repository)
        self.service = SourceImportService(
            workspace_repository=self.workspace_repository,
            source_repository=self.source_repository,
            raw_store=RawSourceStore(self.raw_root),
        )
        self.workspace = self.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="Personal",
            now=NOW,
            privacy_default=PrivacyLevel.RESTRICTED,
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.tempdir.cleanup()

    def test_import_supports_all_mvp_source_types(self) -> None:
        imported_ids = []
        for index, source_type in enumerate(
            (
                SourceType.WEB_PAGE,
                SourceType.MARKDOWN,
                SourceType.PDF,
                SourceType.PLAIN_TEXT,
                SourceType.PROJECT_DOCUMENT,
            )
        ):
            source = self.service.import_source(
                SourceImportRequest(
                    workspace_id=self.workspace.id,
                    source_type=source_type,
                    title=f"Source {index}",
                    origin=f"origin-{index}",
                    content=f"content-{index}",
                    imported_at=NOW + timedelta(minutes=index),
                )
            )
            imported_ids.append(source.id)
            self.assertEqual(source.workspace_id, self.workspace.id)
            self.assertTrue(Path(source.raw_blob_ref).exists())

        visible = self.source_repository.list_by_workspace(self.workspace.id)
        self.assertEqual({source.id for source in visible}, set(imported_ids))

    def test_privacy_defaults_and_validation(self) -> None:
        defaulted = self.service.import_source(
            SourceImportRequest(
                workspace_id=self.workspace.id,
                source_type=SourceType.MARKDOWN,
                title="Default Privacy",
                origin="default.md",
                content="hello",
                imported_at=NOW,
            )
        )
        explicit = self.service.import_source(
            SourceImportRequest(
                workspace_id=self.workspace.id,
                source_type=SourceType.PLAIN_TEXT,
                title="Shared",
                origin="shared.txt",
                content="world",
                imported_at=NOW + timedelta(minutes=1),
                privacy_level=PrivacyLevel.SHARED,
            )
        )

        with self.assertRaises(ValueError):
            self.service.import_source(
                SourceImportRequest(
                    workspace_id=self.workspace.id,
                    source_type=SourceType.PLAIN_TEXT,
                    title="Bad Privacy",
                    origin="bad.txt",
                    content="oops",
                    imported_at=NOW + timedelta(minutes=2),
                    privacy_level="public",
                )
            )

        self.assertEqual(defaulted.privacy_level, PrivacyLevel.RESTRICTED)
        self.assertEqual(explicit.privacy_level, PrivacyLevel.SHARED)

    def test_recompile_placeholder_does_not_mutate_raw_source(self) -> None:
        source = self.service.import_source(
            SourceImportRequest(
                workspace_id=self.workspace.id,
                source_type=SourceType.MARKDOWN,
                title="Immutable",
                origin="immutable.md",
                content="original content",
                imported_at=NOW,
            )
        )
        raw_path = Path(source.raw_blob_ref)
        before = raw_path.read_text()

        recompilation_view = self.service.recompile_placeholder(source.id)
        after = raw_path.read_text()

        self.assertEqual(recompilation_view.raw_blob_ref, source.raw_blob_ref)
        self.assertEqual(before, after)

    def test_archived_workspace_rejects_new_imports(self) -> None:
        self.workspace_service.archive_workspace(self.workspace.id, archived_at=NOW + timedelta(hours=1))
        with self.assertRaises(ValueError):
            self.service.import_source(
                SourceImportRequest(
                    workspace_id=self.workspace.id,
                    source_type=SourceType.MARKDOWN,
                    title="Nope",
                    origin="nope.md",
                    content="blocked",
                    imported_at=NOW + timedelta(minutes=10),
                )
            )


if __name__ == "__main__":
    unittest.main()
