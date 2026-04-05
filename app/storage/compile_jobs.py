"""Compile job persistence helpers."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from app.domain import CompileJob, CompileJobStatus
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return {key: row[key] for key in row.keys()}


class CompileJobRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, job: CompileJob) -> CompileJob:
        payload = encode_record("compile_jobs", compile_job_to_record(job))
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT INTO compile_jobs ({columns}) VALUES ({placeholders})",
            payload,
        )
        self.connection.commit()
        return job

    def latest_for_source(self, source_id: str) -> CompileJob | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM compile_jobs
            WHERE source_id = ?
            ORDER BY requested_at DESC, attempt_number DESC
            LIMIT 1
            """,
            (source_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(CompileJob, _row_to_payload(row))

    def list_for_workspace(self, workspace_id: str) -> tuple[CompileJob, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM compile_jobs
            WHERE workspace_id = ?
            ORDER BY requested_at DESC, attempt_number DESC
            """,
            (workspace_id,),
        ).fetchall()
        return tuple(deserialize_entity(CompileJob, _row_to_payload(row)) for row in rows)

    def update_status(
        self,
        job_id: str,
        *,
        status: CompileJobStatus,
        now: datetime,
        last_error: str | None = None,
    ) -> CompileJob:
        current = self.get(job_id)
        if current is None:
            raise KeyError(f"Unknown compile job: {job_id}")
        started_at = current.started_at
        finished_at = current.finished_at
        if status is CompileJobStatus.RUNNING and started_at is None:
            started_at = now
        if status in (CompileJobStatus.SUCCEEDED, CompileJobStatus.FAILED):
            finished_at = now
            if started_at is None:
                started_at = now
        updated = CompileJob(
            id=current.id,
            source_id=current.source_id,
            workspace_id=current.workspace_id,
            status=status,
            requested_at=current.requested_at,
            started_at=started_at,
            finished_at=finished_at,
            last_error=last_error if status is CompileJobStatus.FAILED else None,
            attempt_number=current.attempt_number,
        )
        payload = encode_record("compile_jobs", compile_job_to_record(updated))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE compile_jobs SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return updated

    def get(self, job_id: str) -> CompileJob | None:
        row = self.connection.execute(
            "SELECT * FROM compile_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(CompileJob, _row_to_payload(row))


def compile_job_to_record(job: CompileJob) -> dict[str, object]:
    return {
        "id": job.id,
        "source_id": job.source_id,
        "workspace_id": job.workspace_id,
        "status": job.status.value,
        "requested_at": job.requested_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "last_error": job.last_error,
        "attempt_number": job.attempt_number,
    }
