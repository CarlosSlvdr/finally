"""Accessors for the trades table (append-only log)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from .connection import resolve_connection
from .models import Trade
from .seed import DEFAULT_USER_ID


def record_trade(
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> Trade:
    """Append a trade to the log. Purely a record; does not touch positions or cash."""
    trade_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    with resolve_connection(conn) as c:
        c.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, user_id, ticker.upper(), side, quantity, price, now),
        )
    return Trade(trade_id, user_id, ticker.upper(), side, quantity, price, now)


def list_trades(
    user_id: str = DEFAULT_USER_ID,
    limit: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[Trade]:
    """Trades newest-first, optionally capped at `limit`."""
    query = "SELECT * FROM trades WHERE user_id = ? ORDER BY executed_at DESC"
    params: tuple = (user_id,)
    if limit is not None:
        query += " LIMIT ?"
        params = (user_id, limit)
    with resolve_connection(conn) as c:
        rows = c.execute(query, params).fetchall()
        return [Trade.from_row(row) for row in rows]
