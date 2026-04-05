"""Passport persistence helpers."""

from __future__ import annotations

import sqlite3

from app.domain import Passport
from app.domain.serialization import deserialize_entity
from app.storage.sqlite import decode_record, encode_record


def _row_to_payload(row: sqlite3.Row) -> dict[str, object]:
    return decode_record("passports", {key: row[key] for key in row.keys()})


class PassportRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, passport_id: str) -> Passport | None:
        row = self.connection.execute(
            "SELECT * FROM passports WHERE id = ?",
            (passport_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(Passport, _row_to_payload(row))

    def get_by_workspace(self, workspace_id: str) -> Passport | None:
        row = self.connection.execute(
            "SELECT * FROM passports WHERE workspace_id = ? LIMIT 1",
            (workspace_id,),
        ).fetchone()
        if row is None:
            return None
        return deserialize_entity(Passport, _row_to_payload(row))

    def upsert(self, passport: Passport) -> Passport:
        current = self.get(passport.id)
        if current is None:
            payload = encode_record("passports", passport_to_record(passport))
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(f":{key}" for key in payload)
            self.connection.execute(
                f"INSERT INTO passports ({columns}) VALUES ({placeholders})",
                payload,
            )
            self.connection.commit()
            return passport
        if _snapshot(current) == _snapshot(passport):
            return current
        updated = Passport(
            id=current.id,
            owner_summary=passport.owner_summary,
            theme_map=passport.theme_map,
            capability_signal_ids=passport.capability_signal_ids,
            focus_card_ids=passport.focus_card_ids,
            representative_postcard_ids=passport.representative_postcard_ids,
            machine_manifest=passport.machine_manifest,
            version=current.version + 1,
            workspace_id=passport.workspace_id,
        )
        payload = encode_record("passports", passport_to_record(updated))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE passports SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return updated

    def set_owner_summary(self, passport_id: str, owner_summary: str) -> Passport:
        current = self.get(passport_id)
        if current is None:
            raise KeyError(f"Unknown passport: {passport_id}")
        machine_manifest = dict(current.machine_manifest)
        machine_manifest["owner_summary"] = owner_summary
        updated = Passport(
            id=current.id,
            owner_summary=owner_summary,
            theme_map=current.theme_map,
            capability_signal_ids=current.capability_signal_ids,
            focus_card_ids=current.focus_card_ids,
            representative_postcard_ids=current.representative_postcard_ids,
            machine_manifest=machine_manifest,
            version=current.version,
            workspace_id=current.workspace_id,
        )
        payload = encode_record("passports", passport_to_record(updated))
        assignments = ", ".join(f"{key} = :{key}" for key in payload if key != "id")
        self.connection.execute(
            f"UPDATE passports SET {assignments} WHERE id = :id",
            payload,
        )
        self.connection.commit()
        return updated


def passport_to_record(passport: Passport) -> dict[str, object]:
    return {
        "id": passport.id,
        "owner_summary": passport.owner_summary,
        "theme_map": list(passport.theme_map),
        "capability_signal_ids": list(passport.capability_signal_ids),
        "focus_card_ids": list(passport.focus_card_ids),
        "representative_postcard_ids": list(passport.representative_postcard_ids),
        "machine_manifest": passport.machine_manifest,
        "version": passport.version,
        "workspace_id": passport.workspace_id,
    }


def _snapshot(passport: Passport) -> tuple[object, ...]:
    return (
        passport.owner_summary,
        passport.theme_map,
        passport.capability_signal_ids,
        passport.focus_card_ids,
        passport.representative_postcard_ids,
        passport.machine_manifest,
        passport.workspace_id,
    )
