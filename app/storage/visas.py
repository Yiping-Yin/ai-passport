"""Visa bundle persistence helpers."""

from __future__ import annotations

import sqlite3

from app.domain import VisaBundle
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("visa_bundles", {key: row[key] for key in row.keys()})


class VisaBundleRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, visa: VisaBundle) -> VisaBundle:
        payload = encode_record("visa_bundles", visa_bundle_to_record(visa))
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT INTO visa_bundles ({columns}) VALUES ({placeholders})",
            payload,
        )
        self.connection.commit()
        return visa

    def get(self, visa_id: str) -> VisaBundle | None:
        row = self.connection.execute(
            "SELECT * FROM visa_bundles WHERE id = ?",
            (visa_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(VisaBundle, _row_to_payload(row))

    def list_by_workspace(self, workspace_id: str) -> tuple[VisaBundle, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM visa_bundles
            WHERE workspace_id = ?
            ORDER BY expiry_at ASC, id ASC
            """,
            (workspace_id,),
        ).fetchall()
        return tuple(deserialize_entity(VisaBundle, _row_to_payload(row)) for row in rows)

    def update(self, visa: VisaBundle) -> VisaBundle:
        payload = encode_record("visa_bundles", visa_bundle_to_record(visa))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE visa_bundles SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return visa


def visa_bundle_to_record(visa: VisaBundle) -> dict[str, object]:
    return {
        "id": visa.id,
        "scope": list(visa.scope),
        "included_postcards": list(visa.included_postcards),
        "included_nodes": list(visa.included_nodes),
        "permission_levels": [permission.value for permission in visa.permission_levels],
        "expiry_at": visa.expiry_at.isoformat() if visa.expiry_at else None,
        "access_mode": visa.access_mode.value,
        "writeback_policy": visa.writeback_policy.value,
        "redaction_rules": list(visa.redaction_rules),
        "status": visa.status.value,
        "version": visa.version,
        "workspace_id": visa.workspace_id,
    }
