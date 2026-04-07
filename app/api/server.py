"""Minimal local API and operator UI for the AI Knowledge Passport MVP."""

from __future__ import annotations

import html
import io
import json
import posixpath
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs
from urllib.parse import urlencode

from app.api.workspaces import ActiveWorkspaceState, WorkspaceAPI, WorkspaceService
from app.compile.review import KnowledgeNodeReviewService
from app.compile.service import KnowledgeCompileService
from app.domain import (
    CandidateType,
    CardType,
    PermissionLevel,
    PrivacyLevel,
    SourceType,
    WorkspaceType,
    serialize_entity,
)
from app.gateway.service import AuthorizationError, MountService
from app.ingest.inbox import InboxService
from app.ingest.service import RawSourceStore, SourceImportRequest, SourceImportService
from app.passport.service import PassportService, PostcardService
from app.passport.signals import CapabilitySignalService, FocusCardService
from app.review.ops import OperationsService
from app.review.service import ExportRestoreService, ReviewService
from app.storage.audit_logs import AuditLogRepository
from app.storage.capability_signals import CapabilitySignalRepository
from app.storage.compile_jobs import CompileJobRepository
from app.storage.evidence import EvidenceFragmentRepository
from app.storage.focus_cards import FocusCardRepository
from app.storage.knowledge_nodes import KnowledgeNodeRepository
from app.storage.migrate import DEFAULT_DB_PATH, migrate_up
from app.storage.mistake_patterns import MistakePatternRepository
from app.storage.mount_sessions import MountSessionRepository
from app.storage.node_evidence_links import NodeEvidenceLinkRepository
from app.storage.node_overrides import KnowledgeNodeOverrideRepository
from app.storage.passports import PassportRepository
from app.storage.postcards import PostcardRepository
from app.storage.review_candidates import ReviewCandidateRepository
from app.storage.sources import SourceRepository
from app.storage.sqlite import ROOT as REPO_ROOT
from app.storage.sqlite import connect
from app.storage.visas import VisaBundleRepository
from app.storage.workspaces import WorkspaceRepository
from app.utils.time import utc_now
from app.wiki import WikiService, WikiWatchService


DEFAULT_RAW_ROOT = REPO_ROOT / "data" / "workspaces"
DEFAULT_EXPORT_ROOT = REPO_ROOT / "data" / "exports"
DEFAULT_REVIEW_ROOT = REPO_ROOT / "data" / "review"


@dataclass(slots=True)
class AppContext:
    workspace_api: WorkspaceAPI
    workspace_service: WorkspaceService
    active_workspace_state: ActiveWorkspaceState
    source_import_service: SourceImportService
    inbox_service: InboxService
    compile_service: KnowledgeCompileService
    signal_service: CapabilitySignalService
    focus_service: FocusCardService
    postcard_service: PostcardService
    passport_service: PassportService
    mount_service: MountService
    review_service: ReviewService
    export_restore_service: ExportRestoreService
    operations_service: OperationsService
    wiki_service: WikiService
    wiki_watch_service: WikiWatchService
    connection: object


def build_context(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    export_root: Path = DEFAULT_EXPORT_ROOT,
    review_root: Path = DEFAULT_REVIEW_ROOT,
) -> AppContext:
    migrate_up(db_path)
    connection = connect(db_path)
    workspaces = WorkspaceRepository(connection)
    sources = SourceRepository(connection)
    capability_signals = CapabilitySignalRepository(connection)
    mistake_patterns = MistakePatternRepository(connection)
    focus_cards = FocusCardRepository(connection)
    compile_jobs = CompileJobRepository(connection)
    evidence = EvidenceFragmentRepository(connection)
    node_evidence = NodeEvidenceLinkRepository(connection)
    knowledge_nodes = KnowledgeNodeRepository(connection)
    postcards = PostcardRepository(connection)
    passports = PassportRepository(connection)
    visas = VisaBundleRepository(connection)
    sessions = MountSessionRepository(connection)
    candidates = ReviewCandidateRepository(connection)
    audits = AuditLogRepository(connection)
    raw_store = RawSourceStore(raw_root)
    wiki_service = WikiService(
        workspace_repository=workspaces,
        raw_root=raw_root,
    )
    wiki_watch_service = WikiWatchService(wiki_service)

    workspace_service = WorkspaceService(workspaces, sources)
    active_workspace_state = ActiveWorkspaceState(workspace_service, sources)
    workspace_api = WorkspaceAPI(workspace_service, active_workspace_state)
    source_import_service = SourceImportService(
        workspace_repository=workspaces,
        source_repository=sources,
        raw_store=raw_store,
    )
    compile_service = KnowledgeCompileService(
        source_repository=sources,
        compile_job_repository=compile_jobs,
        knowledge_node_repository=knowledge_nodes,
        evidence_repository=evidence,
        node_evidence_link_repository=node_evidence,
        raw_store=raw_store,
    )
    signal_service = CapabilitySignalService(
        compiler=compile_service,
        capability_signal_repository=capability_signals,
        mistake_pattern_repository=mistake_patterns,
    )
    focus_service = FocusCardService(focus_cards)
    postcard_service = PostcardService(
        compiler=compile_service,
        capability_signals=capability_signals,
        mistake_patterns=mistake_patterns,
        postcard_repository=postcards,
    )
    passport_service = PassportService(
        workspace_repository=workspaces,
        compiler=compile_service,
        capability_signal_service=signal_service,
        capability_signal_repository=capability_signals,
        mistake_pattern_repository=mistake_patterns,
        focus_service=focus_service,
        postcard_service=postcard_service,
        postcard_repository=postcards,
        passport_repository=passports,
    )
    mount_service = MountService(
        visa_repository=visas,
        session_repository=sessions,
        audit_repository=audits,
        passport_repository=passports,
        passport_service=passport_service,
        postcard_repository=postcards,
        postcard_service=postcard_service,
        knowledge_node_repository=knowledge_nodes,
        focus_service=focus_service,
    )
    review_service = ReviewService(
        candidate_repository=candidates,
        session_repository=sessions,
        audit_repository=audits,
        knowledge_review_service=KnowledgeNodeReviewService(
            knowledge_node_repository=knowledge_nodes,
            override_repository=KnowledgeNodeOverrideRepository(connection),
        ),
        postcard_repository=postcards,
        focus_repository=focus_cards,
        mount_service=mount_service,
        storage_root=review_root,
    )
    export_restore_service = ExportRestoreService(
        workspace_repository=workspaces,
        source_repository=sources,
        knowledge_node_repository=knowledge_nodes,
        evidence_repository=evidence,
        capability_signal_repository=capability_signals,
        mistake_pattern_repository=mistake_patterns,
        focus_repository=focus_cards,
        compile_job_repository=compile_jobs,
        passport_repository=passports,
        postcard_repository=postcards,
        visa_repository=visas,
        session_repository=sessions,
        candidate_repository=candidates,
        audit_repository=audits,
        export_root=export_root,
        raw_root=raw_root,
    )
    operations_service = OperationsService(
        workspace_repository=workspaces,
        source_repository=sources,
        passport_service=passport_service,
        postcard_service=postcard_service,
        visa_repository=visas,
        session_repository=sessions,
        candidate_repository=candidates,
        audit_repository=audits,
    )
    inbox_service = InboxService(
        workspace_repository=workspaces,
        source_repository=sources,
        compile_job_repository=compile_jobs,
        evidence_repository=evidence,
        raw_store=raw_store,
    )
    return AppContext(
        workspace_api=workspace_api,
        workspace_service=workspace_service,
        active_workspace_state=active_workspace_state,
        source_import_service=source_import_service,
        inbox_service=inbox_service,
        compile_service=compile_service,
        signal_service=signal_service,
        focus_service=focus_service,
        postcard_service=postcard_service,
        passport_service=passport_service,
        mount_service=mount_service,
        review_service=review_service,
        export_restore_service=export_restore_service,
        operations_service=operations_service,
        wiki_service=wiki_service,
        wiki_watch_service=wiki_watch_service,
        connection=connection,
    )


