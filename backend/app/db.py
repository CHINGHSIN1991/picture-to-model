import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


def timestamp() -> str:
    # Fixed width keeps ISO strings lexically sortable for ORDER BY created_at.
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class Database:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 15000")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path.parent.chmod(0o700)
        with self.connect() as connection:
            # Changing journal mode can return SQLITE_BUSY immediately even with a
            # busy timeout when API and worker create the same fresh DB together.
            for attempt in range(20):
                try:
                    connection.execute("PRAGMA journal_mode = WAL")
                    break
                except sqlite3.OperationalError as error:
                    if error.sqlite_errorcode != sqlite3.SQLITE_BUSY or attempt == 19:
                        raise
                    time.sleep(min(0.01 * (attempt + 1), 0.1))
        self.path.chmod(0o600)
        with self.transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            migrations = sorted((Path(__file__).parent / "migrations").glob("*.sql"))
            for migration in migrations:
                if connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = ?", (migration.stem,)
                ).fetchone():
                    continue
                # These committed migration files contain simple SQL statements only.
                for statement in migration.read_text().split(";"):
                    if statement.strip():
                        connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (?, ?)", (migration.stem, timestamp())
                )
