#!/usr/bin/env python3
"""Repo-local developer commands for the bootstrap milestone."""

from __future__ import annotations

import argparse
import json
import py_compile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.storage.migrate import DEFAULT_DB_PATH, migrate_up
from app.storage.seed import seed_database

REQUIRED_PATHS = [
    ROOT / "AGENTS.md",
    ROOT / "PLANS.md",
    ROOT / "Documentation.md",
    ROOT / "README.md",
    ROOT / "docs" / "spec" / "product-prd.md",
    ROOT / "docs" / "spec" / "execution-backlog.md",
    ROOT / "docs" / "spec" / "repository-recon.md",
    ROOT / "docs" / "spec" / "architecture-baseline.md",
    ROOT / "docs" / "spec" / "development-policy.md",
    ROOT / "app" / "storage" / "migrations" / "README.md",
    ROOT / "app" / "storage" / "seeds" / "README.md",
    ROOT / "scripts" / "seed_github.py",
    ROOT / "state" / "backlog-manifest.json",
    ROOT / "state" / "github-import-manifest.json",
]
DOCUMENTATION_MARKERS = [
    "python3 scripts/dev.py migrate",
    "python3 scripts/dev.py seed",
    "python3 scripts/dev.py lint",
    "python3 scripts/dev.py typecheck",
    "python3 scripts/dev.py test",
    "python3 scripts/dev.py ci",
]


def python_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for base in ("app", "scripts", "tests"):
        candidate = root / base
        if not candidate.exists():
            continue
        files.extend(path for path in candidate.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(files)


def lint_repo(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for path in REQUIRED_PATHS:
        if not path.exists():
            errors.append(f"Missing required path: {path.relative_to(root)}")

    documentation = (root / "Documentation.md").read_text()
    for marker in DOCUMENTATION_MARKERS:
        if marker not in documentation:
            errors.append(f"Documentation.md is missing command marker: {marker}")

    plans = (root / "PLANS.md").read_text()
    if "Current milestone:" not in plans:
        errors.append("PLANS.md must declare the current milestone.")

    for json_path in (root / "state").glob("*.json"):
        try:
            json.loads(json_path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in {json_path.relative_to(root)}: {exc}")

    return errors


def run_lint(root: Path = ROOT) -> int:
    errors = lint_repo(root)
    if errors:
        for error in errors:
            print(f"lint: {error}")
        return 1
    print("lint: ok")
    return 0


def run_typecheck(root: Path = ROOT) -> int:
    for path in python_files(root):
        py_compile.compile(str(path), doraise=True)
    print(f"typecheck: ok ({len(python_files(root))} python files compiled)")
    return 0


def run_tests(root: Path = ROOT) -> int:
    suite = unittest.defaultTestLoader.discover(
        str(root / "tests"),
        pattern="test_*.py",
        top_level_dir=str(root),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def migration_files(root: Path = ROOT) -> list[Path]:
    migrations_dir = root / "app" / "storage" / "migrations"
    return sorted(path for path in migrations_dir.glob("*.sql") if path.is_file())


def run_migrate(root: Path = ROOT) -> int:
    migrate_up(DEFAULT_DB_PATH)
    files = migration_files(root)
    if files:
        print(f"migrate: database ready at {DEFAULT_DB_PATH.relative_to(root)}")
        for path in files:
            print(path.relative_to(root))
    else:
        print("migrate: no migrations discovered")
    return 0


def run_seed() -> int:
    counts = seed_database(DEFAULT_DB_PATH)
    print(f"seed: database ready at {DEFAULT_DB_PATH.relative_to(ROOT)}")
    for table, count in counts.items():
        print(f"{table}: {count}")
    return 0


def run_ci(root: Path = ROOT) -> int:
    for label, runner in (("lint", run_lint), ("typecheck", run_typecheck), ("test", run_tests)):
        code = runner(root)
        if code != 0:
            print(f"ci: {label} failed")
            return code
    print("ci: ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["lint", "typecheck", "test", "migrate", "seed", "ci"])
    args = parser.parse_args()

    if args.command == "lint":
        return run_lint()
    if args.command == "typecheck":
        return run_typecheck()
    if args.command == "test":
        return run_tests()
    if args.command == "migrate":
        return run_migrate()
    if args.command == "seed":
        return run_seed()
    if args.command == "ci":
        return run_ci()
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
