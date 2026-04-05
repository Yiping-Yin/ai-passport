"""Postcard persistence helpers."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app.domain import Postcard, PrivacyLevel
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("postcards", {key: row[key] for key in row.keys()})


@dataclass(frozen=True, slots=True)
class PostcardRevision:
    id: str
    postcard_id: str
    workspace_id: str
    version: int
    card_type: str
    title: str
    suggested_next_step: str
    evidence_links: tuple[str, ...]
    related_nodes: tuple[str, ...]
    recorded_at: datetime


class PostcardRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, postcard_id: str) -> Postcard | None:
        row = self.connection.execute(
            "SELECT * FROM postcards WHERE id = ?",
            (postcard_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(Postcard, _row_to_payload(row))

    def list_by_workspace(self, workspace_id: str, *, include_hidden: bool = True) -> tuple[Postcard, ...]:
        query = "SELECT * FROM postcards WHERE workspace_id = ?"
        params: list[object] = [workspace_id]
        if not include_hidden:
            query += " AND visibility != ?"
            params.append(PrivacyLevel.RESTRICTED.value)
        query += " ORDER BY card_type ASC, title ASC"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return tuple(deserialize_entity(Postcard, _row_to_payload(row)) for row in rows)

    def upsert(self, postcard: Postcard, *, recorded_at: datetime) -> Postcard:
        current = self.get(postcard.id)
        if current is None:
            self._insert(postcard)
            self._insert_revision(postcard, recorded_at=recorded_at)
            self.connection.commit()
            return postcard
        if _snapshot(current) == _snapshot(postcard):
            return current
        updated = Postcard(
            id=current.id,
            card_type=postcard.card_type,
            title=postcard.title,
            known_things=postcard.known_things,
            done_things=postcard.done_things,
            common_gaps=postcard.common_gaps,
            active_questions=postcard.active_questions,
            suggested_next_step=postcard.suggested_next_step,
            evidence_links=postcard.evidence_links,
            related_nodes=postcard.related_nodes,
            visibility=current.visibility,
            version=current.version + 1,
            workspace_id=postcard.workspace_id,
        )
        payload = encode_record("postcards", postcard_to_record(updated))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE postcards SET {assignments} WHERE id = :id",
            payload,
        )
        self._insert_revision(updated, recorded_at=recorded_at)
        self.connection.commit()
        return updated

    def set_visibility(self, postcard_id: str, visibility: PrivacyLevel) -> Postcard:
        current = self.get(postcard_id)
        if current is None:
            raise KeyError(f"Unknown postcard: {postcard_id}")
        updated = Postcard(
            id=current.id,
            card_type=current.card_type,
            title=current.title,
            known_things=current.known_things,
            done_things=current.done_things,
            common_gaps=current.common_gaps,
            active_questions=current.active_questions,
            suggested_next_step=current.suggested_next_step,
            evidence_links=current.evidence_links,
            related_nodes=current.related_nodes,
            visibility=visibility,
            version=current.version,
            workspace_id=current.workspace_id,
        )
        payload = encode_record("postcards", postcard_to_record(updated))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE postcards SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return updated

    def list_revisions(self, postcard_id: str) -> tuple[PostcardRevision, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM postcard_revisions
            WHERE postcard_id = ?
            ORDER BY version ASC
            """,
            (postcard_id,),
        ).fetchall()
        return tuple(
            PostcardRevision(
                id=row["id"],
                postcard_id=row["postcard_id"],
                workspace_id=row["workspace_id"],
                version=row["version"],
                card_type=row["card_type"],
                title=row["title"],
                suggested_next_step=row["suggested_next_step"],
                evidence_links=tuple(json.loads(row["evidence_links"])),
                related_nodes=tuple(json.loads(row["related_nodes"])),
                recorded_at=datetime.fromisoformat(row["recorded_at"]),
            )
            for row in rows
        )

    def _insert(self, postcard: Postcard) -> None:
        payload = encode_record("postcards", postcard_to_record(postcard))
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT INTO postcards ({columns}) VALUES ({placeholders})",
            payload,
        )

    def _insert_revision(self, postcard: Postcard, *, recorded_at: datetime) -> None:
        payload = encode_record(
            "postcard_revisions",
            {
                "id": f"{postcard.id}-v{postcard.version}",
                "postcard_id": postcard.id,
                "workspace_id": postcard.workspace_id,
                "version": postcard.version,
                "card_type": postcard.card_type.value,
                "title": postcard.title,
                "known_things": list(postcard.known_things),
                "done_things": list(postcard.done_things),
                "common_gaps": list(postcard.common_gaps),
                "active_questions": list(postcard.active_questions),
                "suggested_next_step": postcard.suggested_next_step,
                "evidence_links": list(postcard.evidence_links),
                "related_nodes": list(postcard.related_nodes),
                "visibility": postcard.visibility.value,
                "recorded_at": recorded_at.isoformat(),
            },
        )
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT OR REPLACE INTO postcard_revisions ({columns}) VALUES ({placeholders})",
            payload,
        )


def postcard_to_record(postcard: Postcard) -> dict[str, object]:
    return {
        "id": postcard.id,
        "card_type": postcard.card_type.value,
        "title": postcard.title,
        "known_things": list(postcard.known_things),
        "done_things": list(postcard.done_things),
        "common_gaps": list(postcard.common_gaps),
        "active_questions": list(postcard.active_questions),
        "suggested_next_step": postcard.suggested_next_step,
        "evidence_links": list(postcard.evidence_links),
        "related_nodes": list(postcard.related_nodes),
        "visibility": postcard.visibility.value,
        "version": postcard.version,
        "workspace_id": postcard.workspace_id,
    }


def _snapshot(postcard: Postcard) -> tuple[object, ...]:
    return (
        postcard.card_type,
        postcard.title,
        postcard.known_things,
        postcard.done_things,
        postcard.common_gaps,
        postcard.active_questions,
        postcard.suggested_next_step,
        postcard.evidence_links,
        postcard.related_nodes,
        postcard.workspace_id,
    )
