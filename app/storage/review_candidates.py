"""Review candidate persistence helpers."""

from __future__ import annotations

import sqlite3

from app.domain import ReviewCandidate
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("review_candidates", {key: row[key] for key in row.keys()})


class ReviewCandidateRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, candidate: ReviewCandidate) -> ReviewCandidate:
        payload = encode_record("review_candidates", review_candidate_to_record(candidate))
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload)
        self.connection.execute(
            f"INSERT INTO review_candidates ({columns}) VALUES ({placeholders})",
            payload,
        )
        self.connection.commit()
        return candidate

    def get(self, candidate_id: str) -> ReviewCandidate | None:
        row = self.connection.execute(
            "SELECT * FROM review_candidates WHERE id = ?",
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(ReviewCandidate, _row_to_payload(row))

    def list_all(self) -> tuple[ReviewCandidate, ...]:
        rows = self.connection.execute(
            "SELECT * FROM review_candidates ORDER BY id ASC"
        ).fetchall()
        return tuple(deserialize_entity(ReviewCandidate, _row_to_payload(row)) for row in rows)

    def update(self, candidate: ReviewCandidate) -> ReviewCandidate:
        payload = encode_record("review_candidates", review_candidate_to_record(candidate))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE review_candidates SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return candidate


def review_candidate_to_record(candidate: ReviewCandidate) -> dict[str, object]:
    return {
        "id": candidate.id,
        "session_id": candidate.session_id,
        "candidate_type": candidate.candidate_type.value,
        "content_ref": candidate.content_ref,
        "target_object": candidate.target_object,
        "diff_ref": candidate.diff_ref,
        "status": candidate.status.value,
        "version": candidate.version,
        "evidence_ids": list(candidate.evidence_ids),
    }
