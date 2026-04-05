from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from app.domain import CompileJobStatus, SourceType, WorkspaceType
from app.ingest.inbox import InboxService
from app.ingest.service import RawSourceStore, SourceImportRequest, SourceImportService
from app.storage.compile_jobs import CompileJobRepository
from app.storage.evidence import EvidenceFragmentRepository
from app.storage.migrate import migrate_up
from app.storage.sources import SourceRepository
from app.storage.sqlite import connect
from app.storage.workspaces import WorkspaceRepository
from app.api.workspaces import WorkspaceService


NOW = datetime(2026, 4, 6, 18, 0, 0)


class InboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "inbox.sqlite3"
        self.raw_root = Path(self.tempdir.name) / "raw"
        migrate_up(self.db_path)
        self.connection = connect(self.db_path)
        self.workspace_repository = WorkspaceRepository(self.connection)
        self.source_repository = SourceRepository(self.connection)
        self.compile_repository = CompileJobRepository(self.connection)
        self.evidence_repository = EvidenceFragmentRepository(self.connection)
        self.workspace_service = WorkspaceService(self.workspace_repository, self.source_repository)
        self.import_service = SourceImportService(
            workspace_repository=self.workspace_repository,
            source_repository=self.source_repository,
            raw_store=RawSourceStore(self.raw_root),
        )
        self.inbox = InboxService(
            workspace_repository=self.workspace_repository,
            source_repository=self.source_repository,
            compile_job_repository=self.compile_repository,
            evidence_repository=self.evidence_repository,
            raw_store=RawSourceStore(self.raw_root),
        )
        self.workspace = self.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="Inbox",
            now=NOW,
        )
        self.source = self.import_service.import_source(
            SourceImportRequest(
                workspace_id=self.workspace.id,
                source_type=SourceType.MARKDOWN,
                title="Inbox Source",
                origin="inbox.md",
                content="raw inbox content",
                imported_at=NOW + timedelta(minutes=1),
            )
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.tempdir.cleanup()

    def test_inbox_item_reflects_compile_status(self) -> None:
        item = self.inbox.list_items(workspace_id=self.workspace.id)[0]
        self.assertEqual(item.compile_status, CompileJobStatus.NOT_STARTED)

        job = self.inbox.queue_compile(self.source.id, requested_at=NOW + timedelta(minutes=2))
        running = self.inbox.mark_running(job.id, now=NOW + timedelta(minutes=3))
        failed = self.inbox.mark_failed(running.id, now=NOW + timedelta(minutes=4), last_error="compiler timeout")

        refreshed = self.inbox.list_items(workspace_id=self.workspace.id)[0]
        self.assertEqual(refreshed.compile_status, CompileJobStatus.FAILED)
        self.assertEqual(refreshed.last_error, "compiler timeout")
        self.assertEqual(failed.attempt_number, 1)

    def test_recompile_creates_new_job_without_duplicating_source(self) -> None:
        first = self.inbox.queue_compile(self.source.id, requested_at=NOW + timedelta(minutes=2))
        self.inbox.mark_failed(first.id, now=NOW + timedelta(minutes=3), last_error="failed")
        second = self.inbox.recompile(self.source.id, requested_at=NOW + timedelta(minutes=4))

        rows = self.connection.execute("SELECT COUNT(*) FROM sources").fetchone()
        self.assertEqual(rows[0], 1)
        self.assertEqual(second.attempt_number, 2)
        self.assertEqual(second.status, CompileJobStatus.QUEUED)

    def test_preview_shows_raw_source_and_available_evidence(self) -> None:
        self.connection.execute(
            """
            INSERT INTO evidence_fragments (id, source_id, locator, excerpt, confidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("ev-preview", self.source.id, "line:1", "preview excerpt", 0.9),
        )
        self.connection.commit()
        self.inbox.queue_compile(self.source.id, requested_at=NOW + timedelta(minutes=2))

        preview = self.inbox.preview(self.source.id)
        self.assertEqual(preview.raw_content, "raw inbox content")
        self.assertEqual(preview.evidence_preview, ("preview excerpt",))
        self.assertEqual(preview.compile_status, CompileJobStatus.QUEUED)

    def test_compile_jobs_migration_exists(self) -> None:
        tables = {
            row[0]
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        self.assertIn("compile_jobs", tables)


if __name__ == "__main__":
    unittest.main()
