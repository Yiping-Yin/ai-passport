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
            self.assertEqual(
                applied,
                [
                    "202604061600__initial_schema.sql",
                    "202604061730__compile_jobs.sql",
                    "202604062000__knowledge_node_revisions.sql",
                    "202604062030__node_evidence_links.sql",
                    "202604062100__knowledge_node_field_overrides.sql",
                    "202604062130__insight_controls.sql",
                    "202604062140__mistake_pattern_evidence.sql",
                    "202604062200__postcard_revisions.sql",
                ],
            )

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
            self.assertEqual(rolled_back, "202604062200__postcard_revisions.sql")

            rolled_back_again = migrate_down(db_path)
            self.assertEqual(rolled_back_again, "202604062140__mistake_pattern_evidence.sql")

            rolled_back_third = migrate_down(db_path)
            self.assertEqual(rolled_back_third, "202604062130__insight_controls.sql")

            rolled_back_fourth = migrate_down(db_path)
            self.assertEqual(rolled_back_fourth, "202604062100__knowledge_node_field_overrides.sql")

            rolled_back_fifth = migrate_down(db_path)
            self.assertEqual(rolled_back_fifth, "202604062030__node_evidence_links.sql")

            rolled_back_sixth = migrate_down(db_path)
            self.assertEqual(rolled_back_sixth, "202604062000__knowledge_node_revisions.sql")

            rolled_back_seventh = migrate_down(db_path)
            self.assertEqual(rolled_back_seventh, "202604061730__compile_jobs.sql")

            rolled_back_eighth = migrate_down(db_path)
            self.assertEqual(rolled_back_eighth, "202604061600__initial_schema.sql")

            connection = sqlite3.connect(db_path)
            try:
                table_names = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                self.assertNotIn("workspaces", table_names)
                self.assertNotIn("compile_jobs", table_names)
                self.assertNotIn("knowledge_node_revisions", table_names)
                self.assertNotIn("node_evidence_links", table_names)
                self.assertNotIn("knowledge_node_field_overrides", table_names)
                self.assertNotIn("postcard_revisions", table_names)
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
