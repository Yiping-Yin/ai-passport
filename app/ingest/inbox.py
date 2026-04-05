"""Inbox projections and compile trigger behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from app.domain import CompileJob, CompileJobStatus, Source
from app.ingest.service import RawSourceStore
from app.storage.compile_jobs import CompileJobRepository
from app.storage.evidence import EvidenceFragmentRepository
from app.storage.sources import SourceRepository
from app.storage.workspaces import WorkspaceRepository


@dataclass(frozen=True, slots=True)
class InboxItem:
    source_id: str
    title: str
    source_type: str
    workspace_id: str
    workspace_title: str
    imported_at: datetime
    compile_status: CompileJobStatus
    last_error: str | None


@dataclass(frozen=True, slots=True)
class SourcePreview:
    source_id: str
    raw_content: str
    evidence_preview: tuple[str, ...]
    compile_status: CompileJobStatus
    last_error: str | None


class InboxService:
    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
        source_repository: SourceRepository,
        compile_job_repository: CompileJobRepository,
        evidence_repository: EvidenceFragmentRepository,
        raw_store: RawSourceStore,
    ) -> None:
        self.workspaces = workspace_repository
        self.sources = source_repository
        self.jobs = compile_job_repository
        self.evidence = evidence_repository
        self.raw_store = raw_store

    def list_items(self, *, workspace_id: str | None = None) -> tuple[InboxItem, ...]:
        workspaces = (
            (self.workspaces.get(workspace_id),)
            if workspace_id is not None
            else self.workspaces.list()
        )
        items: list[InboxItem] = []
        for workspace in workspaces:
            if workspace is None:
                continue
            for source in self.sources.list_by_workspace(workspace.id):
                latest_job = self.jobs.latest_for_source(source.id)
                compile_status = latest_job.status if latest_job else CompileJobStatus.NOT_STARTED
                items.append(
                    InboxItem(
                        source_id=source.id,
                        title=source.title,
                        source_type=source.source_type.value,
                        workspace_id=workspace.id,
                        workspace_title=workspace.title,
                        imported_at=source.imported_at,
                        compile_status=compile_status,
                        last_error=latest_job.last_error if latest_job else None,
                    )
                )
        return tuple(sorted(items, key=lambda item: item.imported_at))

    def queue_compile(self, source_id: str, *, requested_at: datetime) -> CompileJob:
        source = self._get_source(source_id)
        latest = self.jobs.latest_for_source(source_id)
        attempt_number = 1 if latest is None else latest.attempt_number + 1
        job = CompileJob(
            id=f"job-{uuid4().hex[:12]}",
            source_id=source.id,
            workspace_id=source.workspace_id,
            status=CompileJobStatus.QUEUED,
            requested_at=requested_at,
            attempt_number=attempt_number,
        )
        return self.jobs.create(job)

    def recompile(self, source_id: str, *, requested_at: datetime) -> CompileJob:
        self._get_source(source_id)
        return self.queue_compile(source_id, requested_at=requested_at)

    def mark_running(self, job_id: str, *, now: datetime) -> CompileJob:
        return self.jobs.update_status(job_id, status=CompileJobStatus.RUNNING, now=now)

    def mark_succeeded(self, job_id: str, *, now: datetime) -> CompileJob:
        return self.jobs.update_status(job_id, status=CompileJobStatus.SUCCEEDED, now=now)

    def mark_failed(self, job_id: str, *, now: datetime, last_error: str) -> CompileJob:
        return self.jobs.update_status(job_id, status=CompileJobStatus.FAILED, now=now, last_error=last_error)

    def preview(self, source_id: str) -> SourcePreview:
        source = self._get_source(source_id)
        latest_job = self.jobs.latest_for_source(source_id)
        compile_status = latest_job.status if latest_job else CompileJobStatus.NOT_STARTED
        evidence_preview = tuple(fragment.excerpt for fragment in self.evidence.list_for_source(source_id))
        return SourcePreview(
            source_id=source.id,
            raw_content=self.raw_store.read_raw_source(source.raw_blob_ref),
            evidence_preview=evidence_preview,
            compile_status=compile_status,
            last_error=latest_job.last_error if latest_job else None,
        )

    def _get_source(self, source_id: str) -> Source:
        source = self.sources.get(source_id)
        if source is None:
            raise KeyError(f"Unknown source: {source_id}")
        return source
