"""SQLite helpers for the bootstrap storage layer."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "data" / "dev" / "ai_passport.sqlite3"
JSON_COLUMNS = {
    "workspaces": {"tags"},
    "sources": {"tags"},
    "knowledge_nodes": {"source_ids", "related_node_ids"},
    "capability_signals": {"evidence_ids", "current_gaps"},
    "mistake_patterns": {"examples", "fix_suggestions"},
    "focus_cards": {"success_criteria", "related_topics"},
    "postcards": {"known_things", "done_things", "common_gaps", "active_questions", "evidence_links", "related_nodes"},
    "passports": {"theme_map", "capability_signal_ids", "focus_card_ids", "representative_postcard_ids", "machine_manifest"},
    "visa_bundles": {"scope", "included_postcards", "included_nodes", "permission_levels", "redaction_rules"},
    "mount_sessions": {"actions"},
    "review_candidates": {"evidence_ids"},
    "audit_logs": {"meta"},
}


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def encode_record(table: str, record: dict[str, Any]) -> dict[str, Any]:
    json_columns = JSON_COLUMNS.get(table, set())
    encoded: dict[str, Any] = {}
    for key, value in record.items():
        if key in json_columns:
            encoded[key] = json.dumps(value, separators=(",", ":"), sort_keys=True)
        else:
            encoded[key] = value
    return encoded


def insert_record(connection: sqlite3.Connection, table: str, record: dict[str, Any]) -> None:
    encoded = encode_record(table, record)
    columns = ", ".join(encoded.keys())
    placeholders = ", ".join(f":{key}" for key in encoded)
    connection.execute(
        f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
        encoded,
    )
