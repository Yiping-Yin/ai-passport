"""Evidence fragment queries for preview use."""

from __future__ import annotations

import sqlite3

from app.domain import EvidenceFragment
from app.domain.serialization import deserialize_entity


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return {key: row[key] for key in row.keys()}


class EvidenceFragmentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_for_source(self, source_id: str) -> tuple[EvidenceFragment, ...]:
        rows = self.connection.execute(
            """
            SELECT ef.*
            FROM evidence_fragments ef
            WHERE ef.source_id = ?
            ORDER BY ef.id ASC
            """,
            (source_id,),
        ).fetchall()
        return tuple(deserialize_entity(EvidenceFragment, _row_to_payload(row)) for row in rows)
