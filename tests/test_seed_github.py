from __future__ import annotations

import unittest

from scripts import seed_github


class SeedGithubTests(unittest.TestCase):
    def test_parse_backlog_counts_match_expected(self) -> None:
        manifest = seed_github.parse_backlog(seed_github.BACKLOG_PATH.read_text())
        self.assertEqual(manifest["counts"], seed_github.EXPECTED_COUNTS)

    def test_project_view_specs_are_named_and_unique(self) -> None:
        names = [spec["name"] for spec in seed_github.PROJECT_VIEW_SPECS]
        self.assertEqual(names, ["Current Milestone", "By Epic", "Blocked"])
        self.assertEqual(len(names), len(set(names)))

    def test_status_option_specs_cover_bootstrap_workflow(self) -> None:
        names = [spec["name"] for spec in seed_github.STATUS_OPTION_SPECS]
        self.assertEqual(names, ["Backlog", "Ready", "In Progress", "In Review", "Done", "Blocked"])


if __name__ == "__main__":
    unittest.main()
