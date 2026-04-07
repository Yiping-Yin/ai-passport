from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.api.server import Application, build_context, make_testing_environ
from app.domain import WorkspaceType


NOW = datetime(2026, 4, 7, 10, 0, 0)
FIXTURE = """
## Topic: Python Typing
Summary: Types improve correctness.
Related: Method: Dataclass Serialization
Typed models help keep contracts stable.

## Method: Dataclass Serialization
Summary: Convert domain objects safely.
Related: Topic: Python Typing
Serialize enums as strings and timestamps as ISO values.
""".strip()


class ApiAndUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.source_root = self.root / "vault"
        self.source_root.mkdir()
        (self.source_root / "typing.md").write_text(FIXTURE)
        (self.source_root / "notes.txt").write_text("Plain text note about local knowledge management.")
        self.context = build_context(
            db_path=self.root / "app.sqlite3",
            raw_root=self.root / "raw",
            export_root=self.root / "exports",
            review_root=self.root / "review",
        )
        workspace = self.context.workspace_service.create_workspace(
            workspace_type=WorkspaceType.PERSONAL,
            title="UI Workspace",
            now=NOW,
        )
        self.workspace_id = workspace.id
        self.context.wiki_service.update_vault(
            workspace.id,
            source_root=str(self.source_root),
            ai_enabled=False,
            watch_interval_seconds=0.1,
        )
        self.context.wiki_service.scan_and_build(workspace.id)
        self.app = Application(self.context)

    def tearDown(self) -> None:
        self.context.connection.close()
        self.tempdir.cleanup()

    def test_onboarding_when_no_workspaces(self) -> None:
        tempdir = TemporaryDirectory()
        try:
            root = Path(tempdir.name)
            context = build_context(
                db_path=root / "empty.sqlite3",
                raw_root=root / "raw",
                export_root=root / "exports",
                review_root=root / "review",
            )
            try:
                app = Application(context)
                status, body = self._call_html(app, "/home")
                self.assertEqual(status, "200 OK")
                self.assertIn("Create Your Personal Knowledge Wiki", body)
                self.assertIn("Create Workspace", body)
            finally:
                context.connection.close()
        finally:
            tempdir.cleanup()

    def test_wiki_api_endpoints_round_trip(self) -> None:
        status, config = self._call_json("GET", f"/api/vaults/{self.workspace_id}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(config["workspace_id"], self.workspace_id)

        status, updated = self._call_json(
            "POST",
            f"/api/vaults/{self.workspace_id}",
            {"source_root": str(self.source_root), "ai_enabled": False, "watch_interval_seconds": 0.1},
        )
        self.assertEqual(status, "200 OK")
        self.assertEqual(updated["source_root"], str(self.source_root))

        status, build = self._call_json("POST", "/api/wiki/scan", {"workspace_id": self.workspace_id})
        self.assertEqual(status, "200 OK")
        self.assertGreaterEqual(build["scanned_file_count"], 2)

        status, index = self._call_json("GET", f"/api/wiki/index/{self.workspace_id}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(index["workspace_id"], self.workspace_id)
        self.assertTrue(index["pages"])

        status, page = self._call_json("GET", f"/api/wiki/page/{self.workspace_id}", query="path=_index.md")
        self.assertEqual(status, "200 OK")
        self.assertIn("Wiki Home", page["content"])

        status, watch = self._call_json("POST", "/api/wiki/watch/start", {"workspace_id": self.workspace_id})
        self.assertEqual(status, "200 OK")
        self.assertTrue(watch["running"])

        status, watch_status = self._call_json("GET", f"/api/wiki/watch/{self.workspace_id}")
        self.assertEqual(status, "200 OK")
        self.assertTrue(watch_status["running"])

        status, stopped = self._call_json("POST", "/api/wiki/watch/stop", {"workspace_id": self.workspace_id})
        self.assertEqual(status, "200 OK")
        self.assertFalse(stopped["running"])

        status, legacy = self._call_html(self.app, "/legacy", query=f"workspace_id={self.workspace_id}")
        self.assertEqual(status, "200 OK")
        self.assertIn("Legacy Passport Views", legacy)

    def test_ui_pages_render_expected_sections(self) -> None:
        for path, text in (
            ("/home", "Wiki Home"),
            ("/sources", "Sources"),
            ("/topics", "Topics"),
            ("/projects", "Projects"),
            ("/methods", "Methods"),
            ("/questions", "Questions"),
            ("/search", "Search Wiki"),
            ("/settings", "Wiki Settings"),
        ):
            status, body = self._call_html(self.app, path, query=f"workspace_id={self.workspace_id}")
            self.assertEqual(status, "200 OK")
            self.assertIn(text, body)
        status, body = self._call_html(self.app, "/home", query=f"workspace_id={self.workspace_id}")
        self.assertIn("Recently Updated", body)
        self.assertIn("Popular Tags", body)

    def test_wiki_page_links_are_rewritten_to_app_routes(self) -> None:
        status, body = self._call_html(
            self.app,
            "/methods",
            query=f"workspace_id={self.workspace_id}&page=methods/dataclass-serialization.md",
        )
        self.assertEqual(status, "200 OK")
        self.assertIn(
            f"/topics?workspace_id={self.workspace_id}&amp;page=topics/python-typing.md",
            body,
        )
        self.assertIn(
            f"/sources?workspace_id={self.workspace_id}&amp;page=sources/typing.md",
            body,
        )

    def _call_json(self, method: str, path: str, payload: dict[str, object] | None = None, *, query: str = "") -> tuple[str, dict[str, object]]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        status_holder: list[str] = []

        def start_response(status, headers):
            status_holder.append(status)

        response = b"".join(self.app(make_testing_environ(method, path, body=body, query=query), start_response))
        return status_holder[0], json.loads(response.decode("utf-8"))

    def _call_html(self, app: Application, path: str, *, query: str = "") -> tuple[str, str]:
        status_holder: list[str] = []

        def start_response(status, headers):
            status_holder.append(status)

        response = b"".join(app(make_testing_environ("GET", path, query=query), start_response))
        return status_holder[0], response.decode("utf-8")
