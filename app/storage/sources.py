"""Source persistence helpers."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from app.domain import PrivacyLevel, Source, SourceType
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("sources", {key: row[key] for key in row.keys()})


class SourceRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, source: Source) -> Source:
        payload = encode_record("sources", source_to_record(source))
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT INTO sources ({columns}) VALUES ({placeholders})",
            payload,
        )
        self.connection.commit()
        return source

    def list_by_workspace(self, workspace_id: str) -> tuple[Source, ...]:
        rows = self.connection.execute(
            "SELECT * FROM sources WHERE workspace_id = ? ORDER BY imported_at ASC",
            (workspace_id,),
        ).fetchall()
        return tuple(deserialize_entity(Source, _row_to_payload(row)) for row in rows)

    def get(self, source_id: str) -> Source | None:
        row = self.connection.execute(
            "SELECT * FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(Source, _row_to_payload(row))

    def count_by_workspace(self, workspace_id: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM sources WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        return int(row[0])


def source_to_record(source: Source) -> dict[str, object]:
    return {
        "id": source.id,
        "source_type": source.source_type.value,
        "title": source.title,
        "origin": source.origin,
        "imported_at": source.imported_at.isoformat(),
        "workspace_id": source.workspace_id,
        "privacy_level": source.privacy_level.value,
        "raw_blob_ref": source.raw_blob_ref,
        "tags": list(source.tags),
    }


def create_source(
    *,
    source_id: str,
    source_type: SourceType,
    title: str,
    origin: str,
    imported_at: datetime,
    workspace_id: str,
    raw_blob_ref: str,
    privacy_level: PrivacyLevel = PrivacyLevel.PRIVATE,
    tags: tuple[str, ...] = (),
) -> Source:
    return Source(
        id=source_id,
        source_type=source_type,
        title=title,
        origin=origin,
        imported_at=imported_at,
        workspace_id=workspace_id,
        privacy_level=privacy_level,
        raw_blob_ref=raw_blob_ref,
        tags=tags,
    )
