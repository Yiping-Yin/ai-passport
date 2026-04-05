"""Knowledge node and revision persistence helpers."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app.domain import KnowledgeNode
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("knowledge_nodes", {key: row[key] for key in row.keys()})


@dataclass(frozen=True, slots=True)
class KnowledgeNodeRevision:
    id: str
    node_id: str
    workspace_id: str
    version: int
    title: str
    summary: str
    body: str
    source_ids: tuple[str, ...]
    related_node_ids: tuple[str, ...]
    recorded_at: datetime


class KnowledgeNodeRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, node_id: str) -> KnowledgeNode | None:
        row = self.connection.execute(
            "SELECT * FROM knowledge_nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(KnowledgeNode, _row_to_payload(row))

    def list_by_workspace(self, workspace_id: str) -> tuple[KnowledgeNode, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM knowledge_nodes
            WHERE workspace_id = ?
            ORDER BY node_type ASC, title ASC
            """,
            (workspace_id,),
        ).fetchall()
        return tuple(deserialize_entity(KnowledgeNode, _row_to_payload(row)) for row in rows)

    def upsert_generated(self, node: KnowledgeNode, *, recorded_at: datetime) -> KnowledgeNode:
        current = self.get(node.id)
        if current is None:
            self._insert_node(node)
            self._insert_revision(node, recorded_at=recorded_at)
            self.connection.commit()
            return node

        if self._snapshot_tuple(current) == self._snapshot_tuple(node):
            return current

        updated = KnowledgeNode(
            id=current.id,
            node_type=node.node_type,
            title=node.title,
            summary=node.summary,
            body=node.body,
            source_ids=node.source_ids,
            related_node_ids=node.related_node_ids,
            updated_at=node.updated_at,
            workspace_id=node.workspace_id,
            version=current.version + 1,
        )
        payload = encode_record("knowledge_nodes", knowledge_node_to_record(updated))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE knowledge_nodes SET {assignments} WHERE id = :id",
            payload,
        )
        self._insert_revision(updated, recorded_at=recorded_at)
        self.connection.commit()
        return updated

    def list_revisions(self, node_id: str) -> tuple[KnowledgeNodeRevision, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM knowledge_node_revisions
            WHERE node_id = ?
            ORDER BY version ASC
            """,
            (node_id,),
        ).fetchall()
        return tuple(
            KnowledgeNodeRevision(
                id=row["id"],
                node_id=row["node_id"],
                workspace_id=row["workspace_id"],
                version=row["version"],
                title=row["title"],
                summary=row["summary"],
                body=row["body"],
                source_ids=tuple(json.loads(row["source_ids"])),
                related_node_ids=tuple(json.loads(row["related_node_ids"])),
                recorded_at=datetime.fromisoformat(row["recorded_at"]),
            )
            for row in rows
        )

    def _insert_node(self, node: KnowledgeNode) -> None:
        payload = encode_record("knowledge_nodes", knowledge_node_to_record(node))
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT INTO knowledge_nodes ({columns}) VALUES ({placeholders})",
            payload,
        )

    def _insert_revision(self, node: KnowledgeNode, *, recorded_at: datetime) -> None:
        payload = encode_record(
            "knowledge_node_revisions",
            {
                "id": f"{node.id}-v{node.version}",
                "node_id": node.id,
                "workspace_id": node.workspace_id,
                "version": node.version,
                "title": node.title,
                "summary": node.summary,
                "body": node.body,
                "source_ids": list(node.source_ids),
                "related_node_ids": list(node.related_node_ids),
                "recorded_at": recorded_at.isoformat(),
            },
        )
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT OR REPLACE INTO knowledge_node_revisions ({columns}) VALUES ({placeholders})",
            payload,
        )

    @staticmethod
    def _snapshot_tuple(node: KnowledgeNode) -> tuple[object, ...]:
        return (
            node.node_type,
            node.title,
            node.summary,
            node.body,
            node.source_ids,
            node.related_node_ids,
            node.workspace_id,
        )


def knowledge_node_to_record(node: KnowledgeNode) -> dict[str, object]:
    return {
        "id": node.id,
        "node_type": node.node_type.value,
        "title": node.title,
        "summary": node.summary,
        "body": node.body,
        "source_ids": list(node.source_ids),
        "related_node_ids": list(node.related_node_ids),
        "updated_at": node.updated_at.isoformat(),
        "workspace_id": node.workspace_id,
        "version": node.version,
    }
