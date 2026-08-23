"""Connection helper with lazy schema/seed initialization.

The database file lives at `db/finally.db` relative to the project root by
default. Set FINALLY_DB_PATH to override (used by tests and devops).
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from . import schema, seed

# backend/app/db/connection.py -> parents[3] is the project root.
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "db" / "finally.db"


def get_db_path() -> Path:
    """Resolve the active database file path (env override or default)."""
    override = os.environ.get("FINALLY_DB_PATH")
    return Path(override) if override else _DEFAULT_DB_PATH


def _is_initialized(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'users_profile'"
    ).fetchone()
    return row is not None


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a connection to the database, creating and seeding it if needed.

    Commits on clean exit, closes always. Each call opens a short-lived
    connection; this app is single-user and low-throughput so per-call
    connections are simpler than a shared pool.
    """
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        if not _is_initialized(conn):
            schema.create_tables(conn)
            seed.seed_defaults(conn)
            conn.commit()
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def resolve_connection(conn: sqlite3.Connection | None) -> Iterator[sqlite3.Connection]:
    """Use `conn` if given (caller controls commit), else open+commit a fresh one.

    Lets accessor functions be called standalone or composed into one atomic
    transaction (e.g. a trade touching cash, positions, and trade history).
    """
    if conn is not None:
        yield conn
        return
    with get_connection() as owned:
        yield owned
