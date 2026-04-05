from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.storage.migrate import migrate_down, migrate_up
from app.storage.seed import seed_database


class StorageTests(unittest.TestCase):
    def test_migration_applies_and_rolls_back(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.sqlite3"
            applied = migrate_up(db_path)
            self.assertEqual(applied, ["202604061600__initial_schema.sql"])

            connection = sqlite3.connect(db_path)
            try:
                table_names = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                self.assertIn("workspaces", table_names)
                self.assertIn("review_candidates", table_names)
            finally:
                connection.close()

            rolled_back = migrate_down(db_path)
            self.assertEqual(rolled_back, "202604061600__initial_schema.sql")

            connection = sqlite3.connect(db_path)
            try:
                table_names = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                self.assertNotIn("workspaces", table_names)
                self.assertIn("schema_migrations", table_names)
            finally:
                connection.close()

    def test_seed_database_populates_relation_chain(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "seed.sqlite3"
            counts = seed_database(db_path)
            self.assertEqual(counts["workspaces"], 1)
            self.assertEqual(counts["review_candidates"], 1)

            connection = sqlite3.connect(db_path)
            try:
                connection.row_factory = sqlite3.Row
                source = connection.execute("SELECT id, workspace_id FROM sources").fetchone()
                evidence = connection.execute("SELECT source_id FROM evidence_fragments").fetchone()
                node = connection.execute("SELECT source_ids FROM knowledge_nodes").fetchone()
                passport = connection.execute("SELECT id, workspace_id FROM passports").fetchone()
                visa = connection.execute("SELECT id, workspace_id FROM visa_bundles").fetchone()
                session = connection.execute("SELECT visa_id FROM mount_sessions").fetchone()

                self.assertEqual(evidence["source_id"], source["id"])
                self.assertIn(source["id"], json.loads(node["source_ids"]))
                self.assertEqual(visa["workspace_id"], passport["workspace_id"])
                self.assertEqual(session["visa_id"], visa["id"])
            finally:
                connection.close()
