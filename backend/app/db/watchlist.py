"""Accessors for the watchlist table."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from .connection import resolve_connection
from .seed import DEFAULT_USER_ID


def list_watchlist(
    user_id: str = DEFAULT_USER_ID, conn: sqlite3.Connection | None = None
) -> list[str]:
    """Tickers on the watchlist, oldest-added first."""
    with resolve_connection(conn) as c:
        rows = c.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at", (user_id,)
        ).fetchall()
        return [row["ticker"] for row in rows]


def add_to_watchlist(
    ticker: str, user_id: str = DEFAULT_USER_ID, conn: sqlite3.Connection | None = None
) -> None:
    """Add a ticker. No-op if it's already on the watchlist."""
    with resolve_connection(conn) as c:
        c.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (str(uuid4()), user_id, ticker.upper(), datetime.now(UTC).isoformat()),
        )


def remove_from_watchlist(
    ticker: str, user_id: str = DEFAULT_USER_ID, conn: sqlite3.Connection | None = None
) -> None:
    """Remove a ticker. No-op if it isn't on the watchlist."""
    with resolve_connection(conn) as c:
        c.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker.upper())
        )
