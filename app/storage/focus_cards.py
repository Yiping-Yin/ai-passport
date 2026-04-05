"""Focus card persistence helpers."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from app.domain import FocusCard, FocusStatus
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("focus_cards", {key: row[key] for key in row.keys()})


class FocusCardRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_by_workspace(self, workspace_id: str) -> tuple[FocusCard, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM focus_cards
            WHERE workspace_id = ?
            ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'archived' THEN 1 ELSE 2 END, title ASC
            """,
            (workspace_id,),
        ).fetchall()
        return tuple(deserialize_entity(FocusCard, _row_to_payload(row)) for row in rows)

    def get(self, focus_id: str) -> FocusCard | None:
        row = self.connection.execute(
            "SELECT * FROM focus_cards WHERE id = ?",
            (focus_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(FocusCard, _row_to_payload(row))

    def create(self, focus_card: FocusCard) -> FocusCard:
        payload = encode_record("focus_cards", focus_card_to_record(focus_card))
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT INTO focus_cards ({columns}) VALUES ({placeholders})",
            payload,
        )
        self.connection.commit()
        return focus_card

    def update(self, focus_card: FocusCard) -> FocusCard:
        payload = encode_record("focus_cards", focus_card_to_record(focus_card))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE focus_cards SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return focus_card

    def archive_other_active(self, workspace_id: str, *, keep_id: str, now: datetime) -> None:
        active_cards = [
            card
            for card in self.list_by_workspace(workspace_id)
            if card.status is FocusStatus.ACTIVE and card.id != keep_id
        ]
        for card in active_cards:
            archived = FocusCard(
                id=card.id,
                title=card.title,
                goal=card.goal,
                timeframe=card.timeframe,
                priority=card.priority,
                success_criteria=card.success_criteria,
                related_topics=card.related_topics,
                status=FocusStatus.ARCHIVED,
                workspace_id=card.workspace_id,
            )
            self.update(archived)

    def active_for_workspace(self, workspace_id: str) -> FocusCard | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM focus_cards
            WHERE workspace_id = ? AND status = 'active'
            ORDER BY priority ASC, title ASC
            LIMIT 1
            """,
            (workspace_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(FocusCard, _row_to_payload(row))


def focus_card_to_record(card: FocusCard) -> dict[str, object]:
    return {
        "id": card.id,
        "title": card.title,
        "goal": card.goal,
        "timeframe": card.timeframe,
        "priority": card.priority,
        "success_criteria": list(card.success_criteria),
        "related_topics": list(card.related_topics),
        "status": card.status.value,
        "workspace_id": card.workspace_id,
    }
