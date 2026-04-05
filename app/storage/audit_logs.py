"""Audit log persistence helpers."""

from __future__ import annotations

import sqlite3

from app.domain import AuditLog
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("audit_logs", {key: row[key] for key in row.keys()})


class AuditLogRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def append(self, event: AuditLog) -> AuditLog:
        payload = encode_record(
            "audit_logs",
            {
                "id": event.id,
                "actor": event.actor,
                "action": event.action,
                "object_id": event.object_id,
                "timestamp": event.timestamp.isoformat(),
                "result": event.result,
                "meta": event.meta,
            },
        )
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT INTO audit_logs ({columns}) VALUES ({placeholders})",
            payload,
        )
        self.connection.commit()
        return event

    def list_all(self) -> tuple[AuditLog, ...]:
        rows = self.connection.execute(
            "SELECT * FROM audit_logs ORDER BY timestamp ASC"
        ).fetchall()
        return tuple(deserialize_entity(AuditLog, _row_to_payload(row)) for row in rows)
