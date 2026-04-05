"""Mount session persistence helpers."""

from __future__ import annotations

import sqlite3

from app.domain import MountSession
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("mount_sessions", {key: row[key] for key in row.keys()})


class MountSessionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, session: MountSession) -> MountSession:
        payload = encode_record("mount_sessions", mount_session_to_record(session))
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT INTO mount_sessions ({columns}) VALUES ({placeholders})",
            payload,
        )
        self.connection.commit()
        return session

    def get(self, session_id: str) -> MountSession | None:
        row = self.connection.execute(
            "SELECT * FROM mount_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(MountSession, _row_to_payload(row))

    def list_by_visa(self, visa_id: str) -> tuple[MountSession, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM mount_sessions
            WHERE visa_id = ?
            ORDER BY started_at DESC
            """,
            (visa_id,),
        ).fetchall()
        return tuple(deserialize_entity(MountSession, _row_to_payload(row)) for row in rows)

    def update(self, session: MountSession) -> MountSession:
        payload = encode_record("mount_sessions", mount_session_to_record(session))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE mount_sessions SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return session


def mount_session_to_record(session: MountSession) -> dict[str, object]:
    return {
        "id": session.id,
        "client_type": session.client_type,
        "visa_id": session.visa_id,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "actions": list(session.actions),
        "writeback_count": session.writeback_count,
        "status": session.status.value,
    }
