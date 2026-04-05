from __future__ import annotations

from pathlib import Path
import unittest

from scripts import dev


ROOT = Path(__file__).resolve().parent.parent


class DevCommandTests(unittest.TestCase):
    def test_lint_repo_has_no_errors(self) -> None:
        self.assertEqual(dev.lint_repo(ROOT), [])

    def test_python_files_include_bootstrap_scripts(self) -> None:
        names = {path.name for path in dev.python_files(ROOT)}
        self.assertIn("dev.py", names)
        self.assertIn("seed_github.py", names)

    def test_migration_directory_exists(self) -> None:
        self.assertTrue((ROOT / "app" / "storage" / "migrations").exists())


if __name__ == "__main__":
    unittest.main()
