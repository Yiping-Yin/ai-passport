"""Node-to-evidence link persistence."""

from __future__ import annotations

import sqlite3


class NodeEvidenceLinkRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def replace_links(self, node_id: str, evidence_ids: tuple[str, ...]) -> None:
        self.connection.execute("DELETE FROM node_evidence_links WHERE node_id = ?", (node_id,))
        for evidence_id in evidence_ids:
            self.connection.execute(
                "INSERT INTO node_evidence_links (node_id, evidence_fragment_id) VALUES (?, ?)",
                (node_id, evidence_id),
            )
        self.connection.commit()

    def list_evidence_ids(self, node_id: str) -> tuple[str, ...]:
        rows = self.connection.execute(
            """
            SELECT evidence_fragment_id
            FROM node_evidence_links
            WHERE node_id = ?
            ORDER BY evidence_fragment_id ASC
            """,
            (node_id,),
        ).fetchall()
        return tuple(row["evidence_fragment_id"] for row in rows)
