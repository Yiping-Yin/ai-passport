#!/usr/bin/env python3
"""Run one end-to-end pilot flow against a local database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.server import build_context
from app.domain import CandidateType, PermissionLevel, SourceType, WorkspaceType
from app.ingest.service import SourceImportRequest
from app.review.ops import OperationsService


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


def main() -> int:
    now = datetime.now(UTC).replace(tzinfo=None)
    context = build_context()
    workspace = context.workspace_service.create_workspace(
        workspace_type=WorkspaceType.PERSONAL,
        title="Pilot Workspace",
        now=now,
    )
    source = context.source_import_service.import_source(
        SourceImportRequest(
            workspace_id=workspace.id,
            source_type=SourceType.MARKDOWN,
            title="Pilot Source",
            origin="pilot.md",
            content=FIXTURE,
            imported_at=now + timedelta(minutes=1),
        )
    )
    context.focus_service.create_focus_card(
        workspace_id=workspace.id,
        title="Pilot focus",
        goal="Validate the full MVP loop",
        timeframe="this session",
        priority=1,
        success_criteria=("Passport generated", "Review action completed", "Export restored"),
        related_topics=("Python Typing",),
    )
    context.compile_service.compile_source(source.id, requested_at=now + timedelta(minutes=2))
    passport = context.passport_service.generate_for_workspace(workspace.id, recorded_at=now + timedelta(minutes=3)).passport
    visa = context.mount_service.issue_visa(
        workspace_id=workspace.id,
        included_postcards=tuple(card.id for card in context.postcard_service.representative_postcards(workspace.id)),
        included_nodes=tuple(node.id for node in context.compile_service.nodes.list_by_workspace(workspace.id)),
        permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.TOPIC_READ, PermissionLevel.WRITEBACK_CANDIDATE),
        expiry_at=now + timedelta(hours=1),
    )
    session = context.mount_service.start_session(visa.id, client_type="gpt", started_at=now + timedelta(minutes=4))
    context.mount_service.read_passport_manifest(session.id)
    candidate = context.review_service.create_candidate(
        session_id=session.id,
        candidate_type=CandidateType.SUMMARY,
        target_object=f"knowledge_node:{context.compile_service.nodes.list_by_workspace(workspace.id)[0].id}",
        content={"summary": "Pilot review candidate summary"},
    )
    context.review_service.accept_candidate(candidate.id, actor="pilot")
    export_path = context.export_restore_service.export_workspace(workspace.id, include_hidden=False)
    context.export_restore_service.restore_workspace(export_path)
    ops = OperationsService(
        workspace_repository=context.workspace_service.workspaces,
        source_repository=context.workspace_service.sources,
        passport_service=context.passport_service,
        postcard_service=context.postcard_service,
        visa_repository=context.mount_service.visas,
        session_repository=context.mount_service.sessions,
        candidate_repository=context.review_service.candidates,
        audit_repository=context.mount_service.audit,
    )

    print(f"workspace: {workspace.id}")
    print(f"passport: {passport.id}")
    print(f"session: {session.id}")
    print(f"candidate: {candidate.id}")
    print(f"export: {export_path}")
    print("metrics:")
    for key, value in ops.metrics(workspace.id).items():
        print(f"  {key}: {value}")
    print("release_gates:")
    for gate in ops.release_gates(workspace.id):
        print(f"  {gate.key}: {'PASS' if gate.passed else 'PENDING'} - {gate.details}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
