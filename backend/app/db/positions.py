"""Accessors for the positions table.

`apply_trade` owns the position-side math for a fill (weighted-average cost on
buys, quantity reduction on sells). Cash validation and cash-balance updates
are the caller's responsibility (see backend-engineer's trade endpoint).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from .connection import resolve_connection
from .models import Position
from .seed import DEFAULT_USER_ID

_QUANTITY_EPSILON = 1e-9


def get_position(
    ticker: str, user_id: str = DEFAULT_USER_ID, conn: sqlite3.Connection | None = None
) -> Position | None:
    with resolve_connection(conn) as c:
        row = c.execute(
            "SELECT * FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker.upper())
        ).fetchone()
        return Position.from_row(row) if row else None


def list_positions(
    user_id: str = DEFAULT_USER_ID, conn: sqlite3.Connection | None = None
) -> list[Position]:
    with resolve_connection(conn) as c:
        rows = c.execute(
            "SELECT * FROM positions WHERE user_id = ? ORDER BY ticker", (user_id,)
        ).fetchall()
        return [Position.from_row(row) for row in rows]


def apply_trade(
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    user_id: str = DEFAULT_USER_ID,
    conn: sqlite3.Connection | None = None,
) -> Position | None:
    """Apply a fill to the position for `ticker`. Returns the resulting position,
    or None if a sell closed it out entirely.

    Buys: weighted-average the cost basis into the existing position (or open one).
    Sells: reduce quantity; raises ValueError if selling more than is held.
    """
    if quantity <= 0:
        raise ValueError(f"quantity must be positive, got {quantity}")
    ticker = ticker.upper()
    now = datetime.now(UTC).isoformat()

    with resolve_connection(conn) as c:
        existing = get_position(ticker, user_id, c)

        if side == "buy":
            if existing is None:
                pos_id = str(uuid4())
                c.execute(
                    "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (pos_id, user_id, ticker, quantity, price, now),
                )
                return Position(pos_id, user_id, ticker, quantity, price, now)

            new_quantity = existing.quantity + quantity
            new_avg_cost = (
                existing.quantity * existing.avg_cost + quantity * price
            ) / new_quantity
            c.execute(
                "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? WHERE id = ?",
                (new_quantity, new_avg_cost, now, existing.id),
            )
            return Position(existing.id, user_id, ticker, new_quantity, new_avg_cost, now)

        if side == "sell":
            if existing is None:
                raise ValueError(f"no position in {ticker} to sell")
            new_quantity = existing.quantity - quantity
            if new_quantity < -_QUANTITY_EPSILON:
                raise ValueError(
                    f"cannot sell {quantity} shares of {ticker}; only {existing.quantity} held"
                )
            if new_quantity <= _QUANTITY_EPSILON:
                c.execute("DELETE FROM positions WHERE id = ?", (existing.id,))
                return None
            c.execute(
                "UPDATE positions SET quantity = ?, updated_at = ? WHERE id = ?",
                (new_quantity, now, existing.id),
            )
            return Position(existing.id, user_id, ticker, new_quantity, existing.avg_cost, now)

        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
