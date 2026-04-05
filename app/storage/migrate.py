#!/usr/bin/env python3
"""Apply or roll back SQLite migrations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.storage.sqlite import DEFAULT_DB_PATH, connect

MIGRATIONS_DIR = ROOT / "app" / "storage" / "migrations"


def migration_files() -> list[Path]:
    return sorted(
        path
        for path in MIGRATIONS_DIR.glob("*.sql")
        if path.name.endswith(".sql") and not path.name.endswith(".down.sql")
    )


def ensure_migration_table(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()


def applied_versions(connection) -> set[str]:
    ensure_migration_table(connection)
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def migrate_up(db_path: Path = DEFAULT_DB_PATH) -> list[str]:
    connection = connect(db_path)
    ensure_migration_table(connection)
    applied = applied_versions(connection)
    applied_now: list[str] = []
    try:
        for migration in migration_files():
            if migration.name in applied:
                continue
            connection.executescript(migration.read_text())
            connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (migration.name,))
            connection.commit()
            applied_now.append(migration.name)
    finally:
        connection.close()
    return applied_now


def migrate_down(db_path: Path = DEFAULT_DB_PATH) -> str | None:
    connection = connect(db_path)
    ensure_migration_table(connection)
    try:
        row = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        version = row["version"]
        rollback = MIGRATIONS_DIR / version.replace(".sql", ".down.sql")
        if not rollback.exists():
            raise FileNotFoundError(f"Missing rollback migration for {version}")
        connection.executescript(rollback.read_text())
        connection.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
        connection.commit()
        return version
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direction", choices=["up", "down"])
    parser.add_argument("--database", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()

    db_path = Path(args.database)
    if args.direction == "up":
        applied = migrate_up(db_path)
        if applied:
            print("migrate: applied")
            for version in applied:
                print(version)
        else:
            print("migrate: already up to date")
        return 0

    rolled_back = migrate_down(db_path)
    if rolled_back:
        print(f"migrate: rolled back {rolled_back}")
    else:
        print("migrate: nothing to roll back")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
