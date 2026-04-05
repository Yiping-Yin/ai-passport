from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.api.workspaces import ActiveWorkspaceState, WorkspaceAPI, WorkspaceService, create_demo_source_for_workspace
from app.domain import PassportReadiness, WorkspaceType
from app.storage.migrate import migrate_up
from app.storage.sources import SourceRepository
from app.storage.sqlite import connect
from app.storage.workspaces import WorkspaceRepository


NOW = datetime(2026, 4, 6, 14, 0, 0)


class WorkspaceMilestoneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "workspace.sqlite3"
        migrate_up(self.db_path)
        self.connection = connect(self.db_path)
        self.workspace_repository = WorkspaceRepository(self.connection)
        self.source_repository = SourceRepository(self.connection)
        self.service = WorkspaceService(self.workspace_repository, self.source_repository)
        self.state = ActiveWorkspaceState(self.service, self.source_repository)
        self.api = WorkspaceAPI(self.service, self.state)

    def tearDown(self) -> None:
        self.connection.close()
        self.tempdir.cleanup()

    def test_workspace_crud_enforces_type_validation(self) -> None:
        personal = self.service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="Personal",
            now=NOW,
        )
        work = self.service.create_workspace(
            workspace_type="work",
            title="Work",
            now=NOW + timedelta(minutes=1),
        )
        project = self.service.create_workspace(
            workspace_type="project",
            title="Project",
            now=NOW + timedelta(minutes=2),
        )

        with self.assertRaises(ValueError):
            self.service.create_workspace(workspace_type="school", title="Bad", now=NOW)

        updated = self.service.update_workspace(
            personal.id,
            now=NOW + timedelta(hours=1),
            title="Personal Updated",
            description="My personal workspace",
        )
        archived = self.service.archive_workspace(work.id, archived_at=NOW + timedelta(hours=2))

        visible_ids = {workspace.id for workspace in self.service.list_workspaces()}
        all_ids = {workspace.id for workspace in self.service.list_workspaces(include_archived=True)}

        self.assertEqual(updated.title, "Personal Updated")
        self.assertIsNotNone(archived.archived_at)
        self.assertNotIn(work.id, visible_ids)
        self.assertEqual(all_ids, {personal.id, work.id, project.id})

    def test_active_workspace_state_isolates_visible_sources(self) -> None:
        first = self.service.create_workspace(
            workspace_type="personal",
            title="First",
            now=NOW,
        )
        second = self.service.create_workspace(
            workspace_type="project",
            title="Second",
            now=NOW + timedelta(minutes=1),
        )

        create_demo_source_for_workspace(
            source_repository=self.source_repository,
            workspace_id=first.id,
            source_id="src-first",
            now=NOW + timedelta(minutes=2),
            title="First Notes",
        )
        create_demo_source_for_workspace(
            source_repository=self.source_repository,
            workspace_id=second.id,
            source_id="src-second",
            now=NOW + timedelta(minutes=3),
            title="Second Notes",
        )

        snapshot_first = self.api.switch_active_workspace(first.id)
        snapshot_second = self.api.switch_active_workspace(second.id)

        self.assertEqual(snapshot_first["visible_source_ids"], ["src-first"])
        self.assertEqual(snapshot_second["visible_source_ids"], ["src-second"])
        self.assertEqual(snapshot_second["active_workspace"]["id"], second.id)

    def test_readiness_placeholder_distinguishes_states(self) -> None:
        not_started = self.service.create_workspace(
            workspace_type="personal",
            title="Empty",
            now=NOW,
        )
        in_progress = self.service.create_workspace(
            workspace_type="work",
            title="Imported",
            now=NOW + timedelta(minutes=1),
        )
        ready = self.service.create_workspace(
            workspace_type="project",
            title="Ready",
            now=NOW + timedelta(minutes=2),
        )

        create_demo_source_for_workspace(
            source_repository=self.source_repository,
            workspace_id=in_progress.id,
            source_id="src-progress",
            now=NOW + timedelta(minutes=3),
            title="Progress Notes",
        )
        create_demo_source_for_workspace(
            source_repository=self.source_repository,
            workspace_id=ready.id,
            source_id="src-ready",
            now=NOW + timedelta(minutes=4),
            title="Ready Notes",
        )
        self.service.update_workspace(
            ready.id,
            now=NOW + timedelta(minutes=5),
            passport_readiness=PassportReadiness.READY,
        )

        self.assertEqual(self.service.readiness_placeholder(not_started.id).dashboard_state, "not_started")
        self.assertEqual(self.service.readiness_placeholder(in_progress.id).dashboard_state, "in_progress")
        ready_placeholder = self.service.readiness_placeholder(ready.id)
        self.assertEqual(ready_placeholder.dashboard_state, "ready_for_draft")
        self.assertTrue(ready_placeholder.can_generate_passport_draft)

    def test_archived_workspace_cannot_become_active(self) -> None:
        workspace = self.service.create_workspace(
            workspace_type="work",
            title="Archive Me",
            now=NOW,
        )
        self.service.archive_workspace(workspace.id, archived_at=NOW + timedelta(hours=1))
        with self.assertRaises(ValueError):
            self.state.set_active_workspace(workspace.id)


if __name__ == "__main__":
    unittest.main()
