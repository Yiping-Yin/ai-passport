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
                status, headers, _ = self._call_response(app=app, method="GET", path="/home")
                self.assertEqual(status, "302 Found")
                self.assertEqual(headers["Location"], "/web/index.html")
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

        status, headers, _ = self._call_response(method="GET", path="/legacy", query=f"workspace_id={self.workspace_id}")
        self.assertEqual(status, "302 Found")
        self.assertEqual(headers["Location"], f"/web/index.html?workspace_id={self.workspace_id}")

    def test_web_frontend_routes_and_context_resolve_workspace(self) -> None:
        status, headers, _ = self._call_response(self.app, "GET", "/", query=f"workspace_id={self.workspace_id}")
        self.assertEqual(status, "302 Found")
        self.assertEqual(headers["Location"], f"/web/index.html?workspace_id={self.workspace_id}")

        status, headers, _ = self._call_response(self.app, "GET", "/wiki", query=f"workspace_id={self.workspace_id}")
        self.assertEqual(status, "302 Found")
        self.assertEqual(headers["Location"], f"/web/wiki.html?workspace_id={self.workspace_id}")

        status, context = self._call_json("GET", "/web/api/site_context", query=f"workspace_id={self.workspace_id}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(context["workspace_id"], self.workspace_id)
        self.assertEqual(context["workspace_title"], "UI Workspace")
        self.assertGreaterEqual(context["page_count"], 1)

        status, articles = self._call_json("GET", "/web/tables/wiki_articles", query=f"workspace_id={self.workspace_id}")
        self.assertEqual(status, "200 OK")
        self.assertTrue(articles["data"])
        self.assertTrue(any(item["category"] == "Reference" for item in articles["data"]))
        self.assertTrue(any(item["kind"] == "topic" for item in articles["data"]))

    def test_old_ui_routes_redirect_to_web_frontend(self) -> None:
        redirects = {
            "/home": f"/web/index.html?workspace_id={self.workspace_id}",
            "/dashboard": f"/web/index.html?workspace_id={self.workspace_id}",
            "/settings": f"/web/index.html?workspace_id={self.workspace_id}",
            "/inbox": f"/web/index.html?workspace_id={self.workspace_id}",
            "/sources": f"/web/wiki.html?workspace_id={self.workspace_id}",
            "/topics": f"/web/wiki.html?workspace_id={self.workspace_id}",
            "/projects": f"/web/wiki.html?workspace_id={self.workspace_id}",
            "/methods": f"/web/wiki.html?workspace_id={self.workspace_id}",
            "/questions": f"/web/wiki.html?workspace_id={self.workspace_id}",
        }
        for path, expected in redirects.items():
            status, headers, _ = self._call_response(method="GET", path=path, query=f"workspace_id={self.workspace_id}")
            self.assertEqual(status, "302 Found")
            self.assertEqual(headers["Location"], expected)

        status, headers, _ = self._call_response(
            method="GET",
            path="/search",
            query=f"workspace_id={self.workspace_id}&q=python",
        )
        self.assertEqual(status, "302 Found")
        self.assertEqual(headers["Location"], f"/web/wiki.html?workspace_id={self.workspace_id}&q=python")

        status, headers, _ = self._call_response(
            method="GET",
            path="/methods",
            query=f"workspace_id={self.workspace_id}&page=methods/dataclass-serialization.md",
        )
        self.assertEqual(status, "302 Found")
        self.assertEqual(
            headers["Location"],
            f"/web/wiki.html?workspace_id={self.workspace_id}&page=methods%2Fdataclass-serialization.md",
        )

    def test_web_article_dataset_includes_resolved_links(self) -> None:
        status, payload = self._call_json("GET", "/web/tables/wiki_articles", query=f"workspace_id={self.workspace_id}")
        self.assertEqual(status, "200 OK")
        by_slug = {item["slug"]: item for item in payload["data"]}
        method = by_slug["method-dataclass-serialization"]
        topic = by_slug["topic-python-typing"]
        source = by_slug["source-typing"]
        self.assertIn(topic["slug"], method["links_to"])
        self.assertIn(source["slug"], method["links_to"])

    def _call_response(self, app: Application | None = None, method: str = "GET", path: str = "/", body: bytes = b"", *, query: str = "") -> tuple[str, dict[str, str], bytes]:
        status_holder: list[str] = []
        header_holder: dict[str, str] = {}

        def start_response(status, headers):
            status_holder.append(status)
            header_holder.update(dict(headers))

        target = app or self.app
        response = b"".join(target(make_testing_environ(method, path, body=body, query=query), start_response))
        return status_holder[0], header_holder, response

    def _call_json(self, method: str, path: str, payload: dict[str, object] | None = None, *, query: str = "") -> tuple[str, dict[str, object]]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        status, _, response = self._call_response(method=method, path=path, body=body, query=query)
        return status, json.loads(response.decode("utf-8"))

    def _call_html(self, app: Application, path: str, *, query: str = "") -> tuple[str, str]:
        status, _, response = self._call_response(app=app, method="GET", path=path, query=query)
        return status, response.decode("utf-8")
