"""Workspace persistence helpers."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from app.domain import PassportReadiness, PrivacyLevel, Workspace, WorkspaceType
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return {key: row[key] for key in row.keys()}


class WorkspaceRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, workspace: Workspace) -> Workspace:
        payload = encode_record("workspaces", workspace_to_record(workspace))
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT INTO workspaces ({columns}) VALUES ({placeholders})",
            payload,
        )
        self.connection.commit()
        return workspace

    def list(self, *, include_archived: bool = False) -> tuple[Workspace, ...]:
        query = "SELECT * FROM workspaces"
        if not include_archived:
            query += " WHERE archived_at IS NULL"
        query += " ORDER BY created_at ASC"
        rows = self.connection.execute(query).fetchall()
        return tuple(deserialize_entity(Workspace, _row_to_payload(row)) for row in rows)

    def get(self, workspace_id: str) -> Workspace | None:
        row = self.connection.execute(
            "SELECT * FROM workspaces WHERE id = ?",
            (workspace_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(Workspace, _row_to_payload(row))

    def update(self, workspace: Workspace) -> Workspace:
        payload = encode_record("workspaces", workspace_to_record(workspace))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE workspaces SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return workspace

    def archive(self, workspace_id: str, archived_at: datetime) -> Workspace:
        workspace = self.get(workspace_id)
        if workspace is None:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        archived = Workspace(
            id=workspace.id,
            workspace_type=workspace.workspace_type,
            title=workspace.title,
            created_at=workspace.created_at,
            updated_at=archived_at,
            description=workspace.description,
            tags=workspace.tags,
            privacy_default=workspace.privacy_default,
            passport_readiness=workspace.passport_readiness,
            archived_at=archived_at,
        )
        return self.update(archived)


def workspace_to_record(workspace: Workspace) -> dict[str, object]:
    return {
        "id": workspace.id,
        "workspace_type": workspace.workspace_type.value,
        "title": workspace.title,
        "description": workspace.description,
        "created_at": workspace.created_at.isoformat(),
        "updated_at": workspace.updated_at.isoformat(),
        "tags": list(workspace.tags),
        "privacy_default": workspace.privacy_default.value,
        "passport_readiness": workspace.passport_readiness.value,
        "archived_at": workspace.archived_at.isoformat() if workspace.archived_at else None,
    }


def create_workspace(
    *,
    workspace_id: str,
    workspace_type: WorkspaceType,
    title: str,
    now: datetime,
    description: str | None = None,
    tags: tuple[str, ...] = (),
    privacy_default: PrivacyLevel = PrivacyLevel.PRIVATE,
    passport_readiness: PassportReadiness = PassportReadiness.NOT_STARTED,
) -> Workspace:
    return Workspace(
        id=workspace_id,
        workspace_type=workspace_type,
        title=title,
        created_at=now,
        updated_at=now,
        description=description,
        tags=tags,
        privacy_default=privacy_default,
        passport_readiness=passport_readiness,
    )