class Application:
    def __init__(self, context: AppContext) -> None:
        self.ctx = context

    def __call__(self, environ: dict[str, object], start_response: Callable[..., object]) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=True)
        try:
            if path == "/":
                return self._redirect(self._web_entry_url("index.html", query), start_response)
            if path == "/wiki":
                return self._redirect(self._web_entry_url("wiki.html", query), start_response)
            if path.startswith("/web/"):
                status, headers, body = self._handle_web(method, path, query, environ)
            elif path.startswith("/api/"):
                status, headers, body = self._handle_api(method, path, query, environ)
            else:
                redirect = self._legacy_ui_redirect(path, query)
                if redirect is not None:
                    return self._redirect(redirect, start_response)
                status, headers, body = self._handle_ui(method, path, query, environ)
        except AuthorizationError as exc:
            status, headers, body = self._json_response(403, {"error": str(exc)})
        except KeyError as exc:
            status, headers, body = self._json_response(404, {"error": str(exc)})
        except ValueError as exc:
            status, headers, body = self._json_response(400, {"error": str(exc)})
        start_response(status, headers)
        return [body]

    def _handle_api(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        environ: dict[str, object],
    ) -> tuple[str, list[tuple[str, str]], bytes]:
        if method == "GET" and path.startswith("/api/vaults/"):
            workspace_id = path[len("/api/vaults/") :]
            config = self.ctx.wiki_service.get_or_create_vault(workspace_id)
            return self._json_response(200, asdict(config))
        if method == "POST" and path.startswith("/api/vaults/"):
            workspace_id = path[len("/api/vaults/") :]
            data = _read_json(environ)
            config = self.ctx.wiki_service.update_vault(
                workspace_id,
                source_root=data.get("source_root"),
                wiki_root=data.get("wiki_root"),
                watcher_enabled=data.get("watcher_enabled"),
                ai_enabled=data.get("ai_enabled"),
                watch_interval_seconds=data.get("watch_interval_seconds"),
            )
            return self._json_response(200, asdict(config))
        if method == "POST" and path == "/api/wiki/scan":
            data = _read_json(environ)
            result = self.ctx.wiki_service.scan_and_build(data["workspace_id"])
            return self._json_response(200, serialize_build_result(result))
        if method == "POST" and path == "/api/wiki/watch/start":
            data = _read_json(environ)
            state = self.ctx.wiki_watch_service.start(data["workspace_id"])
            return self._json_response(200, asdict(state))
        if method == "POST" and path == "/api/wiki/watch/stop":
            data = _read_json(environ)
            state = self.ctx.wiki_watch_service.stop(data["workspace_id"])
            return self._json_response(200, asdict(state))
        if method == "GET" and path.startswith("/api/wiki/watch/"):
            workspace_id = path[len("/api/wiki/watch/") :]
            return self._json_response(200, asdict(self.ctx.wiki_watch_service.status(workspace_id)))
        if method == "GET" and path.startswith("/api/wiki/index/"):
            workspace_id = path[len("/api/wiki/index/") :]
            return self._json_response(200, self.ctx.wiki_service.page_index(workspace_id))
        if method == "GET" and path.startswith("/api/wiki/page/"):
            workspace_id = path[len("/api/wiki/page/") :]
            relative_path = _single(query, "path")
            return self._json_response(
                200,
                {
                    "workspace_id": workspace_id,
                    "path": relative_path,
                    "content": self.ctx.wiki_service.read_page(workspace_id, relative_path),
                },
            )
        if method == "GET" and path.startswith("/api/wiki/status/"):
            workspace_id = path[len("/api/wiki/status/") :]
            return self._json_response(200, self.ctx.wiki_service.status(workspace_id))
        if method == "GET" and path.startswith("/api/passport/") and path.endswith("/manifest"):
            passport_id = path[len("/api/passport/") : -len("/manifest")]
            return self._json_response(200, self.ctx.passport_service.read_machine_manifest(passport_id))
        if method == "GET" and path.startswith("/api/postcards/"):
            postcard_id = path[len("/api/postcards/") :]
            session_id = _single(query, "session_id")
            payload = self.ctx.mount_service.read_postcard(session_id, postcard_id).payload
            return self._json_response(200, payload)
        if method == "POST" and path == "/api/visas":
            data = _read_json(environ)
            expiry_at = datetime.fromisoformat(data["expiry_at"]) if data.get("expiry_at") else None
            permissions = tuple(PermissionLevel(item) for item in data.get("permission_levels", ["passport_read"]))
            visa = self.ctx.mount_service.issue_visa(
                workspace_id=data["workspace_id"],
                included_postcards=tuple(data.get("included_postcards", [])),
                included_nodes=tuple(data.get("included_nodes", [])),
                permission_levels=permissions,
                expiry_at=expiry_at,
            )
            return self._json_response(200, serialize_entity(visa))
        if method == "POST" and path.startswith("/api/visas/") and path.endswith("/revoke"):
            visa_id = path[len("/api/visas/") : -len("/revoke")]
            visa = self.ctx.mount_service.revoke_visa(visa_id, actor="api")
            return self._json_response(200, serialize_entity(visa))
        if method == "POST" and path == "/api/mount-sessions":
            data = _read_json(environ)
            session = self.ctx.mount_service.start_session(
                data["visa_id"],
                client_type=data["client_type"],
                started_at=datetime.fromisoformat(data["started_at"]),
            )
            return self._json_response(200, serialize_entity(session))
        if method == "POST" and path.startswith("/api/mount-sessions/") and path.endswith("/end"):
            session_id = path[len("/api/mount-sessions/") : -len("/end")]
            session = self.ctx.mount_service.end_session(session_id, ended_at=utc_now())
            return self._json_response(200, serialize_entity(session))
        if method == "POST" and path == "/api/writeback-candidates":
            data = _read_json(environ)
            candidate = self.ctx.review_service.create_candidate(
                session_id=data["session_id"],
                candidate_type=CandidateType(data["candidate_type"]),
                target_object=data["target_object"],
                content=data["content"],
                evidence_ids=tuple(data.get("evidence_ids", [])),
            )
            return self._json_response(200, serialize_entity(candidate))
        if method == "POST" and path.startswith("/api/review-candidates/") and path.endswith("/accept"):
            candidate_id = path[len("/api/review-candidates/") : -len("/accept")]
            candidate = self.ctx.review_service.accept_candidate(candidate_id, actor="api")
            return self._json_response(200, serialize_entity(candidate))
        if method == "POST" and path.startswith("/api/review-candidates/") and path.endswith("/reject"):
            candidate_id = path[len("/api/review-candidates/") : -len("/reject")]
            candidate = self.ctx.review_service.reject_candidate(candidate_id, actor="api")
            return self._json_response(200, serialize_entity(candidate))
        if method == "POST" and path.startswith("/api/review-candidates/") and path.endswith("/edit-accept"):
            candidate_id = path[len("/api/review-candidates/") : -len("/edit-accept")]
            data = _read_json(environ)
            candidate = self.ctx.review_service.edit_then_accept(candidate_id, actor="api", content_override=data.get("content_override", {}))
            return self._json_response(200, serialize_entity(candidate))
        if method == "POST" and path == "/api/sources":
            data = _read_json(environ)
            source = self.ctx.source_import_service.import_source(
                SourceImportRequest(
                    workspace_id=data["workspace_id"],
                    source_type=SourceType(data["source_type"]),
                    title=data["title"],
                    origin=data["origin"],
                    content=data["content"],
                    imported_at=datetime.fromisoformat(data.get("imported_at") or utc_now().isoformat()),
                    privacy_level=data.get("privacy_level"),
                    tags=tuple(data.get("tags", [])),
                )
            )
            return self._json_response(200, serialize_entity(source))
        if method == "POST" and path == "/api/compile-jobs":
            data = _read_json(environ)
            result = self.ctx.compile_service.compile_source(
                data["source_id"],
                requested_at=datetime.fromisoformat(data.get("requested_at") or utc_now().isoformat()),
            )
            return self._json_response(
                200,
                {
                    "job": serialize_entity(result.job),
                    "nodes": [serialize_entity(node) for node in result.nodes],
                },
            )
        if method == "GET" and path.startswith("/api/metrics/"):
            workspace_id = path[len("/api/metrics/") :]
            return self._json_response(200, self.ctx.operations_service.metrics(workspace_id))
        if method == "GET" and path.startswith("/api/release-gates/"):
            workspace_id = path[len("/api/release-gates/") :]
            gates = [
                {"key": gate.key, "passed": gate.passed, "details": gate.details}
                for gate in self.ctx.operations_service.release_gates(workspace_id)
            ]
            return self._json_response(200, {"workspace_id": workspace_id, "gates": gates})
        if method == "POST" and path == "/api/export":
            data = _read_json(environ)
            export_path = self.ctx.export_restore_service.export_workspace(
                data["workspace_id"],
                include_hidden=bool(data.get("include_hidden", False)),
            )
            return self._json_response(200, {"path": str(export_path)})
        if method == "POST" and path == "/api/restore":
            data = _read_json(environ)
            payload = self.ctx.export_restore_service.restore_workspace(Path(data["path"]))
            return self._json_response(200, payload)
        raise KeyError(path)

    _WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
    _WEB_MIME = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff2": "font/woff2",
        ".map": "application/json",
    }

    def _handle_web(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        environ: dict[str, object],
    ) -> tuple[str, list[tuple[str, str]], bytes]:
        relative = path[len("/web/"):]
        if method == "POST" and relative == "api/rescan":
            return self._rescan_response(query, environ)
        if method == "POST" and relative == "api/connect":
            return self._connect_response(query, environ)
        if method != "GET":
            return self._json_response(405, {"error": "method not allowed"})
        if relative == "api/site_context":
            return self._site_context_response(query)
        if relative.startswith("tables/wiki_articles"):
            return self._wiki_articles_response(query)
        # Resolve safely under _WEB_ROOT
        target = (self._WEB_ROOT / relative).resolve()
        try:
            target.relative_to(self._WEB_ROOT.resolve())
        except ValueError:
            return self._json_response(403, {"error": "forbidden"})
        if not target.is_file():
            return self._json_response(404, {"error": "not found"})
        mime = self._WEB_MIME.get(target.suffix.lower(), "application/octet-stream")
        body = target.read_bytes()
        return "200 OK", [("Content-Type", mime), ("Content-Length", str(len(body)))], body

    def _site_context_response(self, query: dict[str, list[str]]) -> tuple[str, list[tuple[str, str]], bytes]:
        workspace_id = self._workspace_id_from_query(query)
        payload: dict[str, object] = {
            "workspace_id": workspace_id,
            "workspace_title": "",
            "source_root": "",
            "wiki_root": "",
            "last_build_status": "not_started",
            "last_scan_at": None,
            "page_count": 0,
            "source_file_count": 0,
            "category_count": 0,
            "categories": {},
            "tags": {},
            "featured": [],
            "recent": [],
        }
        if not workspace_id:
            return self._json_response(200, payload)
        workspace = self.ctx.workspace_service.get_workspace(workspace_id)
        vault = self.ctx.wiki_service.get_or_create_vault(workspace_id)
        index = self.ctx.wiki_service.page_index(workspace_id)
        pages = _content_pages(index)
        featured = sorted(
            [page for page in pages if page.get("kind") != "source"],
            key=lambda page: (
                _feature_rank(page),
                len(page.get("backlinks", [])),
                len(page.get("source_refs", [])),
                page.get("updated_at") or "",
            ),
            reverse=True,
        )[:6]
        recent = sorted(pages, key=lambda page: page.get("updated_at") or "", reverse=True)[:8]
        featured = [{**page, "title": self._prettify_title(page.get("title") or page.get("path") or "")} for page in featured]
        recent = [{**page, "title": self._prettify_title(page.get("title") or page.get("path") or "")} for page in recent]
        payload.update(
            {
                "workspace_id": workspace_id,
                "workspace_title": workspace.title,
                "source_root": vault.source_root or "",
                "wiki_root": vault.wiki_root,
                "last_build_status": vault.last_build_status,
                "last_scan_at": vault.last_scan_at,
                "page_count": len(pages),
                "source_file_count": len(index.get("files", {})),
                "category_count": len(index.get("categories", {})),
                "categories": index.get("categories", {}),
                "tags": index.get("tags", {}),
                "featured": featured,
                "recent": recent,
            }
        )
        return self._json_response(200, payload)

    def _connect_response(self, query: dict[str, list[str]], environ: dict[str, object]) -> tuple[str, list[tuple[str, str]], bytes]:
        try:
            data = _read_json(environ)
        except Exception:
            return self._json_response(400, {"error": "invalid JSON body"})
        source_root = (data.get("source_root") or "").strip()
        if not source_root:
            return self._json_response(400, {"error": "source_root is required"})
        if not Path(source_root).expanduser().is_dir():
            return self._json_response(400, {"error": f"folder not found: {source_root}"})
        workspace_id = self._workspace_id_from_query(query)
        if not workspace_id:
            workspace = self.ctx.workspace_service.create_workspace(
                workspace_type=WorkspaceType.PERSONAL,
                title=Path(source_root).name or "Workspace",
                now=utc_now(),
            )
            workspace_id = workspace.id
        try:
            self.ctx.wiki_service.update_vault(
                workspace_id,
                source_root=str(Path(source_root).expanduser()),
                ai_enabled=False,
            )
            result = self.ctx.wiki_service.scan_and_build(workspace_id)
        except Exception as exc:
            return self._json_response(500, {"error": str(exc)})
        return self._json_response(200, {
            "workspace_id": workspace_id,
            "source_root": str(Path(source_root).expanduser()),
            "scanned_file_count": getattr(result, "scanned_file_count", None),
        })

    def _rescan_response(self, query: dict[str, list[str]], environ: dict[str, object]) -> tuple[str, list[tuple[str, str]], bytes]:
        workspace_id = self._workspace_id_from_query(query)
        if not workspace_id:
            return self._json_response(400, {"error": "no workspace configured"})
        try:
            result = self.ctx.wiki_service.scan_and_build(workspace_id)
        except Exception as exc:  # surface to UI
            return self._json_response(500, {"error": str(exc)})
        return self._json_response(200, {
            "workspace_id": workspace_id,
            "scanned_file_count": getattr(result, "scanned_file_count", None),
            "generated_at": getattr(result, "generated_at", None),
        })

    def _wiki_articles_response(self, query: dict[str, list[str]]) -> tuple[str, list[tuple[str, str]], bytes]:
        workspace_id = self._workspace_id_from_query(query)
        articles: list[dict[str, object]] = []
        if workspace_id:
            index = self.ctx.wiki_service.page_index(workspace_id)
            pages = _content_pages(index)
            slug_by_path = {
                str(page["path"]): self._slugify(f"{page.get('kind', 'page')}-{page.get('title') or page.get('path')}")
                for page in pages
            }
            for page in pages:
                rel_path = page["path"]
                try:
                    content = self.ctx.wiki_service.read_page(workspace_id, rel_path)
                except KeyError:
                    content = ""
                tags = list(page.get("tags") or [])
                kind = page.get("kind") or "topic"
                links_to = []
                for href in _extract_markdown_links(content):
                    normalized = posixpath.normpath(posixpath.join(posixpath.dirname(rel_path), href))
                    if normalized in slug_by_path:
                        links_to.append(slug_by_path[normalized])
                backlink_slugs = [
                    slug_by_path[target]
                    for target in page.get("backlinks", [])
                    if target in slug_by_path
                ]
                articles.append({
                    "id": rel_path,
                    "path": rel_path,
                    "title": self._prettify_title(page.get("title") or rel_path),
                    "slug": slug_by_path[rel_path],
                    "summary": page.get("summary") or "",
                    "content": content,
                    "category": page.get("category") or "Reference",
                    "kind": kind,
                    "tags": tags,
                    "backlinks": backlink_slugs,
                    "links_to": sorted(set(links_to)),
                    "difficulty": page.get("difficulty") or "Intermediate",
                    "word_count": len(content.split()),
                    "last_edited": page.get("updated_at") or page.get("created_at") or "",
                    "status": "Published",
                })
        body = json.dumps({"data": articles, "total": len(articles)}).encode("utf-8")
        return "200 OK", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))], body

    def _workspace_id_from_query(self, query: dict[str, list[str]]) -> str:
        return _single(query, "workspace_id", default=self._default_workspace_id() if self.ctx.workspace_service.list_workspaces() else "")

    def _web_entry_url(self, filename: str, query: dict[str, list[str]]) -> str:
        workspace_id = self._workspace_id_from_query(query)
        if not workspace_id:
            return f"/web/{filename}"
        return f"/web/{filename}?{urlencode({'workspace_id': workspace_id})}"

    def _legacy_ui_redirect(self, path: str, query: dict[str, list[str]]) -> str | None:
        index_paths = {
            "/home",
            "/dashboard",
            "/inbox",
            "/passport",
            "/mount",
            "/review",
            "/settings",
            "/legacy",
            "/legacy/knowledge",
            "/legacy/passport",
            "/legacy/mount",
            "/legacy/review",
            "/legacy/settings",
        }
        wiki_paths = {
            "/sources",
            "/topics",
            "/projects",
            "/methods",
            "/questions",
            "/search",
        }
        if path in index_paths:
            return self._web_entry_url("index.html", query)
        if path in wiki_paths:
            forwarded: dict[str, str] = {}
            workspace_id = self._workspace_id_from_query(query)
            if workspace_id:
                forwarded["workspace_id"] = workspace_id
            page = _single(query, "page", default="")
            q = _single(query, "q", default="")
            if page:
                forwarded["page"] = page
            if q:
                forwarded["q"] = q
            if not forwarded:
                return "/web/wiki.html"
            return f"/web/wiki.html?{urlencode(forwarded)}"
        return None

    @staticmethod
    def _slugify(text: str) -> str:
        slug = __import__("re").sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
        return slug or "untitled"

    _TITLE_LOWER = {"a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "of", "on", "or", "the", "to", "vs", "with"}

    @classmethod
    def _prettify_title(cls, raw: str) -> str:
        import re as _re
        text = str(raw or "").rsplit("/", 1)[-1]
        text = _re.sub(r"\.(md|txt|pdf|markdown)$", "", text, flags=_re.IGNORECASE)
        text = text.replace("_", " ").replace("-", " ").strip()
        if not text:
            return "Untitled"
        words = text.split()
        out = []
        for i, w in enumerate(words):
            wl = w.lower()
            if 0 < i < len(words) - 1 and wl in cls._TITLE_LOWER:
                out.append(wl)
            elif w.isupper() and 2 <= len(w) <= 4:
                out.append(w)
            else:
                out.append(wl[:1].upper() + wl[1:])
        return " ".join(out)

    def _handle_ui(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        environ: dict[str, object],
    ) -> tuple[str, list[tuple[str, str]], bytes]:
        if method == "POST":
            return self._handle_ui_action(path, query, environ)
        if not self.ctx.workspace_service.list_workspaces():
            return "200 OK", [("Content-Type", "text/html; charset=utf-8")], self._onboarding_page().encode("utf-8")
        workspace_id = _single(query, "workspace_id", default=self._default_workspace_id())
        if path in {"/home", "/dashboard"}:
            html_body = self._home_page(workspace_id)
        elif path == "/sources":
            html_body = self._wiki_category_page(workspace_id, "source", query)
        elif path == "/topics":
            html_body = self._wiki_category_page(workspace_id, "topic", query)
        elif path == "/projects":
            html_body = self._wiki_category_page(workspace_id, "project", query)
        elif path == "/methods":
            html_body = self._wiki_category_page(workspace_id, "method", query)
        elif path == "/questions":
            html_body = self._wiki_category_page(workspace_id, "question", query)
        elif path == "/inbox":
            html_body = self._inbox_page(workspace_id)
        elif path == "/legacy/knowledge":
            html_body = self._knowledge_page(workspace_id)
        elif path == "/legacy/passport":
            html_body = self._passport_page(workspace_id)
        elif path == "/legacy/mount":
            html_body = self._mount_page(workspace_id)
        elif path == "/legacy/review":
            html_body = self._review_page(workspace_id)
        elif path == "/legacy/settings":
            html_body = self._settings_page(workspace_id)
        elif path == "/passport":
            html_body = self._passport_page(workspace_id)
        elif path == "/mount":
            html_body = self._mount_page(workspace_id)
        elif path == "/review":
            html_body = self._review_page(workspace_id)
        elif path == "/settings":
            html_body = self._settings_page(workspace_id)
        elif path == "/search":
            html_body = self._search_page(workspace_id, _single(query, "q", default=""))
        elif path == "/legacy":
            html_body = self._legacy_page(workspace_id)
        elif path == "/passport":
            html_body = self._passport_page(workspace_id)
        else:
            raise KeyError(path)
        flash = _single(query, "flash", default="")
        if flash:
            banner = f"<div class='flash'>{_e(flash)}</div>"
            html_body = html_body.replace("<div class='shell'>", f"<div class='shell'>{banner}", 1)
        return "200 OK", [("Content-Type", "text/html; charset=utf-8")], html_body.encode("utf-8")

    def _handle_ui_action(
        self,
        path: str,
        query: dict[str, list[str]],
        environ: dict[str, object],
    ) -> tuple[str, list[tuple[str, str]], bytes]:
        data = _read_form(environ)
        if path == "/actions/create-workspace":
            title = data["title"]
            workspace = self.ctx.workspace_service.create_workspace(
                workspace_type=WorkspaceType(data.get("workspace_type", WorkspaceType.PERSONAL.value)),
                title=title,
                now=utc_now(),
            )
            self.ctx.wiki_service.get_or_create_vault(workspace.id)
            return self._redirect(f"/settings?workspace_id={workspace.id}")
        workspace_id = data.get("workspace_id") or self._default_workspace_id()
        if path == "/actions/connect-folder":
            self.ctx.wiki_service.update_vault(
                workspace_id,
                source_root=data["source_root"],
                ai_enabled=data.get("ai_enabled") == "on",
                wiki_root=data.get("wiki_root") or None,
            )
            return self._redirect(f"/home?workspace_id={workspace_id}&flash=Source+folder+connected")
        if path == "/actions/scan-folder":
            self.ctx.wiki_service.scan_and_build(workspace_id)
            return self._redirect(f"/home?workspace_id={workspace_id}&flash=Folder+scanned+and+wiki+rebuilt")
        if path == "/actions/rebuild-wiki":
            self.ctx.wiki_service.scan_and_build(workspace_id)
            return self._redirect(f"/home?workspace_id={workspace_id}&flash=Wiki+rebuilt")
        if path == "/actions/start-watch":
            self.ctx.wiki_watch_service.start(workspace_id)
            return self._redirect(f"/settings?workspace_id={workspace_id}&flash=Watch+started")
        if path == "/actions/stop-watch":
            self.ctx.wiki_watch_service.stop(workspace_id)
            return self._redirect(f"/settings?workspace_id={workspace_id}&flash=Watch+stopped")
        if path == "/actions/open-wiki-folder":
            self._open_folder(Path(self.ctx.wiki_service.get_or_create_vault(workspace_id).wiki_root))
            return self._redirect(f"/settings?workspace_id={workspace_id}&flash=Opened+wiki+folder")
        if path == "/actions/generate-passport":
            self.ctx.passport_service.generate_for_workspace(workspace_id, recorded_at=utc_now())
            return self._redirect(f"/passport?workspace_id={workspace_id}&flash=Passport+generated")
        if path == "/actions/issue-default-visa":
            self.ctx.mount_service.issue_default_passport_visa(workspace_id, expiry_at=utc_now() + timedelta(hours=1))
            return self._redirect(f"/mount?workspace_id={workspace_id}&flash=Visa+issued")
        if path == "/actions/revoke-visa":
            self.ctx.mount_service.revoke_visa(data["visa_id"], actor="operator")
            return self._redirect(f"/mount?workspace_id={workspace_id}&flash=Visa+revoked")
        if path == "/actions/start-session":
            self.ctx.mount_service.start_session(data["visa_id"], client_type="operator", started_at=utc_now())
            return self._redirect(f"/mount?workspace_id={workspace_id}&flash=Session+started")
        if path == "/actions/end-session":
            self.ctx.mount_service.end_session(data["session_id"], ended_at=utc_now())
            return self._redirect(f"/mount?workspace_id={workspace_id}&flash=Session+ended")
        if path == "/actions/accept-candidate":
            self.ctx.review_service.accept_candidate(data["candidate_id"], actor="operator")
            return self._redirect("/review?flash=Candidate+accepted")
        if path == "/actions/edit-accept-candidate":
            override = json.loads(data["content_override"]) if data.get("content_override") else {}
            self.ctx.review_service.edit_then_accept(data["candidate_id"], actor="operator", content_override=override)
            return self._redirect("/review?flash=Candidate+edited+and+accepted")
        if path == "/actions/reject-candidate":
            self.ctx.review_service.reject_candidate(data["candidate_id"], actor="operator")
            return self._redirect("/review?flash=Candidate+rejected")
        if path == "/actions/export-workspace":
            self.ctx.export_restore_service.export_workspace(workspace_id, include_hidden=False)
            return self._redirect(f"/settings?workspace_id={workspace_id}&flash=Workspace+exported")
        if path == "/actions/restore-workspace":
            self.ctx.export_restore_service.restore_workspace(Path(data["path"]))
            return self._redirect(f"/settings?workspace_id={workspace_id}&flash=Workspace+restored")
        if path == "/actions/import-source":
            self.ctx.source_import_service.import_source(
                SourceImportRequest(
                    workspace_id=workspace_id,
                    source_type=SourceType(data.get("source_type", SourceType.MARKDOWN.value)),
                    title=data["title"],
                    origin=data.get("origin") or data["title"].lower().replace(" ", "_"),
                    content=data["content"],
                    imported_at=utc_now(),
                    privacy_level=data.get("privacy_level") or None,
                )
            )
            return self._redirect(f"/inbox?workspace_id={workspace_id}&flash=Source+imported")
        if path == "/actions/compile-source":
            self.ctx.compile_service.compile_source(data["source_id"], requested_at=utc_now())
            return self._redirect(f"/inbox?workspace_id={workspace_id}&flash=Source+compiled")
        raise KeyError(path)

    def _dashboard_page(self, workspace_id: str) -> str:
        readiness = self.ctx.workspace_service.readiness_placeholder(workspace_id)
        focus = self.ctx.focus_service.active_focus(workspace_id)
        inbox_items = self.ctx.inbox_service.list_items(workspace_id=workspace_id)
        sessions = [
            session
            for visa in self.ctx.mount_service.visas.list_by_workspace(workspace_id)
            for session in self.ctx.mount_service.sessions.list_by_visa(visa.id)
        ]
        pending_candidates = [candidate for candidate in self.ctx.review_service.candidates.list_all() if candidate.status.value == "pending"]
        metrics = self.ctx.operations_service.metrics(workspace_id)
        body = f"""
        <section class="hero">
          <p class="eyebrow">Dashboard</p>
          <h1>{_e(self.ctx.workspace_service.get_workspace(workspace_id).title)}</h1>
          <p class="lede">Passport readiness is <strong>{_e(readiness.dashboard_state)}</strong>. Imported items, review queue, and recent sessions stay in one operator view.</p>
        </section>
        <section class="grid">
          <article class="panel"><h2>Active Focus</h2><p>{_e(focus.goal if focus else 'No active focus')}</p></article>
          <article class="panel"><h2>Recent Imports</h2><p>{len(inbox_items)} items in Inbox</p></article>
          <article class="panel"><h2>Pending Review</h2><p>{len(pending_candidates)} pending candidates</p></article>
          <article class="panel"><h2>Mount Sessions</h2><p>{len(sessions)} sessions recorded</p></article>
          <article class="panel"><h2>Acceptance Rate</h2><p>{metrics['review_candidate_acceptance_rate']:.2f}</p></article>
          <article class="panel"><h2>Representative Postcards</h2><p>{metrics['representative_postcard_count']}</p></article>
        </section>
        """
        return _page("Dashboard", body, workspace_id=workspace_id)

    def _home_page(self, workspace_id: str) -> str:
        workspace = self.ctx.workspace_service.get_workspace(workspace_id)
        vault = self.ctx.wiki_service.get_or_create_vault(workspace_id)
        index = self.ctx.wiki_service.page_index(workspace_id)
        if not vault.source_root:
            return _page(
                "Home",
                f"""
                <section class="hero">
                  <p class="eyebrow">Wiki Home</p>
                  <h1>{_e(workspace.title)}</h1>
                  <p class="lede">Connect a local source folder to generate your personal knowledge wiki.</p>
                </section>
                {self._connect_folder_form(workspace_id, vault)}
                """,
                active="/home",
                workspace_id=workspace_id,
            )
        pages = _content_pages(index)
        categories = sorted(index.get("categories", {}).items(), key=lambda item: (-item[1], item[0]))
        tags = sorted(index.get("tags", {}).items(), key=lambda item: (-item[1], item[0]))[:18]
        recent_pages = sorted(pages, key=lambda page: page.get("updated_at") or "", reverse=True)[:8]
        featured_pages = sorted(
            [page for page in pages if page["kind"] != "source"],
            key=lambda page: (
                _feature_rank(page),
                len(page.get("backlinks", [])),
                len(page.get("source_refs", [])),
                page.get("updated_at") or "",
            ),
            reverse=True,
        )[:6]
        warning_html = ""
        if index.get("warnings"):
            warning_html = "<article class='panel'><h2>Warnings</h2>" + "".join(
                f"<div class='item'><p>{_e(warning)}</p></div>" for warning in index.get("warnings", [])
            ) + "</article>"
        category_cards = "".join(
            f"""
            <a class="category-card" href="/search?workspace_id={_e(workspace_id)}&q={_e(category)}">
              <strong>{_e(category)}</strong>
              <span>{count} pages</span>
            </a>
            """
            for category, count in categories
        ) or "<p class='empty'>No categories yet.</p>"
        tag_cloud = "".join(
            f"<a class='pill' href='/search?workspace_id={_e(workspace_id)}&q={_e(tag)}'>{_e(tag)} <span>{count}</span></a>"
            for tag, count in tags
        ) or "<p class='empty'>No tags yet.</p>"
        body = f"""
        <section class="hero">
          <p class="eyebrow">Wiki Home</p>
          <h1>{_e(workspace.title)}</h1>
          <p class="lede">Course wiki generated from your local folder. Markdown is the source of truth; the app is the browser and organizer.</p>
          <p class="muted">Source folder: <code>{_e(vault.source_root)}</code></p>
          <form method="get" action="/search" class="searchbar">
            <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
            <input name="q" placeholder="Search topics, weeks, assessments, methods..." />
            <button type="submit">Search</button>
          </form>
          <div class="hero-actions">
            <form method="post" action="/actions/scan-folder"><input type="hidden" name="workspace_id" value="{_e(workspace_id)}" /><button type="submit">Scan Folder</button></form>
            <form method="post" action="/actions/open-wiki-folder"><input type="hidden" name="workspace_id" value="{_e(workspace_id)}" /><button type="submit">Open Generated Wiki Folder</button></form>
          </div>
        </section>
        <section class="stat-grid">
          <article class="stat-card"><span class="stat-value">{len(pages)}</span><span class="stat-label">Generated Pages</span></article>
          <article class="stat-card"><span class="stat-value">{len(categories)}</span><span class="stat-label">Categories</span></article>
          <article class="stat-card"><span class="stat-value">{len(index.get('files', {}))}</span><span class="stat-label">Scanned Files</span></article>
          <article class="stat-card"><span class="stat-value">{len(index.get('warnings', []))}</span><span class="stat-label">Warnings</span></article>
        </section>
        <section class="split">
          <article class="panel">
            <h2>Build Status</h2>
            <div class="item"><strong>Status</strong><p>{_e(vault.last_build_status)}</p></div>
            <div class="item"><strong>Last Scan</strong><p>{_e(vault.last_scan_at or 'never')}</p></div>
            <div class="item"><strong>AI Mode</strong><p>{_e(index.get('ai_status', 'disabled'))}</p></div>
          </article>
          <article class="panel">
            <h2>Popular Tags</h2>
            <div class="pill-row">{tag_cloud}</div>
          </article>
        </section>
        <section class="panel">
          <h2>Categories</h2>
          <div class="category-grid">{category_cards}</div>
        </section>
        <section class="split">
          <article class="panel">
            <h2>Recently Updated</h2>
            {_render_page_list(workspace_id, recent_pages, empty_message="No recent pages yet.")}
          </article>
          <article class="panel">
            <h2>Featured Pages</h2>
            {_render_page_list(workspace_id, featured_pages, empty_message="No featured pages yet.")}
          </article>
        </section>
        {warning_html}
        <section class="panel">
          <h2>Generated Wiki Overview</h2>
          {_wiki_markdown_html(workspace_id, "_index.md", self.ctx.wiki_service.read_page(workspace_id, '_index.md'), index) if pages else '<p class="empty">No wiki generated yet.</p>'}
        </section>
        """
        return _page("Home", body, active="/home", workspace_id=workspace_id)

    def _search_page(self, workspace_id: str, q: str) -> str:
        index = self.ctx.wiki_service.page_index(workspace_id)
        pages = _content_pages(index)
        needle = q.strip().lower()
        if needle:
            results = [
                page for page in pages
                if needle in (page.get("title") or "").lower()
                or needle in (page.get("summary") or "").lower()
                or needle in (page.get("category") or "").lower()
                or any(needle in tag.lower() for tag in page.get("tags", []))
            ]
        else:
            results = []
        result_html = ""
        if needle and not results:
            result_html = "<p class='empty'>No matches.</p>"
        elif results:
            result_html = _render_page_list(workspace_id, results, empty_message="No matches.")
        body = f"""
        <section class="hero">
          <p class="eyebrow">Search</p>
          <h1>Search Wiki</h1>
          <p class="lede">Search across titles, summaries, categories, and tags.</p>
          <form method="get" action="/search" class="stacked">
            <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
            <input name="q" placeholder="Search titles and summaries…" value="{_e(q)}" autofocus />
            <button type="submit">Search</button>
          </form>
        </section>
        <section class="panel">
          <h2>{len(results)} result{'s' if len(results) != 1 else ''}</h2>
          {result_html or "<p class='empty'>Type a query above.</p>"}
        </section>
        """
        return _page("Search", body, active="/search", workspace_id=workspace_id)

    def _knowledge_page(self, workspace_id: str) -> str:
        nodes = self.ctx.compile_service.nodes.list_by_workspace(workspace_id)
        signals = self.ctx.signal_service.signals.list_by_workspace(workspace_id)
        patterns = self.ctx.signal_service.patterns.list_by_workspace(workspace_id)
        postcards = self.ctx.postcard_service.postcards.list_by_workspace(workspace_id)
        body = (
            "<section class='hero'><p class='eyebrow'>Knowledge</p><h1>Compiled Knowledge</h1>"
            f"<p class='lede'>{len(nodes)} nodes · {len(signals)} signals · {len(patterns)} patterns · {len(postcards)} postcards</p>"
            "<div class='subnav'>"
            "<a href='#nodes'>Nodes</a>"
            "<a href='#signals'>Signals</a>"
            "<a href='#patterns'>Patterns</a>"
            "<a href='#postcards'>Postcards</a>"
            "</div></section>"
        )
        body += "<section class='grid'>"
        body += "<article class='panel' id='nodes'><h2>Nodes</h2>" + ("".join(
            f"<div class='item'><strong>{_e(node.title)}</strong><p>{_e(node.summary)}</p></div>" for node in nodes
        ) or "<p class='empty'>No compiled nodes yet.</p>") + "</article>"
        body += "<article class='panel' id='signals'><h2>Capability Signals</h2>" + ("".join(
            f"<div class='item'><strong>{_e(signal.topic)}</strong><p>{_e(signal.observed_practice)}</p></div>" for signal in signals
        ) or "<p class='empty'>No capability signals detected.</p>") + "</article>"
        body += "<article class='panel' id='patterns'><h2>Mistake Patterns</h2>" + ("".join(
            f"<div class='item'><strong>{_e(pattern.topic)}</strong><p>{_e(pattern.description)}</p></div>" for pattern in patterns
        ) or "<p class='empty'>No mistake patterns logged.</p>") + "</article>"
        body += "<article class='panel' id='postcards'><h2>Postcards</h2>" + ("".join(
            f"<div class='item'><strong>{_e(card.title)}</strong><p>{_e(card.card_type.value)}</p></div>" for card in postcards
        ) or "<p class='empty'>No postcards generated.</p>") + "</article>"
        body += "</section>"
        return _page("Knowledge", body, active="/knowledge", workspace_id=workspace_id)

    def _passport_page(self, workspace_id: str) -> str:
        passport = self.ctx.passport_service.passports.get_by_workspace(workspace_id)
        if passport is None:
            body = f"""
            <section class="hero">
              <p class="eyebrow">Passport</p>
              <h1>Passport Snapshot</h1>
              <p class="lede">No Passport has been generated yet.</p>
              <form method="post" action="/actions/generate-passport">
                <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
                <button type="submit">Generate Passport</button>
              </form>
            </section>
            """
            return _page("Passport", body, active="/passport", workspace_id=workspace_id)
        representative = tuple(
            card
            for card in self.ctx.postcard_service.postcards.list_by_workspace(workspace_id)
            if card.id in passport.representative_postcard_ids
        )
        view = self.ctx.passport_service._human_view(passport, representative)
        body = f"""
        <section class="hero">
          <p class="eyebrow">Passport</p>
          <h1>Passport Snapshot</h1>
          <form method="post" action="/actions/generate-passport">
            <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
            <button type="submit">Regenerate Passport</button>
          </form>
        </section>
        <section class="split">
          <article class="panel"><h2>Human View</h2>{_markdown_html(view)}</article>
          <article class="panel"><h2>Machine Manifest</h2><pre>{_e(json.dumps(passport.machine_manifest, indent=2, sort_keys=True))}</pre></article>
        </section>
        """
        return _page("Passport", body, active="/passport", workspace_id=workspace_id)

    def _mount_page(self, workspace_id: str) -> str:
        visas = self.ctx.mount_service.visas.list_by_workspace(workspace_id)
        sessions = [session for visa in visas for session in self.ctx.mount_service.sessions.list_by_visa(visa.id)]
        body = f"""
        <section class="hero">
          <p class="eyebrow">Mount</p>
          <h1>Visas and Sessions</h1>
          <form method="post" action="/actions/issue-default-visa">
            <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
            <button type="submit">Issue Default Passport Visa</button>
          </form>
        </section>
        <section class="grid">
          <article class="panel"><h2>Visa Bundles</h2>{"".join(self._visa_card(visa, workspace_id) for visa in visas) or "<p class='empty'>No visas issued yet.</p>"}</article>
          <article class="panel"><h2>Sessions</h2>{"".join(self._session_card(session, workspace_id) for session in sessions) or "<p class='empty'>No sessions recorded yet.</p>"}</article>
        </section>
        """
        return _page("Mount", body, active="/mount", workspace_id=workspace_id)

    def _inbox_page(self, workspace_id: str) -> str:
        items = self.ctx.inbox_service.list_items(workspace_id=workspace_id)
        body = f"""
        <section class="hero">
          <p class="eyebrow">Inbox</p>
          <h1>Source Intake and Compile Queue</h1>
          <form method="post" action="/actions/import-source" class="stacked">
            <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
            <input name="title" placeholder="Source title" required />
            <input name="origin" placeholder="Origin or filename" />
            <select name="source_type">
              <option value="markdown">Markdown</option>
              <option value="plain_text">Plain text</option>
              <option value="web_page">Web page</option>
              <option value="pdf">PDF text</option>
              <option value="project_document">Project document</option>
            </select>
            <textarea name="content" placeholder="Paste imported content here" required></textarea>
            <button type="submit">Import Source</button>
          </form>
        </section>
        <section class="panel">
          <h2>Inbox Items</h2>
          {"".join(self._inbox_item_card(item) for item in items) or "<p class='empty'>No imports yet — add your first source above.</p>"}
        </section>
        """
        return _page("Inbox", body, active="/inbox", workspace_id=workspace_id)

    def _review_page(self, workspace_id: str) -> str:
        candidates = self.ctx.review_service.candidates.list_all()
        items = []
        for candidate in candidates:
            diff = self.ctx.review_service.read_diff(candidate.id)
            actions = ""
            if candidate.status.value == "pending":
                actions = f"""
                <form method="post" action="/actions/accept-candidate"><input type="hidden" name="candidate_id" value="{_e(candidate.id)}" /><button type="submit">Accept</button></form>
                <form method="post" action="/actions/edit-accept-candidate"><input type="hidden" name="candidate_id" value="{_e(candidate.id)}" /><input name="content_override" placeholder='{{"summary":"Edited"}}' /><button type="submit">Edit + Accept</button></form>
                <form method="post" action="/actions/reject-candidate"><input type="hidden" name="candidate_id" value="{_e(candidate.id)}" /><button type="submit">Reject</button></form>
                """
            items.append(
                f"<div class='item'><strong>{_e(candidate.id)}</strong><p>{_e(candidate.status.value)} -> {_e(candidate.target_object)}</p><pre>{_e(chr(10).join(diff.unified_diff))}</pre>{actions}</div>"
            )
        body = "<section class='hero'><p class='eyebrow'>Review</p><h1>Review Queue</h1></section>"
        body += "<section class='panel'>" + ("".join(items) if items else "<p class='empty'>No candidates waiting for review.</p>") + "</section>"
        return _page("Review", body, active="/review", workspace_id=workspace_id)

    def _settings_page(self, workspace_id: str) -> str:
        workspace = self.ctx.workspace_service.get_workspace(workspace_id)
        gates = self.ctx.operations_service.release_gates(workspace_id)
        vault = self.ctx.wiki_service.get_or_create_vault(workspace_id)
        watch = self.ctx.wiki_watch_service.status(workspace_id)
        body = f"""
        <section class="hero">
          <p class="eyebrow">Settings</p>
          <h1>Wiki Settings</h1>
        </section>
        <section class="grid">
          <article class="panel">
            <h2>Workspace</h2>
            <p>{_e(workspace.title)} ({_e(workspace.workspace_type.value)})</p>
          </article>
          <article class="panel">
            <h2>Vault</h2>
            {self._connect_folder_form(workspace_id, vault)}
          </article>
          <article class="panel">
            <h2>Watch Mode</h2>
            <p>{'running' if watch.running else 'stopped'}</p>
            <form method="post" action="/actions/start-watch"><input type="hidden" name="workspace_id" value="{_e(workspace_id)}" /><button type="submit">Start Watching</button></form>
            <form method="post" action="/actions/stop-watch"><input type="hidden" name="workspace_id" value="{_e(workspace_id)}" /><button type="submit">Stop Watching</button></form>
            <form method="post" action="/actions/rebuild-wiki"><input type="hidden" name="workspace_id" value="{_e(workspace_id)}" /><button type="submit">Rebuild Wiki</button></form>
          </article>
          <article class="panel">
            <h2>Export</h2>
            <form method="post" action="/actions/export-workspace">
              <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
              <button type="submit">Export Workspace</button>
            </form>
            <form method="post" action="/actions/restore-workspace" class="stacked">
              <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
              <input name="path" placeholder="Path to export package" required />
              <button type="submit">Restore Workspace</button>
            </form>
          </article>
          <article class="panel">
            <h2>Policies</h2>
            <p>Read-only first, whitelist-only access, review-controlled writeback.</p>
          </article>
          <article class="panel">
            <h2>Release Gates</h2>
            {"".join(f"<div class='item'><strong>{_e(gate.key)}</strong><p>{'PASS' if gate.passed else 'PENDING'} - {_e(gate.details)}</p></div>" for gate in gates)}
          </article>
          <article class="panel">
            <h2>Advanced</h2>
            <p><a href="/legacy/knowledge?workspace_id={_e(workspace_id)}">Legacy Knowledge</a></p>
            <p><a href="/legacy/passport?workspace_id={_e(workspace_id)}">Legacy Passport</a></p>
            <p><a href="/legacy/mount?workspace_id={_e(workspace_id)}">Legacy Mount</a></p>
            <p><a href="/legacy/review?workspace_id={_e(workspace_id)}">Legacy Review</a></p>
          </article>
        </section>
        """
        return _page("Settings", body, active="/settings", workspace_id=workspace_id)

    def _wiki_category_page(self, workspace_id: str, kind: str, query: dict[str, list[str]]) -> str:
        index = self.ctx.wiki_service.page_index(workspace_id)
        pages = [page for page in _content_pages(index) if page["kind"] == kind]
        selected = _single(query, "page", default=pages[0]["path"] if pages else "")
        content = self.ctx.wiki_service.read_page(workspace_id, selected) if selected else "No pages yet. Scan your folder first."
        title = {
            "source": "Sources",
            "topic": "Topics",
            "project": "Projects",
            "method": "Methods",
            "question": "Questions",
        }[kind]
        selected_page = next((page for page in pages if page["path"] == selected), None)
        tags = sorted(
            {
                tag
                for page in pages
                for tag in page.get("tags", [])
            }
        )[:16]
        meta = ""
        if selected_page is not None:
            meta = (
                "<div class='pill-row'>"
                f"<span class='pill muted'>{_e(selected_page.get('category', 'General'))}</span>"
                f"<span class='pill muted'>{_e(selected_page.get('difficulty', 'Intermediate'))}</span>"
                + "".join(f"<span class='pill muted'>{_e(tag)}</span>" for tag in selected_page.get("tags", [])[:6])
                + "</div>"
            )
        body = f"""
        <section class="hero">
          <p class="eyebrow">{_e(title)}</p>
          <h1>{_e(title)}</h1>
          <p class="lede">{len(pages)} generated {title.lower()} pages.</p>
          <div class="pill-row">{"".join(f"<a class='pill' href='/search?workspace_id={_e(workspace_id)}&q={_e(tag)}'>{_e(tag)}</a>" for tag in tags) or "<span class='pill muted'>No tags yet</span>"}</div>
        </section>
        <section class="split">
          <article class="panel"><h2>{_e(title)} Index</h2>{_render_page_list(workspace_id, pages, empty_message='No generated pages yet.')}</article>
          <article class="panel"><h2>{_e(selected_page['title'] if selected_page else title)}</h2>{meta}{_wiki_markdown_html(workspace_id, selected, content, index)}</article>
        </section>
        """
        return _page(title, body, active=f"/{title.lower()}", workspace_id=workspace_id)

    def _legacy_page(self, workspace_id: str) -> str:
        return _page(
            "Advanced",
            f"""
            <section class="hero">
              <p class="eyebrow">Advanced</p>
              <h1>Legacy Passport Views</h1>
              <p class="lede">These routes are kept for compatibility while the default product is now wiki-first.</p>
            </section>
            <section class="panel">
              <p><a href="/legacy/knowledge?workspace_id={_e(workspace_id)}">Legacy Knowledge</a></p>
              <p><a href="/legacy/passport?workspace_id={_e(workspace_id)}">Legacy Passport</a></p>
              <p><a href="/legacy/mount?workspace_id={_e(workspace_id)}">Legacy Mount</a></p>
              <p><a href="/legacy/review?workspace_id={_e(workspace_id)}">Legacy Review</a></p>
            </section>
            """,
            workspace_id=workspace_id,
        )

    def _connect_folder_form(self, workspace_id: str, vault) -> str:
        source_root = vault.source_root or ""
        return f"""
        <form method="post" action="/actions/connect-folder" class="stacked">
          <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
          <input name="source_root" placeholder="Absolute path to your local source folder" value="{_e(source_root)}" required />
          <input name="wiki_root" placeholder="Optional generated wiki folder path" value="{_e(vault.wiki_root)}" />
          <label><input type="checkbox" name="ai_enabled" {'checked' if vault.ai_enabled else ''}/> Enable optional AI enhancement</label>
          <button type="submit">Connect Folder</button>
        </form>
        """

    def _onboarding_page(self) -> str:
        body = """
        <section class="hero">
          <p class="eyebrow">Wiki Home</p>
          <h1>Create Your Personal Knowledge Wiki</h1>
          <p class="lede">Create a workspace first, then connect a local folder to scan and generate Markdown wiki pages.</p>
        </section>
        <section class="panel">
          <form method="post" action="/actions/create-workspace" class="stacked">
            <input name="title" placeholder="Workspace title" required />
            <select name="workspace_type">
              <option value="personal">Personal</option>
              <option value="project">Project</option>
              <option value="work">Work</option>
            </select>
            <button type="submit">Create Workspace</button>
          </form>
        </section>
        """
        return _page("Home", body)

    @staticmethod
    def _open_folder(path: Path) -> None:
        if shutil.which("open"):
            subprocess.run(["open", str(path)], check=False)
        elif shutil.which("xdg-open"):
            subprocess.run(["xdg-open", str(path)], check=False)

    def _visa_card(self, visa, workspace_id: str) -> str:
        revoke = ""
        if visa.status.value == "active":
            revoke = f"""
            <form method="post" action="/actions/revoke-visa">
              <input type="hidden" name="visa_id" value="{_e(visa.id)}" />
              <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
              <button type="submit">Revoke</button>
            </form>
            """
        start = ""
        if visa.status.value == "active":
            start = f"""
            <form method="post" action="/actions/start-session">
              <input type="hidden" name="visa_id" value="{_e(visa.id)}" />
              <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
              <button type="submit">Start Session</button>
            </form>
            """
        return f"<div class='item'><strong>{_e(visa.id)}</strong><p>{_e(visa.status.value)} / {', '.join(permission.value for permission in visa.permission_levels)}</p>{start}{revoke}</div>"

    def _session_card(self, session, workspace_id: str) -> str:
        end = ""
        if session.status.value == "active":
            end = f"""
            <form method="post" action="/actions/end-session">
              <input type="hidden" name="session_id" value="{_e(session.id)}" />
              <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
              <button type="submit">End Session</button>
            </form>
            """
        return f"<div class='item'><strong>{_e(session.id)}</strong><p>{_e(session.status.value)}</p>{end}</div>"

    def _inbox_item_card(self, item) -> str:
        preview = self.ctx.inbox_service.preview(item.source_id)
        return f"""
        <div class='item'>
          <strong>{_e(item.title)}</strong>
          <p>{_e(item.source_type)} / {_e(item.compile_status.value)}</p>
          <pre>{_e(preview.raw_content[:400])}</pre>
          <form method="post" action="/actions/compile-source">
            <input type="hidden" name="source_id" value="{_e(item.source_id)}" />
            <input type="hidden" name="workspace_id" value="{_e(item.workspace_id)}" />
            <button type="submit">{'Recompile' if item.compile_status.value in ('failed', 'succeeded') else 'Compile'}</button>
          </form>
        </div>
        """

    def _default_workspace_id(self) -> str:
        workspaces = self.ctx.workspace_service.list_workspaces()
        if not workspaces:
            raise KeyError("No workspaces exist")
        return workspaces[0].id

    @staticmethod
    def _json_response(status_code: int, payload: dict[str, object]) -> tuple[str, list[tuple[str, str]], bytes]:
        body = json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")
        return f"{status_code} {'OK' if status_code < 400 else 'ERROR'}", [("Content-Type", "application/json")], body

    @staticmethod
    def _redirect(location: str, start_response=None) -> tuple[str, list[tuple[str, str]], bytes] | list[bytes]:
        response = ("302 Found", [("Location", location)], b"")
        if start_response is None:
            return response
        start_response(response[0], response[1])
        return [response[2]]


def _page(title: str, body: str, active: str = "", workspace_id: str | None = None) -> str:
    links = [
        ("/home", "Home"),
        ("/sources", "Sources"),
        ("/topics", "Topics"),
        ("/projects", "Projects"),
        ("/methods", "Methods"),
        ("/questions", "Questions"),
        ("/search", "Search"),
        ("/settings", "Settings"),
        ("/legacy", "Advanced"),
    ]
    suffix = f"?workspace_id={_e(workspace_id)}" if workspace_id else ""
    nav_items = "".join(
        f'<a href="{href}{suffix}" class="{"active" if href == active else ""}">{label}</a>'
        for href, label in links
    )
    nav = f'<nav class="nav">{nav_items}</nav>'
    style = """
    <style>
      :root { --bg:#f2efe7; --ink:#1f2430; --accent:#8a3b12; --accent-soft:#f3d8c7; --panel:#fffdf8; --line:#d9cbb8; }
      * { box-sizing:border-box; }
      body { margin:0; font-family:Georgia, 'Avenir Next', serif; background:radial-gradient(circle at top left,#fff7ef,transparent 35%),linear-gradient(180deg,#f4efe6,#efe9df); color:var(--ink); }
      .shell { max-width:1200px; margin:0 auto; padding:32px 24px 48px; }
      .nav { display:flex; gap:14px; padding:14px 18px; background:rgba(255,253,248,0.85); border:1px solid var(--line); border-radius:999px; backdrop-filter:blur(10px); position:sticky; top:16px; }
      .nav a { color:var(--ink); text-decoration:none; font-size:14px; letter-spacing:0.04em; text-transform:uppercase; padding:6px 12px; border-radius:999px; transition:background 0.15s, color 0.15s; }
      .nav a:hover { background:var(--accent-soft); }
      .nav a.active { background:var(--accent); color:#fffaf3; }
      .hero { padding:36px 0 20px; }
      .eyebrow { letter-spacing:0.18em; text-transform:uppercase; color:var(--accent); font-size:12px; margin:0 0 10px; }
      h1 { margin:0 0 10px; font-size:48px; line-height:1; }
      .lede { max-width:760px; font-size:18px; line-height:1.5; }
      .muted { color:#7a6a55; }
      .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:18px; }
      .split { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:18px; }
      .stat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin:0 0 18px; }
      .stat-card { background:linear-gradient(180deg,#fffdf8,#f8f1e7); border:1px solid var(--line); border-radius:22px; padding:18px; box-shadow:0 12px 28px rgba(79,50,22,0.08); }
      .stat-value { display:block; font-size:34px; line-height:1; font-weight:700; color:var(--accent); }
      .stat-label { display:block; margin-top:8px; text-transform:uppercase; letter-spacing:0.06em; font-size:12px; color:#7a6a55; }
      .panel { background:var(--panel); border:1px solid var(--line); border-radius:24px; padding:22px; box-shadow:0 18px 48px rgba(79,50,22,0.08); }
      .item { padding:12px 0; border-top:1px solid rgba(0,0,0,0.07); }
      .item:first-child { border-top:none; padding-top:0; }
      .item strong { display:block; margin-bottom:4px; }
      .item p { margin:0; }
      .hero-actions { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
      .searchbar { display:flex; gap:10px; max-width:760px; margin-top:16px; }
      .searchbar input { flex:1; }
      .category-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; }
      .category-card { display:block; text-decoration:none; background:linear-gradient(180deg,rgba(255,253,248,0.95),#f8f1e7); border:1px solid var(--line); border-radius:18px; padding:16px; }
      .category-card strong { display:block; color:var(--ink); margin-bottom:6px; }
      .category-card span { color:#7a6a55; font-size:13px; }
      .pill-row { display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }
      .pill { display:inline-flex; align-items:center; gap:8px; text-decoration:none; border:1px solid var(--line); background:#fffaf3; color:var(--ink); border-radius:999px; padding:7px 12px; font-size:13px; }
      .pill span { color:#7a6a55; font-size:12px; }
      .pill.muted { color:#7a6a55; background:#f8f1e7; }
      button { border:none; border-radius:999px; padding:10px 18px; background:var(--accent); color:white; font-weight:600; cursor:pointer; transition:transform 0.1s ease, box-shadow 0.15s ease, background 0.15s; box-shadow:0 6px 16px rgba(138,59,18,0.18); }
      button:hover { background:#a0481b; transform:translateY(-1px); box-shadow:0 10px 22px rgba(138,59,18,0.24); }
      button:active { transform:translateY(0); box-shadow:0 4px 10px rgba(138,59,18,0.18); }
      .panel { transition:transform 0.15s ease, box-shadow 0.2s ease; }
      .panel:hover { transform:translateY(-2px); box-shadow:0 24px 56px rgba(79,50,22,0.12); }
      .empty { color:#7a6a55; font-style:italic; padding:14px 0; }
      .subnav { display:flex; gap:10px; margin-top:14px; flex-wrap:wrap; }
      .subnav a { padding:6px 14px; border-radius:999px; background:rgba(255,253,248,0.7); border:1px solid var(--line); text-decoration:none; font-size:13px; letter-spacing:0.04em; text-transform:uppercase; color:var(--ink); }
      .subnav a:hover { background:var(--accent-soft); color:var(--accent); }
      .panel:target { outline:2px solid var(--accent); outline-offset:4px; animation:flash 1.2s ease-out; }
      @keyframes flash { 0% { background:var(--accent-soft); } 100% { background:var(--panel); } }
      .flash { background:var(--accent-soft); border:1px solid var(--accent); color:var(--accent); padding:12px 18px; border-radius:14px; margin-bottom:18px; font-weight:600; }
      a { color:var(--accent); }
      a:hover { color:#a0481b; }
      form { display:inline-block; margin-right:8px; margin-top:8px; }
      .stacked { display:grid; gap:10px; max-width:720px; }
      input, select, textarea { width:100%; padding:10px 12px; border:1px solid var(--line); border-radius:14px; background:#fffaf3; font:inherit; }
      textarea { min-height:160px; }
      pre { white-space:pre-wrap; word-break:break-word; background:#f8f1e7; padding:12px; border-radius:16px; font-family:'SFMono-Regular',Menlo,monospace; font-size:12px; }
      @media (max-width: 720px) { h1 { font-size:34px; } .nav { overflow-x:auto; flex-wrap:nowrap; mask-image:linear-gradient(90deg,#000 85%,transparent); -webkit-mask-image:linear-gradient(90deg,#000 85%,transparent); } .nav a { flex:none; } .shell { padding:18px 14px 32px; } .searchbar { flex-direction:column; } }
    </style>
    """
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{_e(title)}</title>{style}</head><body><div class='shell'>{nav}{body}</div></body></html>"


def _content_pages(index: dict[str, object]) -> list[dict[str, object]]:
    return [
        page
        for page in index.get("pages", [])
        if page.get("kind") not in {"index"} and not str(page.get("kind", "")).endswith("_index")
    ]


def _feature_rank(page: dict[str, object]) -> int:
    order = {
        "project": 5,
        "topic": 4,
        "method": 3,
        "question": 2,
        "source": 1,
    }
    return order.get(str(page.get("kind")), 0)


def _route_for_kind(kind: str) -> str:
    routes = {
        "source": "/sources",
        "topic": "/topics",
        "project": "/projects",
        "method": "/methods",
        "question": "/questions",
        "index": "/home",
    }
    if kind.endswith("_index"):
        return routes.get(kind[:-6], "/home")
    return routes.get(kind, "/home")


def _wiki_href(workspace_id: str, page: dict[str, object]) -> str:
    route = _route_for_kind(str(page.get("kind", "index")))
    if route == "/home" and page.get("path") == "_index.md":
        return f"/home?workspace_id={_e(workspace_id)}"
    if route == "/home":
        return f"/home?workspace_id={_e(workspace_id)}"
    if str(page.get("kind", "")).endswith("_index"):
        return f"{route}?workspace_id={_e(workspace_id)}"
    return f"{route}?workspace_id={_e(workspace_id)}&page={_e(page.get('path', ''))}"


def _render_page_list(workspace_id: str, pages: list[dict[str, object]], *, empty_message: str) -> str:
    if not pages:
        return f"<p class='empty'>{_e(empty_message)}</p>"
    rows = []
    for page in pages:
        pills = [
            f"<span class='pill muted'>{_e(page.get('kind', 'page').title())}</span>",
            f"<span class='pill muted'>{_e(page.get('category', 'General'))}</span>",
        ]
        if page.get("difficulty"):
            pills.append(f"<span class='pill muted'>{_e(page['difficulty'])}</span>")
        for tag in page.get("tags", [])[:3]:
            pills.append(f"<span class='pill muted'>{_e(tag)}</span>")
        updated = page.get("updated_at") or "unknown"
        rows.append(
            f"""
            <div class="item">
              <a href="{_wiki_href(workspace_id, page)}"><strong>{_e(page.get('title', 'Untitled'))}</strong></a>
              <p>{_e(page.get('summary', ''))}</p>
              <p class="muted">Updated: {_e(updated)}</p>
              <div class="pill-row">{''.join(pills)}</div>
            </div>
            """
        )
    return "".join(rows)


def _wiki_markdown_html(workspace_id: str, current_path: str, markdown: str, index: dict[str, object]) -> str:
    pages = {str(page.get("path")): page for page in index.get("pages", [])}

    def resolve(href: str) -> str:
        if href.startswith(("http://", "https://", "mailto:", "#", "/")):
            return href
        normalized = posixpath.normpath(posixpath.join(posixpath.dirname(current_path or "_index.md"), href))
        page = pages.get(normalized)
        if page is None:
            return href
        return _wiki_href(workspace_id, page)

    return _markdown_html(markdown, resolve)


def _e(value: object) -> str:
    return html.escape(str(value))


def _markdown_html(markdown: str, link_resolver: Callable[[str], str] | None = None) -> str:
    lines = markdown.splitlines()
    html_lines: list[str] = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        if stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{_e(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{_e(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{_e(stripped[2:])}</h1>")
            continue
        if stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_markdown_inline(stripped[2:], link_resolver)}</li>")
            continue
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        html_lines.append(f"<p>{_markdown_inline(stripped, link_resolver)}</p>")
    if in_list:
        html_lines.append("</ul>")
    return "".join(html_lines)


def _markdown_inline(text: str, link_resolver: Callable[[str], str] | None = None) -> str:
    escaped = _e(text)
    return re_sub_links(escaped, link_resolver)


def re_sub_links(text: str, link_resolver: Callable[[str], str] | None = None) -> str:
    return __import__("re").sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: (
            f"<a href='{_e(link_resolver(html.unescape(match.group(2))) if link_resolver else html.unescape(match.group(2)))}'>"
            f"{_e(html.unescape(match.group(1)))}</a>"
        ),
        text,
    )


def _extract_markdown_links(markdown: str) -> list[str]:
    return [
        html.unescape(match.group(2))
        for match in __import__("re").finditer(r"\[([^\]]+)\]\(([^)]+)\)", markdown)
    ]


def serialize_build_result(result) -> dict[str, object]:
    return {
        "workspace_id": result.workspace_id,
        "generated_at": result.generated_at,
        "scanned_file_count": result.scanned_file_count,
        "changed_file_count": result.changed_file_count,
        "removed_file_count": result.removed_file_count,
        "skipped_files": list(result.skipped_files),
        "warnings": list(result.warnings),
        "ai_status": result.ai_status,
        "home_page": result.home_page,
        "pages": [
            {
                "kind": page.kind,
                "slug": page.slug,
                "title": page.title,
                "relative_path": page.relative_path,
                "source_ids": list(page.source_ids),
                "backlinks": list(page.backlinks),
                "source_refs": list(page.source_refs),
                "summary": page.summary,
            }
            for page in result.pages
        ],
    }


def _read_json(environ: dict[str, object]) -> dict[str, object]:
    body = _read_body(environ)
    return json.loads(body.decode("utf-8") or "{}")


def _read_form(environ: dict[str, object]) -> dict[str, str]:
    body = _read_body(environ).decode("utf-8")
    data = parse_qs(body, keep_blank_values=True)
    return {key: values[0] for key, values in data.items()}


def _read_body(environ: dict[str, object]) -> bytes:
    length = int(str(environ.get("CONTENT_LENGTH") or "0"))
    stream = environ.get("wsgi.input")
    if stream is None:
        return b""
    return stream.read(length) if length > 0 else b""


def _single(query: dict[str, list[str]], key: str, *, default: str | None = None) -> str:
    values = query.get(key)
    if not values:
        if default is None:
            raise ValueError(f"Missing query parameter: {key}")
        return default
    return values[0]


def make_testing_environ(method: str, path: str, body: bytes = b"", query: str = "") -> dict[str, object]:
    return {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
