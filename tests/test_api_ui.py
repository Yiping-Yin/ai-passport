from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.api.server import Application, build_context, make_testing_environ
from app.domain import PermissionLevel, SourceType, WorkspaceType
from app.ingest.service import SourceImportRequest


NOW = datetime(2026, 4, 7, 10, 0, 0)
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


class ApiAndUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.root = Path(self.tempdir.name)
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
        source = self.context.source_import_service.import_source(
            SourceImportRequest(
                workspace_id=workspace.id,
                source_type=SourceType.MARKDOWN,
                title="API Fixture",
                origin="api.md",
                content=FIXTURE,
                imported_at=NOW + timedelta(minutes=1),
            )
        )
        self.context.focus_service.create_focus_card(
            workspace_id=workspace.id,
            title="UI focus",
            goal="Exercise the UI",
            timeframe="today",
            priority=1,
            success_criteria=("UI works",),
            related_topics=("Python Typing",),
        )
        self.context.compile_service.compile_source(source.id, requested_at=NOW + timedelta(minutes=2))
        self.passport = self.context.passport_service.generate_for_workspace(workspace.id, recorded_at=NOW + timedelta(minutes=3)).passport
        self.workspace_id = workspace.id
        self.postcard_id = self.context.postcard_service.representative_postcards(workspace.id)[0].id
        self.app = Application(self.context)

    def tearDown(self) -> None:
        self.context.connection.close()
        self.tempdir.cleanup()

    def test_api_endpoints_round_trip(self) -> None:
        status, payload = self._call_json("GET", f"/api/passport/{self.passport.id}/manifest")
        self.assertEqual(status, "200 OK")
        self.assertEqual(payload["workspace_id"], self.workspace_id)

        status, visa = self._call_json(
            "POST",
            "/api/visas",
            {
                "workspace_id": self.workspace_id,
                "included_postcards": [self.postcard_id],
                "included_nodes": [],
                "permission_levels": [PermissionLevel.PASSPORT_READ.value, PermissionLevel.TOPIC_READ.value],
                "expiry_at": (NOW + timedelta(hours=1)).isoformat(),
            },
        )
        self.assertEqual(status, "200 OK")

        status, session = self._call_json(
            "POST",
            "/api/mount-sessions",
            {
                "visa_id": visa["id"],
                "client_type": "gpt",
                "started_at": NOW.isoformat(),
            },
        )
        self.assertEqual(status, "200 OK")

        status, postcard = self._call_json(
            "GET",
            f"/api/postcards/{self.postcard_id}",
            query=f"session_id={session['id']}",
        )
        self.assertEqual(status, "200 OK")
        self.assertEqual(postcard["postcard"]["id"], self.postcard_id)

        status, candidate = self._call_json(
            "POST",
            "/api/writeback-candidates",
            {
                "session_id": session["id"],
                "candidate_type": "summary",
                "target_object": f"knowledge_node:{self.context.compile_service.nodes.list_by_workspace(self.workspace_id)[0].id}",
                "content": {"summary": "API candidate"},
            },
        )
        self.assertEqual(status, "200 OK")
        self.assertEqual(candidate["status"], "pending")

        status, imported = self._call_json(
            "POST",
            "/api/sources",
            {
                "workspace_id": self.workspace_id,
                "source_type": "plain_text",
                "title": "Imported via API",
                "origin": "api-import.txt",
                "content": "Topic: API import",
                "imported_at": NOW.isoformat(),
            },
        )
        self.assertEqual(status, "200 OK")

        status, compile_payload = self._call_json(
            "POST",
            "/api/compile-jobs",
            {
                "source_id": imported["id"],
                "requested_at": NOW.isoformat(),
            },
        )
        self.assertEqual(status, "200 OK")
        self.assertTrue(compile_payload["nodes"])

    def test_ui_pages_render_expected_sections(self) -> None:
        for path, text in (
            ("/dashboard", "Dashboard"),
            ("/inbox", "Source Intake and Compile Queue"),
            ("/knowledge", "Compiled Knowledge"),
            ("/passport", "Passport Snapshot"),
            ("/mount", "Visas and Sessions"),
            ("/review", "Review Queue"),
            ("/settings", "Workspace Controls"),
        ):
            status, body = self._call_html(path, query=f"workspace_id={self.workspace_id}")
            self.assertEqual(status, "200 OK")
            self.assertIn(text, body)

    def _call_json(self, method: str, path: str, payload: dict[str, object] | None = None, *, query: str = "") -> tuple[str, dict[str, object]]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        status_holder: list[str] = []

        def start_response(status, headers):
            status_holder.append(status)

        response = b"".join(self.app(make_testing_environ(method, path, body=body, query=query), start_response))
        return status_holder[0], json.loads(response.decode("utf-8"))

    def _call_html(self, path: str, *, query: str = "") -> tuple[str, str]:
        status_holder: list[str] = []

        def start_response(status, headers):
            status_holder.append(status)

        response = b"".join(self.app(make_testing_environ("GET", path, query=query), start_response))
        return status_holder[0], response.decode("utf-8")
