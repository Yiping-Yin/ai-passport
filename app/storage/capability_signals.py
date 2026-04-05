"""Capability signal persistence helpers."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from app.domain import CapabilitySignal, InsightDisposition, PrivacyLevel
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("capability_signals", {key: row[key] for key in row.keys()})


class CapabilitySignalRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_by_workspace(self, workspace_id: str) -> tuple[CapabilitySignal, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM capability_signals
            WHERE workspace_id = ?
            ORDER BY topic ASC, id ASC
            """,
            (workspace_id,),
        ).fetchall()
        return tuple(deserialize_entity(CapabilitySignal, _row_to_payload(row)) for row in rows)

    def get(self, signal_id: str) -> CapabilitySignal | None:
        row = self.connection.execute(
            "SELECT * FROM capability_signals WHERE id = ?",
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(CapabilitySignal, _row_to_payload(row))

    def upsert(self, signal: CapabilitySignal) -> CapabilitySignal:
        current = self.get(signal.id)
        if current is None:
            payload = encode_record("capability_signals", capability_signal_to_record(signal))
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(f":{key}" for key in payload)
            self.connection.execute(
                f"INSERT INTO capability_signals ({columns}) VALUES ({placeholders})",
                payload,
            )
            self.connection.commit()
            return signal
        if _snapshot(current) == _snapshot(signal):
            return current
        updated = CapabilitySignal(
            id=current.id,
            topic=signal.topic,
            evidence_ids=signal.evidence_ids,
            observed_practice=signal.observed_practice,
            current_gaps=signal.current_gaps,
            confidence=signal.confidence,
            workspace_id=signal.workspace_id,
            version=current.version + 1,
            disposition=current.disposition,
            visibility=current.visibility,
        )
        payload = encode_record("capability_signals", capability_signal_to_record(updated))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE capability_signals SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return updated

    def set_controls(
        self,
        signal_id: str,
        *,
        visibility: PrivacyLevel | None = None,
        disposition: InsightDisposition | None = None,
    ) -> CapabilitySignal:
        current = self.get(signal_id)
        if current is None:
            raise KeyError(f"Unknown capability signal: {signal_id}")
        updated = CapabilitySignal(
            id=current.id,
            topic=current.topic,
            evidence_ids=current.evidence_ids,
            observed_practice=current.observed_practice,
            current_gaps=current.current_gaps,
            confidence=current.confidence,
            workspace_id=current.workspace_id,
            version=current.version,
            disposition=disposition if disposition is not None else current.disposition,
            visibility=visibility if visibility is not None else current.visibility,
        )
        payload = encode_record("capability_signals", capability_signal_to_record(updated))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE capability_signals SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return updated


def capability_signal_to_record(signal: CapabilitySignal) -> dict[str, object]:
    return {
        "id": signal.id,
        "topic": signal.topic,
        "evidence_ids": list(signal.evidence_ids),
        "observed_practice": signal.observed_practice,
        "current_gaps": list(signal.current_gaps),
        "confidence": signal.confidence,
        "workspace_id": signal.workspace_id,
        "version": signal.version,
        "disposition": signal.disposition.value,
        "visibility": signal.visibility.value,
    }


def _snapshot(signal: CapabilitySignal) -> tuple[object, ...]:
    return (
        signal.topic,
        signal.evidence_ids,
        signal.observed_practice,
        signal.current_gaps,
        signal.confidence,
        signal.workspace_id,
    )
