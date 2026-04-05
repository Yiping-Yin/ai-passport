"""Manual field override persistence for generated knowledge nodes."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app.domain import OverrideMode


@dataclass(frozen=True, slots=True)
class KnowledgeNodeFieldOverride:
    node_id: str
    field_name: str
    override_mode: OverrideMode
    value: object
    edited_at: datetime
    editor: str


class KnowledgeNodeOverrideRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert(self, override: KnowledgeNodeFieldOverride) -> KnowledgeNodeFieldOverride:
        self.connection.execute(
            """
            INSERT INTO knowledge_node_field_overrides
                (node_id, field_name, override_mode, value_json, edited_at, editor)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(node_id, field_name) DO UPDATE SET
                override_mode = excluded.override_mode,
                value_json = excluded.value_json,
                edited_at = excluded.edited_at,
                editor = excluded.editor
            """,
            (
                override.node_id,
                override.field_name,
                override.override_mode.value,
                json.dumps(override.value, sort_keys=True),
                override.edited_at.isoformat(),
                override.editor,
            ),
        )
        self.connection.commit()
        return override

    def list_for_node(self, node_id: str) -> tuple[KnowledgeNodeFieldOverride, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM knowledge_node_field_overrides
            WHERE node_id = ?
            ORDER BY field_name ASC
            """,
            (node_id,),
        ).fetchall()
        return tuple(
            KnowledgeNodeFieldOverride(
                node_id=row["node_id"],
                field_name=row["field_name"],
                override_mode=OverrideMode(row["override_mode"]),
                value=json.loads(row["value_json"]),
                edited_at=datetime.fromisoformat(row["edited_at"]),
                editor=row["editor"],
            )
            for row in rows
        )
