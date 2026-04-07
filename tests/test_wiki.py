from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import os
import time
import unittest

from app.domain import WorkspaceType
from app.storage.migrate import migrate_up
from app.storage.sqlite import connect
from app.storage.workspaces import WorkspaceRepository
from app.api.workspaces import WorkspaceService
from app.wiki.service import AIGenerationStatus, WikiService
from app.wiki.watch import WikiWatchService
from app.utils.time import utc_now


FIXTURE_MD = """
## Topic: Python Typing
Summary: Types improve correctness.
Related: Method: Dataclass Serialization
Typed models help keep contracts stable.

## Method: Dataclass Serialization
Summary: Convert domain objects safely.
Related: Topic: Python Typing
Serialize enums as strings and timestamps as ISO values.
""".strip()


class WikiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.raw_root = self.root / "raw"
        self.source_root = self.root / "vault"
        self.source_root.mkdir()
        migrate_up(self.root / "wiki.sqlite3")
        self.connection = connect(self.root / "wiki.sqlite3")
        self.workspaces = WorkspaceRepository(self.connection)
        self.workspace_service = WorkspaceService(self.workspaces, source_repository=type("DummySources", (), {"count_by_workspace": lambda *_: 0})())  # type: ignore[arg-type]
        self.workspace = self.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="Wiki",
            now=utc_now(),
        )
        self.service = WikiService(
            workspace_repository=self.workspaces,
            raw_root=self.raw_root,
        )
        self.service.update_vault(
            self.workspace.id,
            source_root=str(self.source_root),
            ai_enabled=False,
            watch_interval_seconds=0.1,
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.tempdir.cleanup()

    def test_scan_build_generate_markdown_and_indexes(self) -> None:
        (self.source_root / "typing.md").write_text(FIXTURE_MD)
        (self.source_root / "notes.txt").write_text("A plain text note.")
        result = self.service.scan_and_build(self.workspace.id)
        wiki_root = Path(self.service.get_or_create_vault(self.workspace.id).wiki_root)

        self.assertEqual(result.scanned_file_count, 2)
        self.assertTrue((wiki_root / "_index.md").exists())
        self.assertTrue((wiki_root / "topics" / "_index.md").exists())
        self.assertTrue((wiki_root / "sources" / "_index.md").exists())
        self.assertTrue(any(page.kind == "topic" for page in result.pages))

    def test_rescan_updates_and_removed_files_are_reflected(self) -> None:
        page = self.source_root / "typing.md"
        page.write_text(FIXTURE_MD)
        first = self.service.scan_and_build(self.workspace.id)
        page.write_text(FIXTURE_MD.replace("Types improve correctness.", "Types improve confidence."))
        second = self.service.scan_and_build(self.workspace.id)
        self.assertGreaterEqual(second.changed_file_count, 1)

        page.unlink()
        third = self.service.scan_and_build(self.workspace.id)
        self.assertEqual(third.removed_file_count, 1)

    def test_watch_mode_reacts_to_file_changes(self) -> None:
        page = self.source_root / "watch.md"
        page.write_text(FIXTURE_MD)
        watcher = WikiWatchService(self.service)
        watcher.start(self.workspace.id)
        try:
            time.sleep(0.2)
            page.write_text(FIXTURE_MD.replace("Types improve correctness.", "Watch mode update."))
            for _ in range(20):
                status = watcher.status(self.workspace.id)
                index = self.service.page_index(self.workspace.id)
                if index.get("generated_at"):
                    break
                time.sleep(0.1)
            self.assertTrue(index.get("pages"))
        finally:
            stopped = watcher.stop(self.workspace.id)
            self.assertFalse(stopped.running)

    def test_ai_optional_modes(self) -> None:
        (self.source_root / "typing.md").write_text(FIXTURE_MD)
        self.service.update_vault(self.workspace.id, ai_enabled=False)
        disabled = self.service.scan_and_build(self.workspace.id)
        self.assertEqual(disabled.ai_status, AIGenerationStatus.DISABLED)

        self.service.update_vault(self.workspace.id, ai_enabled=True)
        previous = os.environ.pop("OPENAI_API_KEY", None)
        try:
            unavailable = self.service.scan_and_build(self.workspace.id)
            self.assertEqual(unavailable.ai_status, AIGenerationStatus.UNAVAILABLE)
            os.environ["OPENAI_API_KEY"] = "test-key"
            enhanced = self.service.scan_and_build(self.workspace.id)
            self.assertEqual(enhanced.ai_status, AIGenerationStatus.ENHANCED)
        finally:
            if previous is not None:
                os.environ["OPENAI_API_KEY"] = previous
            else:
                os.environ.pop("OPENAI_API_KEY", None)

    def test_course_metadata_groups_root_docs_without_filename_categories(self) -> None:
        (self.source_root / "INFS3822 Assessment Guide T1 2026.pdf.txt").write_text("Assessment guide content.")
        week_dir = self.source_root / "Week" / "Week 1"
        week_dir.mkdir(parents=True)
        (week_dir / "Hands-On Activity - Week 1.txt").write_text("Hands-on course activity.")

        self.service.scan_and_build(self.workspace.id)
        index = self.service.page_index(self.workspace.id)

        self.assertIn("Assessment", index["categories"])
        self.assertIn("Week", index["categories"])
        self.assertNotIn("INFS3822 Assessment Guide T1 2026.pdf", index["categories"])
        self.assertTrue(any(page["kind"] == "project" and page["title"] == "Course Docs" for page in index["pages"]))
        self.assertFalse(any(page["kind"] == "method" and "Assessment Guide" in page["title"] for page in index["pages"]))
