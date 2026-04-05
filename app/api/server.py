"""Minimal local API and operator UI for the AI Knowledge Passport MVP."""

from __future__ import annotations

import html
import io
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs

from app.api.workspaces import ActiveWorkspaceState, WorkspaceAPI, WorkspaceService
from app.compile.review import KnowledgeNodeReviewService
from app.compile.service import KnowledgeCompileService
from app.domain import (
    CandidateType,
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
                return self._redirect("/dashboard", start_response)
            if path.startswith("/api/"):
                status, headers, body = self._handle_api(method, path, query, environ)
            else:
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
        if method == "POST" and path == "/api/mount-sessions":
            data = _read_json(environ)
            session = self.ctx.mount_service.start_session(
                data["visa_id"],
                client_type=data["client_type"],
                started_at=datetime.fromisoformat(data["started_at"]),
            )
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
        raise KeyError(path)

    def _handle_ui(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        environ: dict[str, object],
    ) -> tuple[str, list[tuple[str, str]], bytes]:
        if method == "POST":
            return self._handle_ui_action(path, query, environ)
        workspace_id = _single(query, "workspace_id", default=self._default_workspace_id())
        if path == "/dashboard":
            html_body = self._dashboard_page(workspace_id)
        elif path == "/inbox":
            html_body = self._inbox_page(workspace_id)
        elif path == "/knowledge":
            html_body = self._knowledge_page(workspace_id)
        elif path == "/passport":
            html_body = self._passport_page(workspace_id)
        elif path == "/mount":
            html_body = self._mount_page(workspace_id)
        elif path == "/review":
            html_body = self._review_page()
        elif path == "/settings":
            html_body = self._settings_page(workspace_id)
        else:
            raise KeyError(path)
        return "200 OK", [("Content-Type", "text/html; charset=utf-8")], html_body.encode("utf-8")

    def _handle_ui_action(
        self,
        path: str,
        query: dict[str, list[str]],
        environ: dict[str, object],
    ) -> tuple[str, list[tuple[str, str]], bytes]:
        data = _read_form(environ)
        workspace_id = data.get("workspace_id") or self._default_workspace_id()
        if path == "/actions/generate-passport":
            self.ctx.passport_service.generate_for_workspace(workspace_id, recorded_at=utc_now())
            return self._redirect(f"/passport?workspace_id={workspace_id}")
        if path == "/actions/issue-default-visa":
            self.ctx.mount_service.issue_default_passport_visa(workspace_id, expiry_at=utc_now() + timedelta(hours=1))
            return self._redirect(f"/mount?workspace_id={workspace_id}")
        if path == "/actions/revoke-visa":
            self.ctx.mount_service.revoke_visa(data["visa_id"], actor="operator")
            return self._redirect(f"/mount?workspace_id={workspace_id}")
        if path == "/actions/accept-candidate":
            self.ctx.review_service.accept_candidate(data["candidate_id"], actor="operator")
            return self._redirect("/review")
        if path == "/actions/reject-candidate":
            self.ctx.review_service.reject_candidate(data["candidate_id"], actor="operator")
            return self._redirect("/review")
        if path == "/actions/export-workspace":
            self.ctx.export_restore_service.export_workspace(workspace_id, include_hidden=False)
            return self._redirect(f"/settings?workspace_id={workspace_id}")
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
            return self._redirect(f"/inbox?workspace_id={workspace_id}")
        if path == "/actions/compile-source":
            self.ctx.compile_service.compile_source(data["source_id"], requested_at=utc_now())
            return self._redirect(f"/inbox?workspace_id={workspace_id}")
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
        return _page("Dashboard", body)

    def _knowledge_page(self, workspace_id: str) -> str:
        nodes = self.ctx.compile_service.nodes.list_by_workspace(workspace_id)
        signals = self.ctx.signal_service.generate_for_workspace(workspace_id).capability_signals
        patterns = self.ctx.signal_service.generate_for_workspace(workspace_id).mistake_patterns
        postcards = self.ctx.postcard_service.generate_for_workspace(workspace_id, recorded_at=utc_now())
        body = "<section class='hero'><p class='eyebrow'>Knowledge</p><h1>Compiled Knowledge</h1></section>"
        body += "<section class='grid'>"
        body += "<article class='panel'><h2>Nodes</h2>" + "".join(
            f"<div class='item'><strong>{_e(node.title)}</strong><p>{_e(node.summary)}</p></div>" for node in nodes
        ) + "</article>"
        body += "<article class='panel'><h2>Capability Signals</h2>" + "".join(
            f"<div class='item'><strong>{_e(signal.topic)}</strong><p>{_e(signal.observed_practice)}</p></div>" for signal in signals
        ) + "</article>"
        body += "<article class='panel'><h2>Mistake Patterns</h2>" + "".join(
            f"<div class='item'><strong>{_e(pattern.topic)}</strong><p>{_e(pattern.description)}</p></div>" for pattern in patterns
        ) + "</article>"
        body += "<article class='panel'><h2>Postcards</h2>" + "".join(
            f"<div class='item'><strong>{_e(card.title)}</strong><p>{_e(card.card_type.value)}</p></div>" for card in postcards
        ) + "</article>"
        body += "</section>"
        return _page("Knowledge", body)

    def _passport_page(self, workspace_id: str) -> str:
        view = self.ctx.passport_service.generate_for_workspace(workspace_id, recorded_at=utc_now())
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
          <article class="panel"><h2>Human View</h2><pre>{_e(view.human_markdown)}</pre></article>
          <article class="panel"><h2>Machine Manifest</h2><pre>{_e(json.dumps(view.machine_manifest, indent=2, sort_keys=True))}</pre></article>
        </section>
        """
        return _page("Passport", body)

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
          <article class="panel"><h2>Visa Bundles</h2>{"".join(self._visa_card(visa, workspace_id) for visa in visas) or "<p>No visas yet.</p>"}</article>
          <article class="panel"><h2>Sessions</h2>{"".join(f"<div class='item'><strong>{_e(session.id)}</strong><p>{_e(session.status.value)}</p></div>" for session in sessions) or "<p>No sessions yet.</p>"}</article>
        </section>
        """
        return _page("Mount", body)

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
          {"".join(self._inbox_item_card(item) for item in items) or "<p>No imports yet.</p>"}
        </section>
        """
        return _page("Inbox", body)

    def _review_page(self) -> str:
        candidates = self.ctx.review_service.candidates.list_all()
        items = []
        for candidate in candidates:
            diff = self.ctx.review_service.read_diff(candidate.id)
            actions = ""
            if candidate.status.value == "pending":
                actions = f"""
                <form method="post" action="/actions/accept-candidate"><input type="hidden" name="candidate_id" value="{_e(candidate.id)}" /><button type="submit">Accept</button></form>
                <form method="post" action="/actions/reject-candidate"><input type="hidden" name="candidate_id" value="{_e(candidate.id)}" /><button type="submit">Reject</button></form>
                """
            items.append(
                f"<div class='item'><strong>{_e(candidate.id)}</strong><p>{_e(candidate.status.value)} -> {_e(candidate.target_object)}</p><pre>{_e(chr(10).join(diff.unified_diff))}</pre>{actions}</div>"
            )
        body = "<section class='hero'><p class='eyebrow'>Review</p><h1>Review Queue</h1></section>"
        body += "<section class='panel'>" + ("".join(items) if items else "<p>No candidates.</p>") + "</section>"
        return _page("Review", body)

    def _settings_page(self, workspace_id: str) -> str:
        workspace = self.ctx.workspace_service.get_workspace(workspace_id)
        gates = self.ctx.operations_service.release_gates(workspace_id)
        body = f"""
        <section class="hero">
          <p class="eyebrow">Settings</p>
          <h1>Workspace Controls</h1>
        </section>
        <section class="grid">
          <article class="panel">
            <h2>Workspace</h2>
            <p>{_e(workspace.title)} ({_e(workspace.workspace_type.value)})</p>
          </article>
          <article class="panel">
            <h2>Export</h2>
            <form method="post" action="/actions/export-workspace">
              <input type="hidden" name="workspace_id" value="{_e(workspace_id)}" />
              <button type="submit">Export Workspace</button>
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
        </section>
        """
        return _page("Settings", body)

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
        return f"<div class='item'><strong>{_e(visa.id)}</strong><p>{_e(visa.status.value)} / {', '.join(permission.value for permission in visa.permission_levels)}</p>{revoke}</div>"

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


def _page(title: str, body: str) -> str:
    nav = """
    <nav class="nav">
      <a href="/dashboard">Dashboard</a>
      <a href="/inbox">Inbox</a>
      <a href="/knowledge">Knowledge</a>
      <a href="/passport">Passport</a>
      <a href="/mount">Mount</a>
      <a href="/review">Review</a>
      <a href="/settings">Settings</a>
    </nav>
    """
    style = """
    <style>
      :root { --bg:#f2efe7; --ink:#1f2430; --accent:#8a3b12; --accent-soft:#f3d8c7; --panel:#fffdf8; --line:#d9cbb8; }
      * { box-sizing:border-box; }
      body { margin:0; font-family:Georgia, 'Avenir Next', serif; background:radial-gradient(circle at top left,#fff7ef,transparent 35%),linear-gradient(180deg,#f4efe6,#efe9df); color:var(--ink); }
      .shell { max-width:1200px; margin:0 auto; padding:32px 24px 48px; }
      .nav { display:flex; gap:14px; padding:14px 18px; background:rgba(255,253,248,0.85); border:1px solid var(--line); border-radius:999px; backdrop-filter:blur(10px); position:sticky; top:16px; }
      .nav a { color:var(--ink); text-decoration:none; font-size:14px; letter-spacing:0.04em; text-transform:uppercase; }
      .hero { padding:36px 0 20px; }
      .eyebrow { letter-spacing:0.18em; text-transform:uppercase; color:var(--accent); font-size:12px; margin:0 0 10px; }
      h1 { margin:0 0 10px; font-size:48px; line-height:1; }
      .lede { max-width:760px; font-size:18px; line-height:1.5; }
      .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:18px; }
      .split { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:18px; }
      .panel { background:var(--panel); border:1px solid var(--line); border-radius:24px; padding:22px; box-shadow:0 18px 48px rgba(79,50,22,0.08); }
      .item { padding:12px 0; border-top:1px solid rgba(0,0,0,0.07); }
      .item:first-child { border-top:none; padding-top:0; }
      button { border:none; border-radius:999px; padding:10px 16px; background:var(--accent); color:white; font-weight:600; cursor:pointer; }
      form { display:inline-block; margin-right:8px; margin-top:8px; }
      .stacked { display:grid; gap:10px; max-width:720px; }
      input, select, textarea { width:100%; padding:10px 12px; border:1px solid var(--line); border-radius:14px; background:#fffaf3; font:inherit; }
      textarea { min-height:160px; }
      pre { white-space:pre-wrap; word-break:break-word; background:#f8f1e7; padding:12px; border-radius:16px; font-family:'SFMono-Regular',Menlo,monospace; font-size:12px; }
      @media (max-width: 720px) { h1 { font-size:34px; } .nav { overflow:auto; } }
    </style>
    """
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{_e(title)}</title>{style}</head><body><div class='shell'>{nav}{body}</div></body></html>"


def _e(value: object) -> str:
    return html.escape(str(value))


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
