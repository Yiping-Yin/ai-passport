"""Mistake pattern persistence helpers."""

from __future__ import annotations

import sqlite3

from app.domain import InsightDisposition, MistakePattern, PrivacyLevel
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("mistake_patterns", {key: row[key] for key in row.keys()})


class MistakePatternRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_by_workspace(self, workspace_id: str) -> tuple[MistakePattern, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM mistake_patterns
            WHERE workspace_id = ?
            ORDER BY topic ASC, id ASC
            """,
            (workspace_id,),
        ).fetchall()
        return tuple(deserialize_entity(MistakePattern, _row_to_payload(row)) for row in rows)

    def get(self, pattern_id: str) -> MistakePattern | None:
        row = self.connection.execute(
            "SELECT * FROM mistake_patterns WHERE id = ?",
            (pattern_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(MistakePattern, _row_to_payload(row))

    def upsert(self, pattern: MistakePattern) -> MistakePattern:
        current = self.get(pattern.id)
        if current is None:
            payload = encode_record("mistake_patterns", mistake_pattern_to_record(pattern))
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(f":{key}" for key in payload)
            self.connection.execute(
                f"INSERT INTO mistake_patterns ({columns}) VALUES ({placeholders})",
                payload,
            )
            self.connection.commit()
            return pattern
        if _snapshot(current) == _snapshot(pattern):
            return current
        updated = MistakePattern(
            id=current.id,
            topic=pattern.topic,
            description=pattern.description,
            evidence_ids=pattern.evidence_ids,
            examples=pattern.examples,
            fix_suggestions=pattern.fix_suggestions,
            recurrence_count=pattern.recurrence_count,
            workspace_id=pattern.workspace_id,
            version=current.version + 1,
            disposition=current.disposition,
            visibility=current.visibility,
        )
        payload = encode_record("mistake_patterns", mistake_pattern_to_record(updated))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE mistake_patterns SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return updated

    def set_controls(
        self,
        pattern_id: str,
        *,
        visibility: PrivacyLevel | None = None,
        disposition: InsightDisposition | None = None,
    ) -> MistakePattern:
        current = self.get(pattern_id)
        if current is None:
            raise KeyError(f"Unknown mistake pattern: {pattern_id}")
        updated = MistakePattern(
            id=current.id,
            topic=current.topic,
            description=current.description,
            evidence_ids=current.evidence_ids,
            examples=current.examples,
            fix_suggestions=current.fix_suggestions,
            recurrence_count=current.recurrence_count,
            workspace_id=current.workspace_id,
            version=current.version,
            disposition=disposition if disposition is not None else current.disposition,
            visibility=visibility if visibility is not None else current.visibility,
        )
        payload = encode_record("mistake_patterns", mistake_pattern_to_record(updated))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE mistake_patterns SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return updated


def mistake_pattern_to_record(pattern: MistakePattern) -> dict[str, object]:
    return {
        "id": pattern.id,
        "topic": pattern.topic,
        "description": pattern.description,
        "evidence_ids": list(pattern.evidence_ids),
        "examples": list(pattern.examples),
        "fix_suggestions": list(pattern.fix_suggestions),
        "recurrence_count": pattern.recurrence_count,
        "workspace_id": pattern.workspace_id,
        "version": pattern.version,
        "disposition": pattern.disposition.value,
        "visibility": pattern.visibility.value,
    }


def _snapshot(pattern: MistakePattern) -> tuple[object, ...]:
    return (
        pattern.topic,
        pattern.description,
        pattern.evidence_ids,
        pattern.examples,
        pattern.fix_suggestions,
        pattern.recurrence_count,
        pattern.workspace_id,
    )
