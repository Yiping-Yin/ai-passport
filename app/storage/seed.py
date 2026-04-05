#!/usr/bin/env python3
"""Seed the local development database with a sample workspace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.storage.migrate import migrate_up
from app.storage.sqlite import DEFAULT_DB_PATH, connect, insert_record

SEED_PATH = ROOT / "app" / "storage" / "seeds" / "sample_workspace.json"
TABLE_ORDER = [
    ("workspaces", "workspaces"),
    ("sources", "sources"),
    ("knowledge_nodes", "knowledge_nodes"),
    ("evidence_fragments", "evidence_fragments"),
    ("capability_signals", "capability_signals"),
    ("mistake_patterns", "mistake_patterns"),
    ("focus_cards", "focus_cards"),
    ("postcards", "postcards"),
    ("passports", "passports"),
    ("visa_bundles", "visa_bundles"),
    ("mount_sessions", "mount_sessions"),
    ("review_candidates", "review_candidates"),
    ("audit_logs", "audit_logs"),
]


def load_seed_payload(path: Path = SEED_PATH) -> dict[str, list[dict[str, object]]]:
    return json.loads(path.read_text())


def seed_database(db_path: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    migrate_up(db_path)
    payload = load_seed_payload()
    connection = connect(db_path)
    counts: dict[str, int] = {}
    try:
        for key, table in TABLE_ORDER:
            records = payload.get(key, [])
            for record in records:
                insert_record(connection, table, record)
            counts[table] = len(records)
        connection.commit()
    finally:
        connection.close()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()

    counts = seed_database(Path(args.database))
    print("seed: applied sample workspace")
    for table, count in counts.items():
        print(f"{table}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
