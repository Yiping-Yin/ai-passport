from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.api.server import build_context
from app.domain import CandidateType, PermissionLevel, SourceType, WorkspaceType
from app.ingest.service import SourceImportRequest
from app.review.ops import OperationsService


NOW = datetime(2026, 4, 7, 12, 0, 0)
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


class OperationsTests(unittest.TestCase):
    def test_metrics_and_release_gates_reflect_workspace_state(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context = build_context(
                db_path=root / "ops.sqlite3",
                raw_root=root / "raw",
                export_root=root / "exports",
                review_root=root / "review",
            )
            try:
                workspace = context.workspace_service.create_workspace(
                    workspace_type=WorkspaceType.PERSONAL,
                    title="Ops",
                    now=NOW,
                )
                source = context.source_import_service.import_source(
                    SourceImportRequest(
                        workspace_id=workspace.id,
                        source_type=SourceType.MARKDOWN,
                        title="Ops Fixture",
                        origin="ops.md",
                        content=FIXTURE,
                        imported_at=NOW + timedelta(minutes=1),
                    )
                )
                context.focus_service.create_focus_card(
                    workspace_id=workspace.id,
                    title="Ops focus",
                    goal="Validate gates",
                    timeframe="today",
                    priority=1,
                    success_criteria=("gates visible",),
                    related_topics=("Python Typing",),
                )
                context.compile_service.compile_source(source.id, requested_at=NOW + timedelta(minutes=2))
                context.passport_service.generate_for_workspace(workspace.id, recorded_at=NOW + timedelta(minutes=3))
                visa = context.mount_service.issue_visa(
                    workspace_id=workspace.id,
                    included_postcards=tuple(card.id for card in context.postcard_service.representative_postcards(workspace.id)),
                    included_nodes=tuple(node.id for node in context.compile_service.nodes.list_by_workspace(workspace.id)),
                    permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.TOPIC_READ, PermissionLevel.WRITEBACK_CANDIDATE),
                    expiry_at=NOW + timedelta(hours=1),
                )
                session = context.mount_service.start_session(visa.id, client_type="gpt", started_at=NOW + timedelta(minutes=4))
                candidate = context.review_service.create_candidate(
                    session_id=session.id,
                    candidate_type=CandidateType.SUMMARY,
                    target_object=f"knowledge_node:{context.compile_service.nodes.list_by_workspace(workspace.id)[0].id}",
                    content={"summary": "Ops summary"},
                )
                context.review_service.accept_candidate(candidate.id, actor="ops")
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
                metrics = ops.metrics(workspace.id)
                gates = {gate.key: gate for gate in ops.release_gates(workspace.id)}

                self.assertEqual(metrics["passport_readiness"], "ready")
                self.assertGreaterEqual(metrics["representative_postcard_count"], 3)
                self.assertGreaterEqual(metrics["review_candidate_acceptance_rate"], 1.0)
                self.assertTrue(gates["end_to_end_flow"].passed)
                self.assertTrue(gates["review_queue"].passed)
                self.assertTrue(gates["export_restore"].passed)
                self.assertFalse(gates["pilot_feedback"].passed)
            finally:
                context.connection.close()
