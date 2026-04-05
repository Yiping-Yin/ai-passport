"""Evidence fragment queries for preview use."""

from __future__ import annotations

import sqlite3
from typing import Iterable

from app.domain import EvidenceFragment
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return {key: row[key] for key in row.keys()}


class EvidenceFragmentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_or_replace(self, fragment: EvidenceFragment) -> EvidenceFragment:
        payload = encode_record(
            "evidence_fragments",
            {
                "id": fragment.id,
                "source_id": fragment.source_id,
                "locator": fragment.locator,
                "excerpt": fragment.excerpt,
                "confidence": fragment.confidence,
            },
        )
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT OR REPLACE INTO evidence_fragments ({columns}) VALUES ({placeholders})",
            payload,
        )
        self.connection.commit()
        return fragment

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

    def list_for_ids(self, evidence_ids: Iterable[str]) -> tuple[EvidenceFragment, ...]:
        evidence_ids = tuple(evidence_ids)
        if not evidence_ids:
            return ()
        placeholders = ", ".join("?" for _ in evidence_ids)
        rows = self.connection.execute(
            f"SELECT * FROM evidence_fragments WHERE id IN ({placeholders}) ORDER BY id ASC",
            evidence_ids,
        ).fetchall()
        return tuple(deserialize_entity(EvidenceFragment, _row_to_payload(row)) for row in rows)
